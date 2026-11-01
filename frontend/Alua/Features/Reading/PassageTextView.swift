import SwiftUI
import UIKit

extension ReadingTheme {
    var background: Color { Color(uiColor: uiBackground) }
    var foreground: Color { Color(uiColor: uiText) }
    var uiBackground: UIColor {
        switch self { case .light: .systemBackground; case .sepia: UIColor(red: 0.97, green: 0.94, blue: 0.86, alpha: 1); case .dark: UIColor(white: 0.09, alpha: 1) }
    }
    var uiText: UIColor {
        switch self { case .light: .black; case .sepia: UIColor(red: 0.21, green: 0.17, blue: 0.12, alpha: 1); case .dark: UIColor(white: 0.93, alpha: 1) }
    }
}

/// Non-editable TextKit text preserves selection and native VoiceOver, while outer SwiftUI scrolls.
struct PassageTextView: UIViewRepresentable {
    let text: String
    let annotations: [ReadingAnnotation]
    let size: Double
    let theme: ReadingTheme
    let readOnly: Bool
    let onHighlight: (NSRange, String?) -> Void
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> UITextView {
        let view = UITextView()
        view.isEditable = false; view.isSelectable = true; view.isScrollEnabled = false
        view.backgroundColor = .clear; view.textContainerInset = .zero
        view.textContainer.lineFragmentPadding = 0; view.delegate = context.coordinator
        view.adjustsFontForContentSizeCategory = true
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        return view
    }
    func updateUIView(_ view: UITextView, context: Context) {
        context.coordinator.parent = self
        let signature = "\(text)|\(size)|\(theme.rawValue)|\(dynamicTypeSize)|\(annotations)"
        guard context.coordinator.signature != signature else { return }
        context.coordinator.signature = signature
        let selection = view.selectedRange
        let descriptor = UIFont.systemFont(ofSize: size).fontDescriptor.withDesign(.serif) ?? UIFont.systemFont(ofSize: size).fontDescriptor
        let font = UIFontMetrics(forTextStyle: .body).scaledFont(for: UIFont(descriptor: descriptor, size: size))
        let paragraph = NSMutableParagraphStyle(); paragraph.lineSpacing = 6
        let attributed = NSMutableAttributedString(string: text, attributes: [.font: font, .foregroundColor: theme.uiText, .paragraphStyle: paragraph])
        for a in annotations {
            guard let range = ReadingTextRange.utf16(start: a.start, end: a.end, quote: a.quote, in: text) else { continue }
            let color: UIColor = switch a.color {
            case "green": .systemGreen; case "blue": .systemBlue; case "pink": .systemPink; default: .systemYellow
            }
            attributed.addAttribute(.backgroundColor, value: color.withAlphaComponent(theme == .dark ? 0.45 : 0.28), range: range)
        }
        view.attributedText = attributed
        if NSMaxRange(selection) <= attributed.length { view.selectedRange = selection }
        view.invalidateIntrinsicContentSize()
    }
    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UITextView, context: Context) -> CGSize? {
        guard let width = proposal.width, width.isFinite, width > 0 else { return nil }
        let fitted = uiView.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude))
        guard fitted.height.isFinite, fitted.height >= 0 else { return nil }
        return CGSize(width: width, height: ceil(fitted.height))
    }
    final class Coordinator: NSObject, UITextViewDelegate {
        var parent: PassageTextView; var signature = ""
        init(_ parent: PassageTextView) { self.parent = parent }
        func textView(_ textView: UITextView, editMenuForTextIn range: NSRange, suggestedActions: [UIMenuElement]) -> UIMenu? {
            guard !parent.readOnly, ReadingTextRange.codepoints(range, in: parent.text) != nil else { return UIMenu(children: suggestedActions) }
            let colors: [(String, String?)] = [("Жёлтый маркер", "yellow"), ("Зелёный маркер", "green"), ("Синий маркер", "blue"), ("Удалить выделение", nil)]
            let actions = colors.map { name, color in
                UIAction(title: name, image: UIImage(systemName: color == nil ? "eraser" : "highlighter")) { [weak self] _ in self?.parent.onHighlight(range, color) }
            }
            return UIMenu(children: actions + suggestedActions)
        }
    }
}

struct ReadingPassageView: View {
    @Bindable var store: ReadingStore
    let passage: ReadingPassage
    var review = false
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 20) {
                Text(passage.title).font(.system(.title, design: .serif, weight: .bold)).id("\(passage.id)-title")
                if let subtitle = passage.subtitle { Text(subtitle).font(.subheadline) }
                ForEach(Array(passage.content.enumerated()), id: \.offset) { index, block in
                    HStack(alignment: .top, spacing: 12) {
                        if let label = block.label { Text(label).font(.headline).frame(minWidth: 20).accessibilityLabel("Section \(label)") }
                        PassageTextView(text: block.text,
                                        annotations: (store.active?.state.annotations ?? []).filter { $0.passage_id == passage.id && $0.block_index == index && $0.content_hash == store.active?.server.content_hash },
                                        size: block.type == "heading" ? store.preferences.fontSize + 2 : store.preferences.fontSize,
                                        theme: store.preferences.theme, readOnly: review || store.active?.server.terminal == true,
                                        onHighlight: { range, color in store.highlight(passage: passage, block: index, range: range, color: color) })
                    }.id("\(passage.id)-\(index)")
                }
            }.scrollTargetLayout().padding(20).padding(.bottom, review ? 24 : 160)
        }
        .scrollPosition(id: Binding(get: { store.active?.ui.passageAnchors[passage.id] }, set: { id in
            store.updateUI { $0.passageAnchors[passage.id] = id }
        }), anchor: .top)
        .background(store.preferences.theme.background)
        .foregroundStyle(store.preferences.theme.foreground)

    }
}

struct ReadingAssetView: View {
    let asset: ReadingAsset
    let store: ReadingStore
    @State private var bytes: Data?
    @State private var failed = false
    @State private var zoom = false
    var body: some View {
        Group {
            if let bytes, let image = UIImage(data: bytes) {
                Button { zoom = true } label: {
                    Image(uiImage: image).resizable().scaledToFit().background(.white)
                }.buttonStyle(.plain).accessibilityLabel("Схема задания. Открыть увеличение")
            } else if failed {
                VStack { Text("Не удалось загрузить схему. Повтори попытку."); Button("Повторить") { Task { await load() } } }.padding()
            } else { SwiftUI.ProgressView("Загружаем схему…").padding() }
        }
        .task(id: asset.sha256) { await load() }
        .sheet(isPresented: $zoom) {
            NavigationStack {
                if let bytes, let image = UIImage(data: bytes) { ReadingZoomImage(image: image).ignoresSafeArea(edges: .bottom).navigationTitle("Схема").navigationBarTitleDisplayMode(.inline).toolbar { Button("Готово") { zoom = false } } }
            }
        }
    }
    private func load() async {
        failed = false
        do { bytes = try await store.loadAsset(asset) }
        catch is CancellationError { }
        catch { failed = true }
    }
}
struct ReadingZoomImage: UIViewRepresentable {
    let image: UIImage
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeUIView(context: Context) -> ReadingImageScrollView {
        let view = ReadingImageScrollView(); view.delegate = context.coordinator
        view.imageView.image = image
        return view
    }
    func updateUIView(_ view: ReadingImageScrollView, context: Context) {
        view.imageView.image = image; view.setNeedsLayout()
    }
    final class Coordinator: NSObject, UIScrollViewDelegate {
        func viewForZooming(in scrollView: UIScrollView) -> UIView? { (scrollView as? ReadingImageScrollView)?.imageView }
    }
}
final class ReadingImageScrollView: UIScrollView {
    let imageView = UIImageView()
    override init(frame: CGRect) {
        super.init(frame: frame)
        minimumZoomScale = 1; maximumZoomScale = 6; backgroundColor = .white
        imageView.contentMode = .scaleAspectFit; addSubview(imageView)
        isAccessibilityElement = true; accessibilityLabel = "Схема задания"
        accessibilityCustomActions = [UIAccessibilityCustomAction(name: "Увеличить", target: self, selector: #selector(zoomIn)), UIAccessibilityCustomAction(name: "Уменьшить", target: self, selector: #selector(zoomOut))]
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }
    override func layoutSubviews() {
        super.layoutSubviews()
        if zoomScale == minimumZoomScale { imageView.frame = bounds; contentSize = bounds.size }
    }
    @objc private func zoomIn() -> Bool { setZoomScale(min(maximumZoomScale, zoomScale * 2), animated: !UIAccessibility.isReduceMotionEnabled); return true }
    @objc private func zoomOut() -> Bool { setZoomScale(max(minimumZoomScale, zoomScale / 2), animated: !UIAccessibility.isReduceMotionEnabled); return true }
}
