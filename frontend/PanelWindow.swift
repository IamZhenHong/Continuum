import Cocoa

class PanelWindow: NSWindow {
    
    init() {
        // Create a window with a specific style
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 300, height: 600),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        // Configure window properties
        self.title = "Continuum Panel"
        self.center()
        self.isMovableByWindowBackground = true
        self.isReleasedWhenClosed = false
        self.backgroundColor = NSColor.windowBackgroundColor
        
        // Set up the window level to keep it above other windows
        self.level = .floating
        
        // Add the main view controller
        self.contentViewController = PanelViewController()
        
        // Set up window position
        setupWindowPosition()
    }
    
    private func setupWindowPosition() {
        if let screen = NSScreen.main {
            let screenFrame = screen.visibleFrame
            let windowFrame = self.frame
            
            // Position the window on the right side of the screen
            let x = screenFrame.maxX - windowFrame.width
            let y = screenFrame.maxY - windowFrame.height
            
            self.setFrameOrigin(NSPoint(x: x, y: y))
        }
    }
    
    override func mouseDown(with event: NSEvent) {
        // Allow window dragging from anywhere
        self.performWindowDrag(with: event)
    }
} 