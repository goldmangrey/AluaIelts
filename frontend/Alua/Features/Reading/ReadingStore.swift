import Foundation
import Network
import Observation

@MainActor @Observable final class ReadingStore {
    enum Phase { case idle, loading, ready, starting, active, syncing, submitting, completed, expired, recoverableError }
    let uid: String
    private(set) var disk: ReadingDisk
    private(set) var phase: Phase = .idle
    private(set) var activeID: String?
    private(set) var busy = false
    private(set) var errorMessage: String?
    private(set) var diskError = false
    private(set) var hasMoreHistory = false
    @ObservationIgnored private let automaticallySync: Bool
    @ObservationIgnored private let api: any ReadingAPIProtocol
    @ObservationIgnored let files: ReadingFiles
    @ObservationIgnored private var generation = UUID()
    @ObservationIgnored private var enabled = true
    @ObservationIgnored private var storageBlocked = false
    @ObservationIgnored private var syncing: Set<String> = []
    @ObservationIgnored private var workers: [String: Task<Void, Never>] = [:]
    @ObservationIgnored private var monitor: NWPathMonitor?
    @ObservationIgnored private var anchors: [String: (ContinuousClock.Instant, Int, Date)] = [:]

    init(api: any ReadingAPIProtocol, uid: String, root: URL = ReadingFiles.root, monitorNetwork: Bool = true, automaticallySync: Bool = true) {
        self.api = api; self.uid = uid; self.automaticallySync = automaticallySync; files = ReadingFiles(uid: uid, root: root)
        do { disk = try files.load() }
        catch {
            disk = ReadingDisk(); diskError = true
            do { try files.preserveUnreadableStore() } catch { storageBlocked = true }
            errorMessage = "Не удалось прочитать локальные ответы. Исходный файл сохранён."
        }
        if monitorNetwork {
            let m = NWPathMonitor(); monitor = m
            m.pathUpdateHandler = { [weak self] path in
                guard path.status == .satisfied else { return }
                Task { @MainActor [weak self] in await self?.reconnect() }
            }
            m.start(queue: DispatchQueue(label: "alua.reading.connectivity"))
        }
    }
    var active: ReadingRecord? { activeID.flatMap { disk.records[$0] } }
    var books: [ReadingBook] { disk.books.filter { !$0.available.isEmpty }.sorted { $0.book_number > $1.book_number } }
    var preferences: ReadingPreferences { disk.preferences }
    var isSubmitting: Bool { active?.queue.contains { $0.kind == .submit } == true }
    var isChecking: Bool { active?.queue.contains { $0.kind == .check } == true }
    var canEdit: Bool {
        guard let r = active, !r.server.terminal, !isSubmitting, !isChecking else { return false }
        return r.server.mode == .passage_practice || (remainingSeconds ?? 0) > 0
    }
    var remainingSeconds: Int? {
        guard let id = activeID, active?.server.mode == .full_exam, let a = anchors[id] else { return nil }
        let elapsed = a.0.duration(to: .now).components.seconds
        return max(0, a.1 - Int(elapsed))
    }
    var syncMessage: String {
        guard let r = active else { return "" }
        if diskError { return "Не удалось сохранить на iPhone. Не закрывай приложение; повтори сохранение." }
        if r.conflict { return "Не удалось синхронизировать изменения. Твои локальные ответы сохранены." }
        if r.server.terminal, !r.excludedLocalAnswers.isEmpty { return "Часть ответов сохранена только на iPhone и не вошла в результат." }
        if !r.queue.isEmpty { return "\(r.queue.count) изменений сохранены на iPhone и ожидают отправки." }
        return "Ответы сохранены на сервере."
    }
    private func appendEvent(_ event: ReadingEvent, to record: inout ReadingRecord) {
        var event = event
        event.expectedVersion = record.queue.last?.expectedVersion.map { $0 + 1 } ?? record.server.version
        record.queue.append(event)
    }
    private func save() -> Bool {
        guard !storageBlocked else { diskError = true; return false }
        do { try files.save(disk); diskError = false; return true }
        catch { diskError = true; errorMessage = "Не удалось сохранить ответы на iPhone. Повтори сохранение."; return false }
    }
    func retryLocalSave() { if save() { errorMessage = nil; scheduleSync() } }
    func deactivate() {
        enabled = false; generation = UUID(); workers.values.forEach { $0.cancel() }; workers = [:]
        monitor?.cancel(); monitor = nil; activeID = nil; anchors = [:]
    }
    func setPreferences(theme: ReadingTheme? = nil, size: Double? = nil) {
        if let theme { disk.preferences.theme = theme }
        if let size { disk.preferences.fontSize = min(30, max(16, size)) }
        _ = save()
    }
    func updateUI(_ action: (inout ReadingUIState) -> Void) {
        guard let id = activeID, var r = disk.records[id] else { return }
        let previous = r.ui
        action(&r.ui)
        guard previous != r.ui else { return }
        disk.records[id] = r; _ = save()
    }
    func selectQuestion(_ question: ReadingQuestion) {
        guard let r = active, let p = r.exam.passage(for: question.id) else { return }
        updateUI { $0.currentPassage = p.number; $0.questionID = question.id }
        if r.state.current_passage != p.number { queueState(passage: p.number) }
    }
    func selectPassage(_ number: Int) {
        guard let p = active?.exam.passages.first(where: { $0.number == number }) else { return }
        let remembered = active?.ui.questionID.flatMap { id in p.questions.first { $0.id == id } }
        updateUI { $0.currentPassage = number; $0.questionID = remembered?.id ?? p.questions.first?.id }
        queueState(passage: number)
    }
    func edit(_ qid: String, answer: String) {
        guard canEdit, let id = activeID, var r = active,
              r.exam.questions.contains(where: { $0.id == qid }), !r.state.checked_question_ids.contains(qid) else { return }
        let value = String(answer.prefix(500)); r.answers[qid] = value
        appendEvent(ReadingEvent(kind: .answer, questionID: qid, answer: value), to: &r)
        disk.records[id] = r
        if save() { scheduleSync() }
    }
    func batch(_ answers: [String: String]) {
        guard canEdit, let id = activeID, var r = active,
              answers.keys.allSatisfy({ qid in r.exam.questions.contains { $0.id == qid } && !r.state.checked_question_ids.contains(qid) }) else { return }
        r.answers.merge(answers) { _, new in new }; appendEvent(ReadingEvent(kind: .batch, answers: answers), to: &r)
        disk.records[id] = r; if save() { scheduleSync() }
    }
    func queueState(passage: Int? = nil, annotations: [ReadingAnnotation]? = nil, crossed: [ReadingCrossedOption]? = nil) {
        guard let id = activeID, var r = active, !r.server.terminal else { return }
        if let passage { r.state.current_passage = passage }
        if let annotations { r.state.annotations = annotations }
        if let crossed { r.state.crossed_options = crossed }
        appendEvent(ReadingEvent(kind: .state, state: r.state), to: &r)
        disk.records[id] = r; if save() { scheduleSync() }
    }
    func highlight(passage: ReadingPassage, block: Int, range: NSRange, color: String?) {
        guard let r = active, !r.server.terminal, block < passage.content.count,
              let offsets = ReadingTextRange.codepoints(range, in: passage.content[block].text) else { return }
        var annotations = r.state.annotations.filter { !($0.passage_id == passage.id && $0.block_index == block && $0.start < offsets.end && $0.end > offsets.start) }
        if let color {
            guard annotations.count < 300 else { errorMessage = "Достигнут лимит выделений для попытки."; return }
            annotations.append(ReadingAnnotation(id: UUID(), passage_id: passage.id, content_hash: r.server.content_hash,
                                                block_index: block, start: offsets.start, end: offsets.end,
                                                quote: offsets.quote, color: color))
        }
        queueState(annotations: annotations)
    }
    func cross(_ qid: String, label: String) {
        guard let r = active, canEdit else { return }
        let item = ReadingCrossedOption(question_id: qid, option_label: label)
        var options = r.state.crossed_options
        if options.contains(item) { options.removeAll { $0 == item } } else { options.append(item) }
        queueState(crossed: options)
    }
    func check(_ ids: [String]) {
        guard canEdit, active?.server.mode == .passage_practice, let id = activeID else { return }
        guard var r = disk.records[id] else { return }
        appendEvent(ReadingEvent(kind: .check, questionIDs: ids), to: &r)
        disk.records[id] = r
        if save() { scheduleSync() }
    }
    func submit() {
        guard let id = activeID, var r = active, !r.server.terminal, !isSubmitting else { return }
        appendEvent(ReadingEvent(kind: .submit), to: &r)
        disk.records[id] = r
        phase = .submitting; if save() { scheduleSync() }
    }
    func clearError() { errorMessage = nil }
    private func endpoint(_ suffix: String, method: HTTPMethod = .get, body: (any Encodable)? = nil, query: [URLQueryItem] = []) -> APIEndpoint {
        APIEndpoint(path: "api/v1/reading/" + suffix, method: method, queryItems: query, body: body, requiresAuthentication: true)
    }
    func loadLibrary() async {
        guard enabled, !busy else { return }; busy = true; phase = .loading
        let g = generation
        defer { if g == generation { busy = false } }
        do {
            let response = try await api.send(endpoint("books"), as: ReadingCatalogResponse.self)
            guard enabled, g == generation else { return }
            disk.books = response.items; _ = save()
            await loadHistory(reset: true)
            guard g == generation else { return }; phase = .ready; errorMessage = nil
        } catch { if g == generation { report(error) } }
    }
    func loadHistory(reset: Bool) async {
        let g = generation
        do {
            let page = try await api.send(endpoint("attempts", query: [URLQueryItem(name: "limit", value: "100"), URLQueryItem(name: "offset", value: String(reset ? 0 : disk.history.count))]), as: ReadingAttemptList.self)
            guard enabled, g == generation else { return }
            if reset { disk.history = page.items } else { disk.history += page.items.filter { item in !disk.history.contains { $0.id == item.id } } }
            hasMoreHistory = page.items.count == page.limit; _ = save()
        } catch { if g == generation { report(error) } }
    }
    func start(exam: String, mode: ReadingMode, passage: Int?) async -> Bool {
        guard enabled, !busy else { return false }; busy = true; phase = .starting
        let g = generation
        defer { if g == generation { busy = false } }
        do {
            let content = try await api.send(endpoint("exams/" + exam), as: ReadingExam.self)
            guard enabled, g == generation else { return false }
            // Cache necessary materials BEFORE the authoritative Full Exam timer starts.
            for a in content.passages.filter({ passage == nil || $0.number == passage }).flatMap({ $0.question_groups.flatMap(\.assets) }) {
                _ = try await loadAsset(a)
                guard enabled, g == generation else { return false }
            }
            if let pending = disk.pendingStart, pending.exam_id != exam || pending.mode != mode || pending.selected_passage != passage {
                errorMessage = "Сначала восстанови предыдущий запрос начала экзамена."; return false
            }
            if disk.pendingStart == nil { disk.pendingStart = ReadingStart(exam_id: exam, mode: mode, selected_passage: passage) }
            guard save(), let request = disk.pendingStart else { return false }
            let created = try await api.send(endpoint("attempts", method: .post, body: request), as: ReadingAttempt.self)
            guard enabled, g == generation else { return false }
            let cached = ReadingExam(id: content.id, dataset_version: content.dataset_version, source_book: content.source_book, source_test_number: content.source_test_number, test_ordinal: content.test_ordinal, duration_seconds: content.duration_seconds,
                                     question_count: passage == nil ? content.question_count : content.passages.first { $0.number == passage }?.questions.count ?? 0,
                                     content_status: content.content_status, passages: content.passages.filter { passage == nil || $0.number == passage })
            var record = ReadingRecord(server: created, exam: cached, answers: created.answers ?? [:], state: created.state ?? ReadingAttemptState())
            record.ui.currentPassage = passage ?? 1; record.ui.questionID = cached.questions.first?.id
            disk.records[created.id] = record; disk.pendingStart = nil; activeID = created.id
            _ = save(); anchor(created)
            // A replayed create response may predate expiry or later edits. GET is authoritative.
            await refresh()
            return true
        } catch { if g == generation { report(error) }; return false }
    }
    func open(_ id: String) async -> Bool {
        guard enabled, !busy else { return false }; busy = true
        defer { busy = false }
        activeID = id; errorMessage = nil
        await refresh()
        return active != nil
    }
    func refresh() async {
        guard enabled, let id = activeID else { return }
        let g = generation
        do {
            let server = try await api.send(endpoint("attempts/" + id), as: ReadingAttempt.self)
            guard enabled, g == generation else { return }
            absorb(server, id: id, fresh: true)
            if server.terminal { await fetchResult(id: id, generation: g) }
            else { scheduleSync(id) }
        } catch { if g == generation && id == activeID { report(error) } }
    }
    private func anchor(_ server: ReadingAttempt) {
        guard let remaining = server.remaining_seconds else { return }
        if let old = anchors[server.id], old.2 > server.server_now { return }
        anchors[server.id] = (.now, remaining, server.server_now)
    }
    private func absorb(_ server: ReadingAttempt, id: String, fresh: Bool) {
        if var r = disk.records[id] {
            guard server.version >= r.server.version else { return }
            r.server = server
            if let exam = server.exam { r.exam = exam }
            if let checked = server.checked_result {
                var positions = Dictionary(uniqueKeysWithValues: r.checkedPositions.map { ($0.question_id, $0) })
                for position in checked.positions { positions[position.question_id] = position }
                r.checkedAnswers = positions
                r.checked = checked
            }
            if let result = server.result { r.result = result }
            if server.terminal {
                r.unaccepted += r.queue; r.queue = []
                if r.answers == (server.answers ?? [:]) { r.conflict = false }
            } else if r.queue.isEmpty && !r.conflict {
                r.answers = server.answers ?? r.answers; r.state = server.state ?? r.state
            }
            // Keep newer local edits over an older acknowledgement; only checked IDs are authoritative.
            if let checked = server.state?.checked_question_ids { r.state.checked_question_ids = checked }
            disk.records[id] = r
        } else if let exam = server.exam {
            var r = ReadingRecord(server: server, exam: exam, answers: server.answers ?? [:], state: server.state ?? ReadingAttemptState())
            r.checked = server.checked_result
            if let checked = server.checked_result {
                r.checkedAnswers = Dictionary(uniqueKeysWithValues: checked.positions.map { ($0.question_id, $0) })
            }
            r.ui.currentPassage = server.state?.current_passage ?? exam.passages.first?.number ?? 1
            r.ui.questionID = exam.questions.first?.id
            disk.records[id] = r
        }
        if fresh { anchor(server) }
        _ = save()
        if id == activeID { phase = server.status == "expired" ? .expired : server.terminal ? .completed : .active }
    }
    private func fetchResult(id: String, generation g: UUID) async {
        do {
            let result = try await api.send(endpoint("attempts/\(id)/result"), as: ReadingResult.self)
            guard enabled, g == generation else { return }
            disk.records[id]?.result = result; _ = save()
        } catch { if g == generation && id == activeID { report(error) } }
    }
    func scheduleSync(_ id: String? = nil) {
        guard enabled, automaticallySync, let id = id ?? activeID, !syncing.contains(id), workers[id] == nil else { return }
        workers[id] = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(250)) } catch { return }
            let firstID = self?.disk.records[id]?.queue.first?.id
            await self?.sync(id)
            self?.workers[id] = nil
            if let next = self?.disk.records[id]?.queue.first?.id, next != firstID,
               self?.disk.records[id]?.conflict == false, self?.diskError == false {
                self?.scheduleSync(id)
            }
        }
    }
    func sync(_ id: String? = nil) async {
        guard enabled, !diskError, let id = id ?? activeID, !syncing.contains(id), disk.records[id]?.conflict == false else { return }
        syncing.insert(id); let g = generation
        defer { syncing.remove(id) }
        while enabled, g == generation, let first = disk.records[id]?.queue.first, disk.records[id]?.server.terminal == false {
            guard first.expectedVersion != nil else {
                disk.records[id]?.conflict = true; _ = save()
                errorMessage = "Не удалось синхронизировать изменения. Твои локальные ответы сохранены."
                return
            }
            guard let event = disk.records[id]?.queue.first else { return }
            do {
                let reply = try await api.send(event.endpoint(attempt: id), as: ReadingAttempt.self)
                guard enabled, g == generation else { return }
                guard disk.records[id]?.queue.first?.id == event.id else { return }
                if reply.mutation_applied == false { // Deadline rejection is a successful HTTP response, not an accepted answer.
                    absorb(reply, id: id, fresh: true)
                    await fetchResult(id: id, generation: g); return
                }
                disk.records[id]?.queue.removeFirst()
                absorb(reply, id: id, fresh: true)
                if id == activeID && !diskError { errorMessage = nil }
                if reply.terminal {
                    if reply.result == nil { await fetchResult(id: id, generation: g) }
                    return
                }
            } catch is CancellationError { return }
            catch {
                guard enabled, g == generation else { return }
                if case let APIError.server(status, _, _) = error, status == 409 || status == 422 {
                    disk.records[id]?.conflict = true; _ = save()
                    // Get server state without silently rebasing an old local answer onto its version.
                    do {
                        let latest = try await api.send(endpoint("attempts/" + id), as: ReadingAttempt.self)
                        guard enabled, g == generation else { return }
                        absorb(latest, id: id, fresh: true)
                        if latest.terminal { await fetchResult(id: id, generation: g) }
                    } catch { }
                }
                if id == activeID { report(error) }; return
            }
        }
    }
    func resolveConflict(keepLocal: Bool) {
        guard let id = activeID, var r = active, !r.server.terminal else { return }
        r.unaccepted += r.queue; r.queue = []; r.conflict = false
        if keepLocal {
            let changes = r.answers.filter { !r.state.checked_question_ids.contains($0.key) && $0.value != r.server.answers?[$0.key] }
            if !changes.isEmpty { appendEvent(ReadingEvent(kind: .batch, answers: changes), to: &r) }
            appendEvent(ReadingEvent(kind: .state, state: r.state), to: &r)
        } else { r.answers = r.server.answers ?? [:]; r.state = r.server.state ?? ReadingAttemptState() }
        disk.records[id] = r; errorMessage = nil; if save() { scheduleSync(id) }
    }
    func reconnect() async {
        guard enabled else { return }
        if activeID != nil { await refresh() }
        for id in disk.records.keys where disk.records[id]?.queue.isEmpty == false { scheduleSync(id) }
    }
    func loadAsset(_ a: ReadingAsset) async throws -> Data {
        if let data = files.asset(a) { return data }
        let g = generation
        let data = try await api.asset(a, cached: nil)
        guard enabled, g == generation else { throw CancellationError() }
        try files.saveAsset(data, asset: a); return data
    }
    private func report(_ error: Error) {
        if error is CancellationError { return }
        phase = .recoverableError
        if case APIError.unauthorized = error { errorMessage = "Устройство не авторизовано. Вернись в настройки подключения." }
        else if active?.conflict == true { errorMessage = "Не удалось синхронизировать изменения. Твои локальные ответы сохранены." }
        else if case APIError.decoding = error { errorMessage = "Не удалось прочитать материалы. Локальные ответы сохранены; повтори загрузку." }
        else { errorMessage = "Нет соединения. Сохранённые на iPhone ответы доступны; повтори попытку." }
    }
}
