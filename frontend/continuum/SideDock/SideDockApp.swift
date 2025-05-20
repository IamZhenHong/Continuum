import SwiftUI

@main
struct SideDockApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentSize)
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private var startY: CGFloat = 0
    private var startWindowY: CGFloat = 0
    private var isDragging = false
    private var mainWindow: NSWindow?
    private var fullscreenPanel: NSPanel?
    private var isFullscreen = false
    private var visibilityTimer: Timer?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMainWindow()
        setupFullscreenPanel()
        setupObservers()
    }
    
    private func setupMainWindow() {
        if let window = NSApplication.shared.windows.first {
            mainWindow = window
            window.level = .popUpMenu
            window.backgroundColor = .clear
            window.isOpaque = false
            window.hasShadow = false
            window.styleMask = [.borderless, .fullSizeContentView]
            
            // Position window on the right side of the screen
            if let screen = NSScreen.main {
                let screenFrame = screen.visibleFrame
                let windowFrame = window.frame
                let newOrigin = NSPoint(
                    x: screenFrame.maxX - windowFrame.width - 10, // Add small margin from right edge
                    y: screenFrame.midY - (windowFrame.height / 2)
                )
                window.setFrameOrigin(newOrigin)
            }
            
            // Make window stay on top of other windows and stick to right side
            window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .transient, .ignoresCycle]
            
            // Enable default window dragging but constrain it
            window.isMovableByWindowBackground = true
            window.delegate = self
            
            setupDragHandling(for: window)
            
            // Add observer for screen changes
            NotificationCenter.default.addObserver(forName: NSApplication.didChangeScreenParametersNotification, object: NSApplication.shared, queue: .main) { [weak self] _ in
                self?.repositionWindow()
            }
        }
    }
    
    private func repositionWindow() {
        guard let window = mainWindow, let screen = NSScreen.main else { return }
        let screenFrame = screen.visibleFrame
        let windowFrame = window.frame
        let newOrigin = NSPoint(
            x: screenFrame.maxX - windowFrame.width - 10, // Add small margin from right edge
            y: screenFrame.midY - (windowFrame.height / 2)
        )
        window.setFrameOrigin(newOrigin)
    }
    
    private func setupFullscreenPanel() {
        let panel = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 40, height: 240),
            styleMask: [.borderless, .fullSizeContentView, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        
        panel.level = .popUpMenu
        panel.backgroundColor = .clear
        panel.isOpaque = false
        panel.hasShadow = false
        panel.isMovableByWindowBackground = false
        panel.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .transient, .ignoresCycle]
        panel.ignoresMouseEvents = false
        panel.acceptsMouseMovedEvents = true
        panel.becomesKeyOnlyIfNeeded = true
        panel.hidesOnDeactivate = false
        
        let hostingView = NSHostingView(rootView: ContentView())
        panel.contentView = hostingView
        
        fullscreenPanel = panel
        panel.orderOut(nil)
    }
    
    private func setupObservers() {
        // Watch for our own window's fullscreen state
        NotificationCenter.default.addObserver(forName: NSWindow.didEnterFullScreenNotification, object: nil, queue: .main) { [weak self] _ in
            self?.handleFullscreenChange(isFullscreen: true)
        }
        
        NotificationCenter.default.addObserver(forName: NSWindow.didExitFullScreenNotification, object: nil, queue: .main) { [weak self] _ in
            self?.handleFullscreenChange(isFullscreen: false)
        }
        
        // Watch for other applications entering fullscreen
        NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.activeSpaceDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
            self?.checkForFullscreenApps()
        }
        
        // Add observer for screen changes
        NotificationCenter.default.addObserver(forName: NSApplication.didChangeScreenParametersNotification, object: NSApplication.shared, queue: .main) { [weak self] _ in
            if self?.isFullscreen == true {
                self?.positionFullscreenPanel()
            }
        }
    }
    
    private func checkForFullscreenApps() {
        let options = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
        let windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] ?? []
        
        let isAnyAppFullscreen = windowList.contains { window in
            guard let bounds = window[kCGWindowBounds as String] as? [String: Any],
                  let screen = NSScreen.main else { return false }
            
            let windowFrame = CGRect(
                x: bounds["X"] as? CGFloat ?? 0,
                y: bounds["Y"] as? CGFloat ?? 0,
                width: bounds["Width"] as? CGFloat ?? 0,
                height: bounds["Height"] as? CGFloat ?? 0
            )
            
            return windowFrame.width >= screen.frame.width && windowFrame.height >= screen.frame.height
        }
        
        handleFullscreenChange(isFullscreen: isAnyAppFullscreen)
    }
    
    private func handleFullscreenChange(isFullscreen: Bool) {
        self.isFullscreen = isFullscreen
        if isFullscreen {
            mainWindow?.orderOut(nil)
            fullscreenPanel?.orderFront(nil)
            positionFullscreenPanel()
            
            // Force panel to front and ensure it stays visible
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
                self?.fullscreenPanel?.orderFront(nil)
                self?.fullscreenPanel?.level = .floating // Ensure it stays above fullscreen windows
            }
        } else {
            mainWindow?.orderFront(nil)
            fullscreenPanel?.orderOut(nil)
        }
    }
    
    private func positionFullscreenPanel() {
        guard let panel = fullscreenPanel, let screen = NSScreen.main else { return }
        let screenFrame = screen.frame
        let panelFrame = panel.frame
        let newOrigin = NSPoint(
            x: screenFrame.maxX - panelFrame.width - 10, // Add small margin from right edge
            y: screenFrame.midY - (panelFrame.height / 2)
        )
        panel.setFrameOrigin(newOrigin)
    }
    
    private func setupDragHandling(for window: NSWindow) {
        NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDragged]) { [weak self] event in
            if self?.isDragging == true {
                self?.handleDrag(event, window: window)
                return nil
            }
            return event
        }
        
        NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown]) { [weak self] event in
            self?.startY = event.locationInWindow.y
            self?.startWindowY = window.frame.origin.y
            self?.isDragging = true
            return event
        }
        
        NSEvent.addLocalMonitorForEvents(matching: [.leftMouseUp]) { [weak self] event in
            self?.isDragging = false
            return event
        }
    }
    
    private func handleDrag(_ event: NSEvent, window: NSWindow) {
        guard let screen = NSScreen.main else { return }
        
        let deltaY = event.locationInWindow.y - startY
        let newY = startWindowY + deltaY
        
        // Keep the window within screen bounds with margin
        let margin: CGFloat = 20
        let minY = screen.visibleFrame.minY + margin
        let maxY = screen.visibleFrame.maxY - window.frame.height - margin
        let clampedY = max(minY, min(maxY, newY))
        
        // Update window position, keeping it fixed to the right edge
        var frame = window.frame
        frame.origin = NSPoint(
            x: screen.visibleFrame.maxX - frame.width - 10, // Add small margin from right edge
            y: clampedY
        )
        window.setFrame(frame, display: true)
    }
}

extension AppDelegate: NSWindowDelegate {
    func windowWillMove(_ notification: Notification) {
        guard let window = notification.object as? NSWindow,
              let screen = NSScreen.main else { return }
        
        // Get the current frame
        var frame = window.frame
        
        // Keep the x position fixed at the right edge
        frame.origin.x = screen.visibleFrame.maxX - frame.width
        
        // Ensure y position stays within screen bounds with a small margin
        let margin: CGFloat = 20
        let minY = screen.visibleFrame.minY + margin
        let maxY = screen.visibleFrame.maxY - frame.height - margin
        frame.origin.y = max(minY, min(maxY, frame.origin.y))
        
        // Apply the new frame
        window.setFrame(frame, display: true)
    }
    
    // Prevent window from being resized
    func windowWillResize(_ sender: NSWindow, to frameSize: NSSize) -> NSSize {
        return sender.frame.size
    }
} 