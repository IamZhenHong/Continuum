import SwiftUI
import UniformTypeIdentifiers
import QuickLook

// MARK: - Theme
struct Theme {
    static let primary = Color.blue
    static let secondary = Color.gray.opacity(0.8)
    static let background = Color(NSColor.windowBackgroundColor)
    static let accent = Color.blue.opacity(0.2)
    static let text = Color.primary
    static let textSecondary = Color.secondary
    
    static let cornerRadius: CGFloat = 12
    static let padding: CGFloat = 16
    static let spacing: CGFloat = 12
}

// MARK: - Window Controller
class ImagePreviewWindowController: NSWindowController {
    init(url: URL) {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = url.lastPathComponent
        window.center()
        window.backgroundColor = NSColor.windowBackgroundColor
        
        let hostingView = NSHostingView(rootView: ImagePreviewView(url: url))
        window.contentView = hostingView
        
        super.init(window: window)
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func showWindow(_ sender: Any?) {
        super.showWindow(sender)
        window?.makeKeyAndOrderFront(nil)
    }
}

// MARK: - Content View
struct ContentView: View {
    @State private var isTargeted = false
    @State private var isProcessing = false
    @State private var showSettings = false
    @State private var recentFiles: [FileItem] = []
    @State private var isExpanded = false
    @State private var selectedFile: FileItem?
    @State private var previewWindows: [URL: ImagePreviewWindowController] = [:]
    @State private var hoveredFile: FileItem?
    
    var body: some View {
        HStack(spacing: 0) {
            // Expand/Collapse button
            Button(action: { 
                withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    isExpanded.toggle()
                    // Update window size when expanding/collapsing
                    if let window = NSApplication.shared.windows.first {
                        let newWidth = isExpanded ? 340 : 40
                        let newHeight = 600
                        
                        // Get screen frame
                        if let screen = NSScreen.main {
                            let screenFrame = screen.frame
                            let currentFrame = window.frame
                            
                            // Calculate new frame
                            let newFrame = NSRect(
                                x: screenFrame.maxX - CGFloat(newWidth) - 10,
                                y: currentFrame.origin.y,
                                width: CGFloat(newWidth),
                                height: CGFloat(newHeight)
                            )
                            
                            window.setFrame(newFrame, display: true)
                            
                            // Ensure window stays within screen bounds
                            if newFrame.maxX > screenFrame.maxX {
                                let adjustedFrame = NSRect(
                                    x: screenFrame.maxX - CGFloat(newWidth) - 10,
                                    y: currentFrame.origin.y,
                                    width: CGFloat(newWidth),
                                    height: CGFloat(newHeight)
                                )
                                window.setFrame(adjustedFrame, display: true)
                            }
                        }
                    }
                }
            }) {
                Image(systemName: isExpanded ? "chevron.left" : "chevron.right")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(Theme.secondary)
                    .frame(width: 24, height: 24)
                    .background(
                        Circle()
                            .fill(Theme.background)
                            .shadow(color: Color.black.opacity(0.1), radius: 2, x: 0, y: 1)
                    )
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 8)
            
            // Expanded view
            if isExpanded {
                VStack(spacing: 0) {
                    // Header
                    HStack {
                        Text("Recent Files")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(Theme.text)
                        Spacer()
                        Button(action: { showSettings.toggle() }) {
                            Image(systemName: "gear")
                                .font(.system(size: 16))
                                .foregroundColor(Theme.secondary)
                                .frame(width: 32, height: 32)
                                .background(
                                    Circle()
                                        .fill(Theme.background)
                                        .shadow(color: Color.black.opacity(0.1), radius: 2, x: 0, y: 1)
                                )
                        }
                        .buttonStyle(.plain)
                        .popover(isPresented: $showSettings) {
                            SettingsView()
                        }
                    }
                    .padding(Theme.padding)
                    .background(Theme.background)
                    
                    // File list
                    ScrollView {
                        LazyVStack(spacing: 8) {
                            ForEach(recentFiles) { file in
                                FileRow(file: file, isHovered: hoveredFile?.id == file.id)
                                    .onHover { isHovered in
                                        withAnimation(.easeInOut(duration: 0.2)) {
                                            hoveredFile = isHovered ? file : nil
                                        }
                                    }
                                    .onTapGesture {
                                        if isImageFile(file.url) {
                                            openImagePreview(file.url)
                                        } else {
                                            openFile(file.url)
                                        }
                                    }
                                    .contextMenu {
                                        if isImageFile(file.url) {
                                            Button("Preview") {
                                                openImagePreview(file.url)
                                            }
                                        }
                                        Button("Open") {
                                            openFile(file.url)
                                        }
                                        Button("Show in Finder") {
                                            NSWorkspace.shared.activateFileViewerSelecting([file.url])
                                        }
                                        Button("Copy Path") {
                                            NSPasteboard.general.clearContents()
                                            NSPasteboard.general.setString(file.url.path, forType: .string)
                                        }
                                    }
                            }
                        }
                        .padding(.horizontal, Theme.padding)
                        .padding(.vertical, 8)
                    }
                }
                .frame(width: 300, height: 400)
                .background(Theme.background)
            }
            
            // Main drop zone
            ZStack {
                // Background
                RoundedRectangle(cornerRadius: Theme.cornerRadius)
                    .fill(Theme.background)
                    .frame(width: 40)
                    .overlay(
                        RoundedRectangle(cornerRadius: Theme.cornerRadius)
                            .stroke(Theme.secondary, lineWidth: 1)
                    )
                
                // Content
                VStack(spacing: Theme.spacing) {
                    if isTargeted {
                        Image(systemName: "arrow.down.doc")
                            .font(.system(size: 20, weight: .medium))
                            .foregroundColor(Theme.primary)
                            .scaleEffect(1.1)
                            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: isTargeted)
                        
                        Text("Drop Here")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundColor(Theme.primary)
                            .animation(.easeInOut(duration: 0.2), value: isTargeted)
                    } else {
                        Text("Continuum")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(Theme.secondary)
                            .rotationEffect(.degrees(-90))
                            .animation(.easeInOut(duration: 0.2), value: isTargeted)
                    }
                }
            }
            .frame(width: 40, height: 400)
            .background(
                RoundedRectangle(cornerRadius: Theme.cornerRadius)
                    .fill(isTargeted ? Theme.accent : Color.clear)
                    .animation(.easeInOut(duration: 0.2), value: isTargeted)
            )
            .onDrop(of: [.fileURL, .image, .png, .jpeg, .tiff], isTargeted: $isTargeted) { providers in
                print("Drop received with \(providers.count) providers")
                isProcessing = true
                handleDrop(providers: providers)
                return true
            }
            .onChange(of: isTargeted) { newValue in
                if !newValue {
                    isProcessing = false
                }
            }
        }
        .frame(height: 400)
        .frame(maxWidth: .infinity, alignment: .trailing)
        .onAppear {
            // Set up window size observer
            if let window = NSApplication.shared.windows.first {
                NotificationCenter.default.addObserver(forName: NSWindow.didResizeNotification, object: window, queue: .main) { _ in
                    if let screen = NSScreen.main {
                        let screenFrame = screen.frame
                        let windowFrame = window.frame
                        let newOrigin = NSPoint(
                            x: screenFrame.maxX - windowFrame.width - 10,
                            y: screenFrame.midY - (windowFrame.height / 2)
                        )
                        window.setFrameOrigin(newOrigin)
                    }
                }
            }
        }
    }
    
    private func openImagePreview(_ url: URL) {
        if let existingWindow = previewWindows[url] {
            existingWindow.showWindow(nil)
        } else {
            let windowController = ImagePreviewWindowController(url: url)
            previewWindows[url] = windowController
            windowController.showWindow(nil)
            
            // Clean up the window controller when the window is closed
            NotificationCenter.default.addObserver(forName: NSWindow.willCloseNotification, object: windowController.window, queue: .main) { _ in
                previewWindows.removeValue(forKey: url)
            }
        }
    }
    
    private func handleDrop(providers: [NSItemProvider]) {
        for provider in providers {
            print("Processing provider with types: \(provider.registeredTypeIdentifiers)")
            
            // Try file URL first
            if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
                provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { (data, error) in
                    if let error = error {
                        print("Error loading file URL: \(error)")
                        return
                    }
                    
                    if let urlData = data as? Data,
                       let url = URL(dataRepresentation: urlData, relativeTo: nil) {
                        print("Received file URL: \(url.path)")
                        DispatchQueue.main.async {
                            FileProcessor.shared.processFile(at: url)
                            addFileToRecent(url)
                            isProcessing = false
                        }
                    }
                }
            }
            // Try image data
            else if provider.hasItemConformingToTypeIdentifier(UTType.image.identifier) ||
                    provider.hasItemConformingToTypeIdentifier(UTType.png.identifier) ||
                    provider.hasItemConformingToTypeIdentifier(UTType.jpeg.identifier) {
                
                let typeIdentifier = provider.registeredTypeIdentifiers.first ?? UTType.image.identifier
                print("Loading image with type: \(typeIdentifier)")
                
                provider.loadItem(forTypeIdentifier: typeIdentifier, options: nil) { (data, error) in
                    if let error = error {
                        print("Error loading image: \(error)")
                        return
                    }
                    
                    if let imageData = data as? Data {
                        print("Received image data of size: \(imageData.count) bytes")
                        saveAndProcessImage(imageData)
                    } else if let url = data as? URL {
                        print("Received image URL: \(url.path)")
                        DispatchQueue.main.async {
                            FileProcessor.shared.processFile(at: url)
                            addFileToRecent(url)
                            isProcessing = false
                        }
                    } else if let image = data as? NSImage {
                        print("Received NSImage directly")
                        if let tiffData = image.tiffRepresentation,
                           let bitmapImage = NSBitmapImageRep(data: tiffData),
                           let pngData = bitmapImage.representation(using: .png, properties: [:]) {
                            saveAndProcessImage(pngData)
                        }
                    } else {
                        print("Unknown data type: \(type(of: data))")
                        DispatchQueue.main.async {
                            isProcessing = false
                        }
                    }
                }
            }
        }
    }
    
    private func saveAndProcessImage(_ imageData: Data) {
        let tempDir = FileManager.default.temporaryDirectory
        let fileName = "dropped_image_\(Date().timeIntervalSince1970).png"
        let fileURL = tempDir.appendingPathComponent(fileName)
        
        do {
            try imageData.write(to: fileURL)
            print("Saved image to: \(fileURL.path)")
            DispatchQueue.main.async {
                FileProcessor.shared.processFile(at: fileURL)
                addFileToRecent(fileURL)
                isProcessing = false
            }
        } catch {
            print("Error saving image: \(error)")
            DispatchQueue.main.async {
                isProcessing = false
            }
        }
    }
    
    private func addFileToRecent(_ url: URL) {
        print("Adding file to recent: \(url.path)")
        let newFile = FileItem(url: url, date: Date())
        recentFiles.insert(newFile, at: 0)
        if recentFiles.count > 10 {
            recentFiles.removeLast()
        }
    }
    
    private func isImageFile(_ url: URL) -> Bool {
        let imageExtensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff"]
        return imageExtensions.contains(url.pathExtension.lowercased())
    }
    
    private func fileIcon(for url: URL) -> String {
        if url.pathExtension.lowercased() == "pdf" {
            return "doc.text"
        } else if isImageFile(url) {
            return "photo"
        } else if ["mp4", "mov", "avi"].contains(url.pathExtension.lowercased()) {
            return "film"
        } else {
            return "doc"
        }
    }
    
    private func openFile(_ url: URL) {
        NSWorkspace.shared.open(url)
    }
}

// MARK: - File Row
struct FileRow: View {
    let file: FileItem
    let isHovered: Bool
    
    var body: some View {
        HStack(spacing: Theme.spacing) {
            if isImageFile(file.url) {
                if let image = NSImage(contentsOf: file.url) {
                    Image(nsImage: image)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(width: 40, height: 40)
                        .cornerRadius(8)
                        .shadow(color: Color.black.opacity(0.1), radius: 2, x: 0, y: 1)
                } else {
                    Image(systemName: "photo")
                        .font(.system(size: 20))
                        .foregroundColor(Theme.secondary)
                        .frame(width: 40, height: 40)
                        .background(Theme.background)
                        .cornerRadius(8)
                }
            } else {
                Image(systemName: fileIcon(for: file.url))
                    .font(.system(size: 20))
                    .foregroundColor(Theme.secondary)
                    .frame(width: 40, height: 40)
                    .background(Theme.background)
                    .cornerRadius(8)
            }
            
            VStack(alignment: .leading, spacing: 4) {
                Text(file.url.lastPathComponent)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(Theme.text)
                    .lineLimit(1)
                Text(file.date, style: .time)
                    .font(.system(size: 12))
                    .foregroundColor(Theme.textSecondary)
            }
            
            Spacer()
            
            Image(systemName: "arrow.right.circle.fill")
                .font(.system(size: 16))
                .foregroundColor(Theme.primary)
                .opacity(isHovered ? 1 : 0.7)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: Theme.cornerRadius)
                .fill(isHovered ? Theme.accent : Theme.background)
        )
        .overlay(
            RoundedRectangle(cornerRadius: Theme.cornerRadius)
                .stroke(Theme.secondary.opacity(0.3), lineWidth: 1)
        )
    }
    
    private func isImageFile(_ url: URL) -> Bool {
        let imageExtensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff"]
        return imageExtensions.contains(url.pathExtension.lowercased())
    }
    
    private func fileIcon(for url: URL) -> String {
        if url.pathExtension.lowercased() == "pdf" {
            return "doc.text"
        } else if isImageFile(url) {
            return "photo"
        } else if ["mp4", "mov", "avi"].contains(url.pathExtension.lowercased()) {
            return "film"
        } else {
            return "doc"
        }
    }
}

// MARK: - Image Preview View
struct ImagePreviewView: View {
    let url: URL
    @State private var image: NSImage?
    
    var body: some View {
        Group {
            if let image = image {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Theme.background)
            } else {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .onAppear {
            loadImage()
        }
    }
    
    private func loadImage() {
        DispatchQueue.global(qos: .userInitiated).async {
            if let loadedImage = NSImage(contentsOf: url) {
                DispatchQueue.main.async {
                    self.image = loadedImage
                }
            }
        }
    }
}

// MARK: - Settings View
struct SettingsView: View {
    @State private var autoHide = false
    @State private var transparency: Double = 0.1
    @State private var defaultAction: FileAction = .open
    
    var body: some View {
        VStack(spacing: Theme.spacing) {
            Text("Settings")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Theme.text)
                .padding(.top, Theme.padding)
            
            Form {
                Toggle("Auto-hide", isOn: $autoHide)
                    .toggleStyle(.switch)
                
                VStack(alignment: .leading, spacing: 8) {
                    Text("Transparency")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(Theme.textSecondary)
                    Slider(value: $transparency, in: 0...1)
                }
                
                VStack(alignment: .leading, spacing: 8) {
                    Text("Default Action")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(Theme.textSecondary)
                    Picker("", selection: $defaultAction) {
                        Text("Open").tag(FileAction.open)
                        Text("Move").tag(FileAction.move)
                        Text("Copy").tag(FileAction.copy)
                        Text("Rename").tag(FileAction.rename)
                        Text("Upload").tag(FileAction.upload)
                    }
                    .pickerStyle(.menu)
                }
            }
            .padding(Theme.padding)
        }
        .frame(width: 300)
        .background(Theme.background)
    }
}

struct FileItem: Identifiable {
    let id = UUID()
    let url: URL
    let date: Date
}

#Preview {
    ContentView()
} 

