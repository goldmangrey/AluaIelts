import SwiftUI

struct ReadingQuestionPanel: View {
    @Bindable var store: ReadingStore
    let expanded: Bool
    let onExpand: () -> Void
    @FocusState private var focused: String?
    private var record: ReadingRecord? { store.active }
    private var current: ReadingQuestion? { record?.exam.questions.first { $0.id == record?.ui.questionID } ?? record?.exam.questions.first }
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                if let q = current {
                    Button { onExpand() } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("Question \(q.number)").font(.headline)
                            Text(record?.answers[q.id, default: ""].isEmpty == false ? "С ответом" : "Без ответа").font(.caption).foregroundStyle(.secondary)
                        }
                    }.buttonStyle(.plain).accessibilityIdentifier("reading.question.expand")
                    Spacer()
                    Button { store.updateUI { if !$0.bookmarks.insert(q.id).inserted { $0.bookmarks.remove(q.id) } } } label: {
                        Image(systemName: record?.ui.bookmarks.contains(q.id) == true ? "bookmark.fill" : "bookmark").frame(width: 44, height: 44)
                    }.accessibilityLabel("Отметить вопрос \(q.number) для возврата. Сохраняется на iPhone")
                    Button { move(-1) } label: { Image(systemName: "chevron.left").frame(width: 44, height: 44) }.accessibilityLabel("Предыдущий вопрос")
                    Button { move(1) } label: { Image(systemName: "chevron.right").frame(width: 44, height: 44) }.accessibilityLabel("Следующий вопрос")
                }
            }.padding(.horizontal)
            if expanded, let q = current, let group = record?.exam.group(for: q.id) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 20) {
                            groupContext(group)
                            if group.type == .multiple_choice_multiple, !group.options.isEmpty {
                                multiChoice(group).id(q.id)
                            } else {
                                ForEach(group.questions) { item in
                                    question(item, group: group).id(item.id)
                                }
                            }
                            if record?.server.mode == .passage_practice {
                                Button("Проверить группу") { focused = nil; store.check(group.questions.map(\.id)) }
                                    .buttonStyle(.borderedProminent).tint(.primary).disabled(!store.canEdit)
                            }
                        }.scrollTargetLayout().padding()
                    }
                    .scrollPosition(id: Binding(get: { record?.ui.questionAnchors[group.id] }, set: { id in store.updateUI { $0.questionAnchors[group.id] = id } }), anchor: .top)
                    .scrollDismissesKeyboard(.interactively)
                    .onChange(of: current?.id) { _, id in if let id { proxy.scrollTo(id, anchor: .top) } }
                }
            } else if let q = current {
                Button(action: onExpand) { Text(q.prompt).font(.subheadline).lineLimit(2).frame(maxWidth: .infinity, alignment: .leading) }
                    .buttonStyle(.plain).padding(.horizontal).padding(.bottom, 12)
            }
        }
        .toolbar { ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("Готово") { focused = nil } } }

    }
    @ViewBuilder private func groupContext(_ group: ReadingGroup) -> some View {
        if group.usesImage {
            ForEach(group.assets) { ReadingAssetView(asset: $0, store: store) }
            if group.assets.isEmpty { Text("Для задания отсутствует обязательная схема. Прохождение недоступно.").foregroundStyle(.red) }
        } else if sharedContext(group) {
            ReadingBlocksView(blocks: group.content_blocks, assets: group.assets, store: store)
        } else {
            Text(group.instructions).font(.subheadline).textSelection(.enabled)
            DisclosureGroup("Полный контекст задания") {
                ReadingBlocksView(blocks: group.content_blocks, assets: group.assets, store: store)
            }.font(.subheadline)
        }
    }
    @ViewBuilder private func question(_ q: ReadingQuestion, group: ReadingGroup) -> some View {
        let checked = record?.state.checked_question_ids.contains(q.id) == true
        let locked = !store.canEdit || checked
        VStack(alignment: .leading, spacing: 12) {
            Text("Question \(q.number)").font(.headline)
            if !group.usesImage && !sharedContext(group) { Text(q.prompt).textSelection(.enabled) }
            let options = group.options(for: q)
            if !options.isEmpty && q.answer_input_type != .text {
                ForEach(options) { option in
                    HStack(alignment: .top) {
                        Button { store.edit(q.id, answer: option.label); UISelectionFeedbackGenerator().selectionChanged() } label: {
                            HStack(alignment: .top) {
                                Image(systemName: record?.answers[q.id] == option.label ? "largecircle.fill.circle" : "circle")
                                Text(group.usesImage || option.label == option.text ? option.label : "\(option.label)  \(option.text)")
                                    .strikethrough(record?.state.crossed_options.contains(ReadingCrossedOption(question_id: q.id, option_label: option.label)) == true)
                                Spacer(minLength: 0)
                            }.frame(minHeight: 44, alignment: .leading).contentShape(Rectangle())
                        }.buttonStyle(.plain).disabled(locked).accessibilityLabel("Вопрос \(q.number), вариант \(option.label), \(option.text)").accessibilityAddTraits(record?.answers[q.id] == option.label ? .isSelected : [])
                        if q.type == .multiple_choice_single || q.type == .multiple_choice_multiple {
                            Button { store.cross(q.id, label: option.label) } label: { Image(systemName: "strikethrough").frame(width: 44, height: 44) }
                                .disabled(locked).accessibilityLabel("Зачеркнуть вариант \(option.label)")
                        }
                    }
                }
            } else if q.answer_input_type == .text || group.usesImage {
                TextField(group.usesImage && q.answer_input_type != .text ? "Буква ответа \(q.number)" : "Ответ \(q.number)", text: Binding(get: { record?.answers[q.id] ?? "" }, set: { store.edit(q.id, answer: $0) }))
                    .textFieldStyle(.roundedBorder).textInputAutocapitalization(.never).autocorrectionDisabled()
                    .focused($focused, equals: q.id).disabled(locked).submitLabel(.next).onSubmit { move(1) }
                    .accessibilityIdentifier("reading.answer.\(q.number)")
            } else { Text("Не удалось отобразить варианты задания. Вернись в библиотеку.").foregroundStyle(.red) }
            if let graded = record?.checkedPositions.first(where: { $0.question_id == q.id }) {
                Label(graded.is_correct ? "Верно" : "Правильный ответ: \(graded.correct_answer)", systemImage: graded.is_correct ? "checkmark.circle" : "xmark.circle").font(.subheadline)
            }
            if record?.server.mode == .passage_practice, !checked {
                Button("Проверить ответ") { focused = nil; store.check([q.id]) }.disabled(locked)
            }
        }.padding(14).background(Color.primary.opacity(0.035), in: RoundedRectangle(cornerRadius: 12))
    }
    private func multiChoice(_ group: ReadingGroup) -> some View {
        let ids = group.questions.map(\.id)
        let values = ids.compactMap { record?.answers[$0] }.filter { !$0.isEmpty }.reduce(into: [String]()) { if !$0.contains($1) { $0.append($1) } }
        let limit = group.constraints.selection_count ?? ids.count
        let locked = !store.canEdit || ids.contains { record?.state.checked_question_ids.contains($0) == true }
        return VStack(alignment: .leading, spacing: 12) {
            Text("Questions \(group.question_numbers.map(String.init).joined(separator: ", ")) · выбери \(limit)").font(.headline)
            ForEach(group.options) { option in
                HStack {
                    Button {
                        var selection = values.filter { $0 != option.label }
                        if !values.contains(option.label) && selection.count < limit { selection.append(option.label) }
                        store.batch(Dictionary(uniqueKeysWithValues: ids.enumerated().map { ($0.element, $0.offset < selection.count ? selection[$0.offset] : "") }))
                        UISelectionFeedbackGenerator().selectionChanged()
                    } label: {
                        HStack(alignment: .top) {
                            Image(systemName: values.contains(option.label) ? "checkmark.square.fill" : "square")
                            Text("\(option.label)  \(option.text)").strikethrough(record?.state.crossed_options.contains(ReadingCrossedOption(question_id: ids[0], option_label: option.label)) == true)
                            Spacer(minLength: 0)
                        }.frame(minHeight: 44).contentShape(Rectangle())
                    }.buttonStyle(.plain).disabled(locked || (!values.contains(option.label) && values.count >= limit))
                    Button { store.cross(ids[0], label: option.label) } label: { Image(systemName: "strikethrough").frame(width: 44, height: 44) }.disabled(locked).accessibilityLabel("Зачеркнуть вариант \(option.label)")
                }
            }
            if let checked = record?.checkedPositions {
                ForEach(checked.filter { ids.contains($0.question_id) }) { p in
                    Text("\(p.number): \(p.is_correct ? "Верно" : p.correct_answer)").font(.subheadline)
                }
            }
        }
    }
    private func sharedContext(_ group: ReadingGroup) -> Bool {
        [.summary_completion, .note_completion, .table_completion, .flow_chart_completion, .diagram_labelling].contains(group.type) && !group.content_blocks.isEmpty
    }
    private func move(_ offset: Int) {
        guard let q = current, let all = record?.exam.questions, let i = all.firstIndex(where: { $0.id == q.id }), all.indices.contains(i + offset) else { return }
        focused = nil; store.selectQuestion(all[i + offset])
    }
}

struct ReadingBlocksView: View {
    let blocks: [ReadingBlock]; let assets: [ReadingAsset]; let store: ReadingStore
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { _, block in
                switch block.type {
                case .rich_text: segments(block.segments ?? [])
                case .heading: Text(block.text ?? "").font(.headline)
                case .image:
                    if let a = assets.first(where: { $0.id == block.asset_id }) { ReadingAssetView(asset: a, store: store) }
                    else { Text("Схема недоступна").foregroundStyle(.red) }
                case .list:
                    ForEach(Array((block.items ?? []).enumerated()), id: \.offset) { _, item in HStack(alignment: .top) { Text("•"); segments(item) } }
                case .table:
                    ScrollView(.horizontal) {
                        Grid(alignment: .topLeading, horizontalSpacing: 0, verticalSpacing: 0) {
                            GridRow { ForEach(Array((block.columns ?? []).enumerated()), id: \.offset) { _, c in Text(c).bold().frame(minWidth: 140, alignment: .leading).padding(10).background(Color.primary.opacity(0.06)) } }
                            ForEach(Array((block.rows ?? []).enumerated()), id: \.offset) { _, row in
                                GridRow { ForEach(Array(row.enumerated()), id: \.offset) { _, cell in segments(cell.segments).frame(minWidth: 140, maxWidth: 220, alignment: .leading).padding(10).border(Color.secondary.opacity(0.2), width: 0.5) } }
                            }
                        }
                    }
                }
            }
        }
    }
    private func segments(_ items: [ReadingSegment]) -> some View {
        Text(items.reduce(into: AttributedString()) { result, s in
            if s.type == .text { result.append(AttributedString(s.text ?? "")) }
            else if let n = s.number {
                var blank = AttributedString(" [\(n)] ______ "); blank.font = .body.bold()
                blank.link = URL(string: "alua-reading://question/\(n)"); result.append(blank)
            }
        }).textSelection(.enabled).environment(\.openURL, OpenURLAction { url in
            if url.scheme == "alua-reading", let number = Int(url.lastPathComponent), let q = store.active?.exam.questions.first(where: { $0.number == number }) { store.selectQuestion(q); return .handled }
            return .discarded
        })
    }
}
