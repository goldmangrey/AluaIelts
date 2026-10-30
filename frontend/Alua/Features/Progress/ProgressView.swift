import Charts
import SwiftUI

struct ProgressView: View {
    let store: ProgressStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: AluaSpacing.lg) {
                Picker("Period", selection: periodBinding) {
                    ForEach(ProgressPeriodSelection.allCases) { period in
                        Text(period.title).tag(period)
                    }
                }
                .pickerStyle(.segmented)

                if store.isLoading, store.snapshot == nil {
                    loadingCard
                } else if let snapshot = store.snapshot {
                    content(snapshot)
                } else {
                    retryCard
                }
            }
            .padding(AluaSpacing.md)
        }
        .background(AluaColors.groupedBackground)
        .navigationTitle("Progress")
        .task { await store.load() }
        .refreshable { await store.refresh() }
    }

    private var periodBinding: Binding<ProgressPeriodSelection> {
        Binding(
            get: { store.selectedPeriod },
            set: { period in Task { await store.changePeriod(period) } }
        )
    }

    private var loadingCard: some View {
        AluaCard {
            HStack(spacing: AluaSpacing.sm) {
                SwiftUI.ProgressView()
                Text("Loading your progress…")
            }
        }
    }

    private var retryCard: some View {
        ContentUnavailableView {
            Label("Progress unavailable", systemImage: "chart.bar.xaxis")
        } description: {
            Text(store.errorMessage ?? "Please try again.")
        } actions: {
            Button("Retry") { Task { await store.refresh() } }
                .buttonStyle(.borderedProminent)
        }
    }

    @ViewBuilder
    private func content(_ snapshot: ProgressSnapshot) -> some View {
        summary(snapshot)
        if snapshot.summary.activeDays == 0, snapshot.summary.plannedItems == 0 {
            emptyProgress
        } else {
            activityChart(snapshot)
        }
        if snapshot.assessment.attempts == 0 {
            assessmentEmpty
        } else {
            practice(snapshot)
        }
        mastery("Vocabulary", snapshot.mastery.vocabulary, noun: "words")
        mastery("Grammar", snapshot.mastery.grammar, noun: "topics")
        learningProfile(snapshot)
        if !snapshot.recentErrors.isEmpty { recentPatterns(snapshot.recentErrors) }
        comparison(snapshot)
    }

    private func summary(_ snapshot: ProgressSnapshot) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: "This period")
            LazyVGrid(columns: [.init(.flexible()), .init(.flexible())], spacing: AluaSpacing.sm) {
                metric("Active days", "\(snapshot.summary.activeDays) / \(snapshot.summary.eligibleDays)", "calendar")
                metric("Completed activities", "\(snapshot.summary.completedItems)", "checkmark.circle")
                metric("Practice answers", "\(snapshot.assessment.attempts)", "text.badge.checkmark")
                metric("Estimated study", "~\(snapshot.summary.estimatedCompletedMinutes) min", "clock")
            }
        }
    }

    private func metric(_ title: String, _ value: String, _ icon: String) -> some View {
        AluaCard {
            VStack(alignment: .leading, spacing: AluaSpacing.xs) {
                Image(systemName: icon).foregroundStyle(AluaColors.accent)
                Text(value).font(AluaTypography.title)
                Text(title).font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var emptyProgress: some View {
        AluaCard {
            VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                Label("Build your learning profile", systemImage: "chart.line.uptrend.xyaxis")
                    .font(AluaTypography.headline)
                Text("Open learning content and complete practice activities to see progress here.")
                    .font(AluaTypography.subheadline)
                    .foregroundStyle(AluaColors.secondaryText)
            }
        }
    }

    private func activityChart(_ snapshot: ProgressSnapshot) -> some View {
        chartSection("Completed activities", subtitle: "Daily Plan items completed by day") {
            Chart(snapshot.timeline) { point in
                BarMark(x: .value("Date", point.date), y: .value("Completed", point.completedItems))
                    .foregroundStyle(AluaColors.accent)
            }
            .chartYAxis { AxisMarks(position: .leading) }
            .frame(height: 180)
        }
    }

    private var assessmentEmpty: some View {
        AluaCard {
            VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                Text("Practice accuracy").font(AluaTypography.headline)
                Text("Not enough practice data yet").foregroundStyle(AluaColors.secondaryText)
                Text("Complete assessment activities to see correct and incorrect answers over time.")
                    .font(AluaTypography.caption)
                    .foregroundStyle(AluaColors.secondaryText)
            }
        }
    }

    @ViewBuilder
    private func practice(_ snapshot: ProgressSnapshot) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: "Practice")
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    if snapshot.assessment.dataQuality == .insufficient {
                        Text("Not enough data yet").font(AluaTypography.headline)
                        Text("\(snapshot.assessment.attempts) answers completed")
                            .foregroundStyle(AluaColors.secondaryText)
                    } else if let accuracy = snapshot.assessment.accuracy {
                        Text(accuracy, format: .percent.precision(.fractionLength(0)))
                            .font(AluaTypography.largeTitle)
                        Text("Overall accuracy · \(snapshot.assessment.attempts) answers")
                            .foregroundStyle(AluaColors.secondaryText)
                        HStack {
                            domainAccuracy("Grammar", snapshot.assessment.grammar)
                            Spacer()
                            domainAccuracy("Vocabulary", snapshot.assessment.vocabulary)
                        }
                    }
                }
            }
        }
        chartSection("Correct and incorrect", subtitle: "Assessment answers by day") {
            Chart(snapshot.timeline) { point in
                BarMark(x: .value("Date", point.date), y: .value("Answers", point.correctAttempts))
                    .foregroundStyle(by: .value("Result", "Correct"))
                BarMark(x: .value("Date", point.date), y: .value("Answers", point.incorrectAttempts))
                    .foregroundStyle(by: .value("Result", "Incorrect"))
            }
            .chartForegroundStyleScale(["Correct": Color.green, "Incorrect": Color.orange])
            .chartYAxis { AxisMarks(position: .leading) }
            .frame(height: 190)
        }
    }

    private func domainAccuracy(_ title: String, _ domain: ProgressDomainAssessment) -> some View {
        VStack(alignment: .leading) {
            Text(title).font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
            Text(domain.accuracy.map { $0.formatted(.percent.precision(.fractionLength(0))) } ?? "—")
                .font(AluaTypography.headline)
            Text("\(domain.attempts) answers").font(AluaTypography.caption)
        }
    }

    private func mastery(_ title: String, _ value: ProgressContentMasteryBreakdown, noun: String) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: title, subtitle: "Current evidence-backed mastery")
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.sm) {
                    Text("\(value.assessed) of \(value.total) \(noun) assessed")
                        .font(AluaTypography.headline)
                    detailRow("Developing", value.developing)
                    detailRow("Competent", value.competent)
                    detailRow("Strong", value.strong)
                    detailRow("Not assessed", value.unassessed)
                }
            }
        }
    }

    private func learningProfile(_ snapshot: ProgressSnapshot) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: "Learning profile")
            AluaCard {
                VStack(alignment: .leading, spacing: AluaSpacing.md) {
                    if let stage = snapshot.curriculum.recommendedStageTitle {
                        VStack(alignment: .leading) {
                            Text("Current stage").font(AluaTypography.caption).foregroundStyle(AluaColors.secondaryText)
                            Text(stage).font(AluaTypography.headline)
                        }
                    }
                    profileGroup("Strengths", snapshot.strengths.map { $0.dimension.title })
                    profileGroup("Areas to work on", snapshot.weaknesses.map { $0.dimension.title })
                }
            }
        }
    }

    private func profileGroup(_ title: String, _ values: [String]) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.xs) {
            Text(title).font(AluaTypography.headline)
            Text(values.isEmpty ? "More practice is needed before these can be identified." : values.joined(separator: " · "))
                .font(AluaTypography.subheadline)
                .foregroundStyle(AluaColors.secondaryText)
        }
    }

    private func recentPatterns(_ patterns: [ProgressErrorPattern]) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: "Recent patterns")
            AluaCard {
                VStack(spacing: AluaSpacing.sm) {
                    ForEach(patterns) { pattern in
                        HStack {
                            Text(pattern.displayTitle)
                            Spacer()
                            Text("\(pattern.count) errors").foregroundStyle(AluaColors.secondaryText)
                        }
                    }
                }
            }
        }
    }

    private func comparison(_ snapshot: ProgressSnapshot) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: "Compared with previous \(snapshot.period.days) days")
            AluaCard {
                if snapshot.comparison.previousDataAvailable {
                    VStack(spacing: AluaSpacing.sm) {
                        deltaRow("Active days", snapshot.comparison.activeDaysDelta)
                        deltaRow("Completed activities", snapshot.comparison.completedItemsDelta)
                        deltaRow("Practice answers", snapshot.comparison.assessmentAttemptsDelta)
                        if snapshot.comparison.accuracyComparisonAvailable,
                           let delta = snapshot.comparison.accuracyPercentagePointsDelta
                        {
                            HStack {
                                Text("Accuracy")
                                Spacer()
                                Text("\(delta.formatted(.number.precision(.fractionLength(0)).sign(strategy: .always()))) pp")
                                    .foregroundStyle(AluaColors.secondaryText)
                            }
                        }
                    }
                } else {
                    Text("No previous-period data yet.")
                        .foregroundStyle(AluaColors.secondaryText)
                }
            }
        }
    }

    private func chartSection<Content: View>(_ title: String, subtitle: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: AluaSpacing.sm) {
            AluaSectionHeader(title: title, subtitle: subtitle)
            AluaCard { content() }
        }
    }

    private func detailRow(_ title: String, _ value: Int) -> some View {
        HStack { Text(title); Spacer(); Text("\(value)").foregroundStyle(AluaColors.secondaryText) }
    }

    private func deltaRow(_ title: String, _ value: Int) -> some View {
        HStack {
            Text(title)
            Spacer()
            Text(value.formatted(.number.sign(strategy: .always())))
                .foregroundStyle(AluaColors.secondaryText)
        }
    }
}
