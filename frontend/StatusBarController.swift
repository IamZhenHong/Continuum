import Cocoa

class StatusBarController {
    private var statusBar: NSStatusBar
    private var statusItem: NSStatusItem
    private var popover: NSPopover
    
    init() {
        statusBar = NSStatusBar.system
        statusItem = statusBar.statusItem(withLength: NSStatusItem.variableLength)
        
        if let statusBarButton = statusItem.button {
            statusBarButton.image = NSImage(systemSymbolName: "sidebar.right", accessibilityDescription: "Continuum Panel")
            statusBarButton.action = #selector(togglePopover)
            statusBarButton.target = self
        }
        
        popover = NSPopover()
        popover.contentViewController = StatusBarMenuViewController()
        popover.behavior = .transient
    }
    
    @objc private func togglePopover() {
        if let button = statusItem.button {
            if popover.isShown {
                popover.performClose(nil)
            } else {
                popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            }
        }
    }
}

class StatusBarMenuViewController: NSViewController {
    override func loadView() {
        let view = NSView(frame: NSRect(x: 0, y: 0, width: 200, height: 100))
        
        let stackView = NSStackView()
        stackView.orientation = .vertical
        stackView.alignment = .leading
        stackView.spacing = 8
        stackView.edgeInsets = NSEdgeInsets(top: 8, left: 8, bottom: 8, right: 8)
        
        let showPanelButton = NSButton(title: "Show Panel", target: self, action: #selector(showPanel))
        showPanelButton.bezelStyle = .texturedRounded
        
        let quitButton = NSButton(title: "Quit", target: self, action: #selector(quit))
        quitButton.bezelStyle = .texturedRounded
        
        stackView.addArrangedSubview(showPanelButton)
        stackView.addArrangedSubview(quitButton)
        
        view.addSubview(stackView)
        stackView.translatesAutoresizingMaskIntoConstraints = false
        
        NSLayoutConstraint.activate([
            stackView.topAnchor.constraint(equalTo: view.topAnchor),
            stackView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            stackView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            stackView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        
        self.view = view
    }
    
    @objc private func showPanel() {
        NotificationCenter.default.post(name: NSNotification.Name("TogglePanel"), object: nil)
    }
    
    @objc private func quit() {
        NSApplication.shared.terminate(nil)
    }
} 