import SwiftUI

struct AuthView: View {
    @State private var isLoggedIn = false
    @State private var showSignup = false
    @State private var email = ""
    @State private var password = ""
    @State private var username = ""
    @State private var showSettings = false
    @State private var selectedTheme = "System"
    @State private var notificationsEnabled = true
    
    let themes = ["System", "Light", "Dark"]
    
    var body: some View {
        if isLoggedIn {
            VStack {
                HStack {
                    Text("Welcome, \(username)")
                        .font(.title2)
                    Spacer()
                    Button(action: { showSettings.toggle() }) {
                        Image(systemName: "gear")
                            .font(.title2)
                    }
                }
                .padding()
                
                if showSettings {
                    settingsView
                }
                
                Spacer()
                
                Button("Launch SideDock") {
                    // Send notification to launch the sidedock
                    NotificationCenter.default.post(name: NSNotification.Name("LaunchSideDock"), object: nil)
                }
                .buttonStyle(.borderedProminent)
                .padding()
            }
        } else {
            VStack(spacing: 20) {
                Text("Welcome to SideDock")
                    .font(.largeTitle)
                    .bold()
                
                if showSignup {
                    signupView
                } else {
                    loginView
                }
                
                Button(action: { showSignup.toggle() }) {
                    Text(showSignup ? "Already have an account? Login" : "Don't have an account? Sign up")
                        .foregroundColor(.blue)
                }
            }
            .padding()
            .frame(maxWidth: 400)
        }
    }
    
    private var loginView: some View {
        VStack(spacing: 15) {
            TextField("Email", text: $email)
                .textFieldStyle(.roundedBorder)
                .textContentType(.emailAddress)
                .textCase(.lowercase)
                .disableAutocorrection(true)
            
            SecureField("Password", text: $password)
                .textFieldStyle(.roundedBorder)
                .textContentType(.password)
            
            Button("Login") {
                // Here we'll add actual authentication logic
                isLoggedIn = true
                username = "User" // This will be replaced with actual user data
            }
            .buttonStyle(.borderedProminent)
        }
    }
    
    private var signupView: some View {
        VStack(spacing: 15) {
            TextField("Username", text: $username)
                .textFieldStyle(.roundedBorder)
                .textContentType(.username)
                .textCase(.lowercase)
                .disableAutocorrection(true)
            
            TextField("Email", text: $email)
                .textFieldStyle(.roundedBorder)
                .textContentType(.emailAddress)
                .textCase(.lowercase)
                .disableAutocorrection(true)
            
            SecureField("Password", text: $password)
                .textFieldStyle(.roundedBorder)
                .textContentType(.newPassword)
            
            Button("Sign Up") {
                // Here we'll add actual signup logic
                isLoggedIn = true
            }
            .buttonStyle(.borderedProminent)
        }
    }
    
    private var settingsView: some View {
        Form {
            Section(header: Text("Appearance")) {
                Picker("Theme", selection: $selectedTheme) {
                    ForEach(themes, id: \.self) { theme in
                        Text(theme)
                    }
                }
            }
            
            Section(header: Text("Notifications")) {
                Toggle("Enable Notifications", isOn: $notificationsEnabled)
            }
            
            Section {
                Button("Logout") {
                    isLoggedIn = false
                    email = ""
                    password = ""
                    username = ""
                }
                .foregroundColor(.red)
            }
        }
        .padding()
    }
}

#Preview {
    AuthView()
} 