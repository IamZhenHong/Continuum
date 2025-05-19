import Foundation

class SettingsManager {
    static let shared = SettingsManager()
    
    private let defaults = UserDefaults.standard
    
    private enum Keys {
        static let windowPosition = "windowPosition"
        static let autoHide = "autoHide"
        static let transparency = "transparency"
        static let defaultAction = "defaultAction"
    }
    
    private init() {}
    
    // Window position
    var windowPosition: CGPoint {
        get {
            let x = defaults.double(forKey: Keys.windowPosition + "X")
            let y = defaults.double(forKey: Keys.windowPosition + "Y")
            return CGPoint(x: x, y: y)
        }
        set {
            defaults.set(newValue.x, forKey: Keys.windowPosition + "X")
            defaults.set(newValue.y, forKey: Keys.windowPosition + "Y")
        }
    }
    
    // Auto-hide setting
    var autoHide: Bool {
        get { defaults.bool(forKey: Keys.autoHide) }
        set { defaults.set(newValue, forKey: Keys.autoHide) }
    }
    
    // Window transparency
    var transparency: Double {
        get { defaults.double(forKey: Keys.transparency) }
        set { defaults.set(newValue, forKey: Keys.transparency) }
    }
    
    // Default action for dropped files
    var defaultAction: FileAction {
        get {
            if let rawValue = defaults.string(forKey: Keys.defaultAction),
               let action = FileAction(rawValue: rawValue) {
                return action
            }
            return .open
        }
        set { defaults.set(newValue.rawValue, forKey: Keys.defaultAction) }
    }
}

enum FileAction: String {
    case open = "open"
    case move = "move"
    case copy = "copy"
    case rename = "rename"
    case upload = "upload"
} 