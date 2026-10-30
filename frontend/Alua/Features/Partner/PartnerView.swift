import SwiftUI

struct PartnerView: View {
    let store: PartnerStore
    let aiStore: AIProgressStore
    @State private var inviteCode = ""
    @State private var showRevokeConfirmation = false
    @State private var showReport = false
    @State private var showChat = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                if store.isLoading, store.status == nil { loading }
                else if let status = store.status { statusContent(status) }
                else { errorCard }
            }.padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground).navigationTitle("Partner")
        .task { await store.loadStatus() }.refreshable { await store.refresh() }
        .onChange(of: store.status?.monitoringLearner?.sharingSettings.allowAIProgressAnalysis) { _, allowed in
            aiStore.permissionChanged(isAllowed: allowed == true)
        }
        .navigationDestination(isPresented: $showReport) {
            if let report = aiStore.report { AIProgressReportView(response: report) }
        }
        .navigationDestination(isPresented: $showChat) {
            AIProgressChatView(store: aiStore)
        }
        .confirmationDialog("Disconnect this partner relationship?", isPresented: $showRevokeConfirmation, titleVisibility: .visible) {
            Button("Disconnect", role: .destructive) { Task { await store.revoke() } }
        } message: { Text("Shared dashboard access will stop immediately.") }
    }

    @ViewBuilder private func statusContent(_ status: PartnerStatus) -> some View {
        if status.sharingMyProgress == nil, status.monitoringLearner == nil { noRelationship }
        if let sharing = status.sharingMyProgress { SharingSettingsCard(relationship: sharing, store: store, showRevoke: $showRevokeConfirmation) }
        if status.monitoringLearner == nil { connectCard }
        if let dashboard = store.dashboard { dashboardView(dashboard) }
        else if status.monitoringLearner != nil { loading }
        if let message = store.errorMessage { Text(message).font(AluaTypography.caption).foregroundStyle(.red) }
    }

    private var noRelationship: some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Label("Share your progress", systemImage: "person.2") .font(AluaTypography.headline)
            Text("Sharing requires an explicit invitation and can be stopped at any time.").foregroundStyle(AluaColors.secondaryText)
            Button("Create Invite") { Task { await store.createInvite() } }.buttonStyle(.borderedProminent)
            if let invite = store.invite { inviteView(invite) }
        }}
    }

    private var connectCard: some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Connect to a learner").font(AluaTypography.headline)
            TextField("Invite Code", text: $inviteCode).textInputAutocapitalization(.characters).autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)
            Button("Connect") { Task { await store.acceptInvite(inviteCode) } }
                .buttonStyle(.bordered).disabled(inviteCode.trimmingCharacters(in: .whitespaces).isEmpty || store.isMutating)
        }}
    }

    private func inviteView(_ invite: PartnerInvite) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
            Text("Partner Invite").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
            Text(invite.code).font(.title2.monospaced().weight(.semibold)).textSelection(.enabled)
            Text("Expires \(invite.expiresAt.formatted(date: .abbreviated, time: .shortened))").font(AluaTypography.caption)
            ShareLink(item: "Join my Alua learning progress with code \(invite.code)") { Label("Share Code", systemImage: "square.and.arrow.up") }
            Text("Anyone with this code can connect until it expires. It can only be accepted once.").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
        }.padding(.top, AluaSpacing.sm)
    }

    private func dashboardView(_ dashboard: PartnerDashboardSnapshot) -> some View {
        Group {
            AluaSectionHeader(title: "\(dashboard.learner.displayName)'s Progress")
            Picker("Period", selection: Binding(get: { store.selectedPeriod }, set: { value in Task { await store.changePeriod(value) } })) {
                ForEach(ProgressPeriodSelection.allCases) { Text($0.title).tag($0) }
            }.pickerStyle(.segmented)
            if let today = dashboard.todayActivity { todayCard(today) }
            if let progress = dashboard.progress { progressCard(progress) }
            if let profile = dashboard.learningProfile { profileCard(profile) }
            if let errors = dashboard.recentErrors, !errors.isEmpty { errorsCard(errors) }
            aiProgressCard(dashboard.permissions.allowAIProgressAnalysis)
            Button("Disconnect", role: .destructive) { showRevokeConfirmation = true }.buttonStyle(.bordered)
        }
    }

    private func aiProgressCard(_ allowed: Bool) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Label("AI Progress Analyst", systemImage: "sparkles").font(AluaTypography.headline)
            if allowed, aiStore.isAvailable {
                Text("Generate advisory insights from the learning data shared with you.")
                    .foregroundStyle(AluaColors.secondaryText)
                Button(aiStore.isGeneratingReport ? "Analyzing progress…" : "Generate AI Report") {
                    Task {
                        await aiStore.generateReport(days: store.selectedPeriod.rawValue)
                        if aiStore.report != nil { showReport = true }
                    }
                }.buttonStyle(.borderedProminent).disabled(aiStore.isGeneratingReport)
                Button("Ask AI about progress") {
                    Task {
                        await aiStore.startConversation(days: store.selectedPeriod.rawValue)
                        if aiStore.conversation != nil { showChat = true }
                    }
                }.buttonStyle(.bordered).disabled(aiStore.isSendingMessage)
            } else {
                Text("Not enabled by learner").foregroundStyle(AluaColors.secondaryText)
            }
            if let error = aiStore.errorMessage { Text(error).font(AluaTypography.caption).foregroundStyle(.red) }
        }}
    }

    private func todayCard(_ today: PartnerTodayActivity) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Today").font(AluaTypography.headline)
            if today.hasPlan {
                Text("\(today.completedItems) of \(today.totalItems) activities completed").font(AluaTypography.title)
                AluaProgressBar(value: today.totalItems > 0 ? Double(today.completedItems) / Double(today.totalItems) : 0)
                Text("Estimated study: ~\(today.estimatedCompletedMinutes) min completed / ~\(today.estimatedMinutes ?? 0) min planned").font(AluaTypography.subheadline).foregroundStyle(AluaColors.secondaryText)
                if let focus = today.currentFocus { Text("Current focus: \(focus)") }
            } else { Text("No activity plan yet").foregroundStyle(AluaColors.secondaryText) }
        }}
    }

    private func progressCard(_ progress: ProgressSnapshot) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Progress").font(AluaTypography.headline)
            row("Active days", "\(progress.summary.activeDays) / \(progress.summary.eligibleDays)")
            row("Completed activities", "\(progress.summary.completedItems)")
            row("Practice answers", "\(progress.assessment.attempts)")
            row("Estimated study", "~\(progress.summary.estimatedCompletedMinutes) min")
            if progress.assessment.dataQuality != .insufficient, let accuracy = progress.assessment.accuracy { row("Accuracy", accuracy.formatted(.percent.precision(.fractionLength(0)))) }
            else { Text("Not enough practice data yet").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText) }
        }}
    }

    private func profileCard(_ profile: PartnerLearningProfile) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Learning Profile").font(AluaTypography.headline)
            if let stage = profile.curriculum.recommendedStageTitle { row("Current stage", stage) }
            Text("Strengths: \(profile.strengths.isEmpty ? "Still being identified" : profile.strengths.map { $0.dimension.title }.joined(separator: ", "))")
            Text("Areas to work on: \(profile.weaknesses.isEmpty ? "Still being identified" : profile.weaknesses.map { $0.dimension.title }.joined(separator: ", "))")
        }}
    }

    private func errorsCard(_ errors: [ProgressErrorPattern]) -> some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Recent Patterns").font(AluaTypography.headline)
            ForEach(errors) { row($0.displayTitle, "\($0.count) errors") }
        }}
    }

    private var loading: some View { AluaCard { HStack { SwiftUI.ProgressView(); Text("Loading partner access…") } } }
    private var errorCard: some View { ContentUnavailableView("Partner unavailable", systemImage: "person.2.slash", description: Text(store.errorMessage ?? "Please try again.")) }
    private func row(_ title: String, _ value: String) -> some View { HStack { Text(title); Spacer(); Text(value).foregroundStyle(AluaColors.secondaryText) } }
}

private struct SharingSettingsCard: View {
    let relationship: PartnerRelationshipSummary
    let store: PartnerStore
    @Binding var showRevoke: Bool
    @State private var settings: PartnerSharingSettings
    init(relationship: PartnerRelationshipSummary, store: PartnerStore, showRevoke: Binding<Bool>) {
        self.relationship = relationship; self.store = store; _showRevoke = showRevoke
        _settings = State(initialValue: relationship.sharingSettings)
    }
    var body: some View {
        AluaCard { VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            Text("Progress shared with \(relationship.displayName)").font(AluaTypography.headline)
            Text("Connected \(relationship.connectedAt.formatted(date: .abbreviated, time: .omitted))").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
            Toggle("Daily Activity", isOn: $settings.shareDailyActivity)
            Toggle("Progress Analytics", isOn: $settings.shareProgressAnalytics)
            Toggle("Learning Profile", isOn: $settings.shareLearningProfile)
            Toggle("Recent Error Patterns", isOn: $settings.shareRecentErrorPatterns)
            Toggle("Allow AI Progress Analysis", isOn: $settings.allowAIProgressAnalysis)
            Text("AI analysis consent is off by default; no AI analysis is performed in this version.").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
            Button("Save Changes") { Task { await store.updateSharing(settings) } }.buttonStyle(.borderedProminent).disabled(store.isMutating)
            Button("Stop Sharing", role: .destructive) { showRevoke = true }
        }}
    }
}
