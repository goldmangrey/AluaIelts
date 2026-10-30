import WidgetKit
import SwiftUI

@main
struct AluaWidgetsBundle: WidgetBundle {
    var body: some Widget {
        AluaGlanceWidget()
        TodayLearningWidget()
        VocabularyWidget()
        GrammarWidget()
        PracticeWidget()
        PartnerProgressWidget()
    }
}
