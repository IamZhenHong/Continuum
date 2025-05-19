import Cocoa

@main
class AppDelegate: NSObject, NSApplicationDelegate {
    
    private var statusBarController: StatusBarController?
    private var panelWindow: PanelWindow?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Initialize the status bar controller
        statusBarController = StatusBarController()
        
        // Initialize the panel window
        panelWindow = PanelWindow()
        panelWindow?.makeKeyAndOrderFront(nil)
        
        // Set up notification center
        setupNotificationCenter()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Clean up resources
    }
    
    private func setupNotificationCenter() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(togglePanel),
            name: NSNotification.Name("TogglePanel"),
            object: nil
        )
    }
    
    @objc private func togglePanel() {
        if let window = panelWindow {
            if window.isVisible {
                window.orderOut(nil)
            } else {
                window.makeKeyAndOrderFront(nil)
            }
        }
    }
} 