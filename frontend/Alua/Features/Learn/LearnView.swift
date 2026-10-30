import SwiftUI

struct LearnView: View {
    let studyStore: StudyStore?
    let store: CurriculumStore
    let vocabularyStore: VocabularyStore
    let grammarStore: GrammarStore
    let vocabularyLearningStore: VocabularyLearningStore
    let notifications: VocabularyNotificationService
    let learningEventService: any LearningEventServiceProtocol
    let profile: UserProfile?
    let qualityService: LearningQualityService
    @State private var reviewSessionID: ReviewPresentation?
    @State private var reminderState: VocabularyNotificationService.AuthorizationState = .unknown
    @State private var debugMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                NavigationLink("Стартовая проверка · 12 вопросов (по желанию)") { DiagnosticView(service: qualityService) }
                if let studyStore { AluaCard { StudyHome(store: studyStore) }.id(studyStore.uid) }
                if let today = vocabularyLearningStore.today { reminders(today) }
                secondaryDestinations
            }.padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground).navigationTitle("Vocabulary")
        .task { await vocabularyLearningStore.loadToday(); reminderState = await notifications.authorizationState() }
        .refreshable { await vocabularyLearningStore.loadToday() }
        .fullScreenCover(item: $reviewSessionID) { value in VocabularyReviewSessionView(sessionID: value.id, store: vocabularyLearningStore) }
    }

    private func dashboard(_ today: VocabularyLearningToday) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.lg) {
            AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) { Text("TODAY").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText); Text("\(today.dailyPack.count) lexical units").font(AluaTypography.title); Text("\(today.dailyPack.coreWords.count) words · \(today.dailyPack.synonymUpgrades.count) upgrades · \(today.dailyPack.phrases.count) phrases").font(AluaTypography.subheadline); Divider(); Text("Review due  \(today.reviewDueCount)").font(AluaTypography.headline) } }
            if let recall = today.currentRecall {
                quickRecall(recall)
            }
            Button(primaryTitle(today)) { reviewSessionID = ReviewPresentation(id: primarySession(today).sessionID) }.buttonStyle(.borderedProminent).controlSize(.large).frame(maxWidth: .infinity)
            packSection("WORDS", items: today.dailyPack.coreWords)
            packSection("UPGRADES", items: today.dailyPack.synonymUpgrades)
            packSection("PHRASES & COLLOCATIONS", items: today.dailyPack.phrases)
            reminders(today)
        }
    }

    private func quickRecall(_ recall: CurrentVocabularyRecall) -> some View {
        Button {
            reviewSessionID = ReviewPresentation(id: recall.sessionID)
        } label: {
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                    Text("QUICK RECALL")
                        .font(AluaTypography.caption.weight(.semibold))
                        .foregroundStyle(AluaColors.secondaryText)
                    Text(recall.lexicalItem.term.uppercased())
                        .font(AluaTypography.title)
                        .foregroundStyle(AluaColors.primaryText)
                    Text(recall.prompt)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(AluaColors.secondaryText)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Quick recall: \(recall.lexicalItem.term). \(recall.prompt)")
    }

    private func packSection(_ title: String, items: [LexicalItem]) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text(title)
                .font(AluaTypography.caption.weight(.semibold))
                .foregroundStyle(AluaColors.secondaryText)
            AluaCard {
                VStack(spacing: 0) {
                    ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                        lexicalRow(item)
                        if index < items.count - 1 { Divider() }
                    }
                }
            }
        }
    }

    private func lexicalRow(_ item: LexicalItem) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(alignment: .firstTextBaseline, spacing: AluaSpacing.sm) {
                Text(item.term)
                    .font(AluaTypography.headline)
                    .foregroundStyle(AluaColors.primaryText)
                if let ipa = item.ipa, !ipa.isEmpty {
                    Text(ipa)
                        .font(AluaTypography.subheadline)
                        .foregroundStyle(AluaColors.secondaryText)
                }
                Spacer(minLength: 0)
                if let cefr = item.cefr, !cefr.isEmpty {
                    Text(cefr)
                        .font(AluaTypography.caption)
                        .foregroundStyle(AluaColors.secondaryText)
                }
            }
            CardActionsView(itemID: item.id, service: qualityService, onSaved: { await vocabularyLearningStore.loadToday() })
            Text(item.translationRU)
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)
        }
        .padding(.vertical, AluaSpacing.sm)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    private func primarySession(_ today: VocabularyLearningToday) -> ReviewSessionSummary { Calendar.current.component(.hour, from: Date()) >= 20 ? today.eveningSession : today.middaySession }
    private func primaryTitle(_ today: VocabularyLearningToday) -> String { let session = primarySession(today); if session.completedCount >= session.cardCount { return "Done for today" }; return session.completedCount > 0 ? "Continue review" : session.kind == .evening ? "Start evening review" : "Start midday review" }
    private func reminders(_ today: VocabularyLearningToday) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Vocabulary reminders").font(AluaTypography.headline); Text("14:00 review · 20:00 review").font(AluaTypography.subheadline).foregroundStyle(AluaColors.secondaryText)
            if reminderState == .enabled { Button("Disable reminders") { notifications.disable(); reminderState = .unknown } }
            else { Button(reminderState == .denied ? "Open Settings" : "Enable reminders") { Task { if reminderState == .denied { notifications.openSettings() } else { _ = await notifications.enable(); reminderState = await notifications.authorizationState(); await notifications.scheduleDailyReminders(for: today) } } } }
            #if DEBUG
            Button("Send vocabulary test notification in 10 seconds") { Task { debugMessage = await notifications.scheduleDebugTest(today: today) ? "Test scheduled" : "Enable notifications first" } }
            if let debugMessage { Text(debugMessage).font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText) }
            #endif
        } }
    }
    private var secondaryDestinations: some View {
        NavigationLink { GrammarLibraryView(store: grammarStore, curriculumStore: store, learningEventService: learningEventService) } label: { track("Grammar", "textformat") }.buttonStyle(.plain)
    }
    private func track(_ title: String, _ symbol: String) -> some View { AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) { Image(systemName: symbol).foregroundStyle(AluaColors.accent); Text(title).font(AluaTypography.headline) } } }
}

private struct ReviewPresentation: Identifiable { let id: String }
