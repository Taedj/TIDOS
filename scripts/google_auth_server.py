"""TIDOS Firebase Google Authentication Server.

Starts a local web server on localhost:8766, opens the browser to sign in
with Google / Gmail via Firebase Web SDK, captures the authenticated tokens
and user profile, and persists the session to ~/.tidos/tidos-session.json.

Exit codes:
  0 = Successfully authenticated with Google
  1 = Authentication failed or aborted
  2 = Configuration or binding error
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser

PORT = 8766
HOST = "localhost"
TIMEOUT_SECONDS = 180

SESSION_DIR = os.path.join(os.path.expanduser("~"), ".tidos")
SESSION_FILE = os.path.join(SESSION_DIR, "tidos-session.json")

# Firebase Web App Config from config/firebase.md
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDzbyda_7ygLaWtqjLZtiHrqSd0b_CYBQk",
    "authDomain": "tidos-framework.firebaseapp.com",
    "projectId": "tidos-framework",
    "storageBucket": "tidos-framework.firebasestorage.app",
    "messagingSenderId": "640232479990",
    "appId": "1:640232479990:web:dd6117b3d8599ac295a0d7",
}

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TIDOS Authentication | Sign in with Google</title>
  <style>
    :root {
      --bg: #0a0d14;
      --card-bg: rgba(18, 24, 38, 0.85);
      --border: rgba(255, 255, 255, 0.08);
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --success: #10b981;
      --error: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      background-image: 
        radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 40%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .auth-card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 40px;
      width: 100%;
      max-width: 440px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    .auth-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
    }
    .badge {
      display: inline-block;
      padding: 4px 12px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      border-radius: 9999px;
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
      margin-bottom: 16px;
    }
    h1 {
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
    }
    p.subtitle {
      font-size: 14px;
      color: var(--text-muted);
      margin-bottom: 28px;
      line-height: 1.5;
    }
    .google-btn {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: #ffffff;
      color: #1f2937;
      font-size: 15px;
      font-weight: 600;
      padding: 14px 20px;
      border-radius: 10px;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .google-btn:hover {
      background: #f9fafb;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .google-btn:active {
      transform: translateY(0);
    }
    .google-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }
    .google-icon {
      width: 20px;
      height: 20px;
    }
    .status-box {
      margin-top: 24px;
      padding: 16px;
      border-radius: 10px;
      font-size: 13px;
      line-height: 1.4;
      display: none;
    }
    .status-box.success {
      display: block;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
    }
    .status-box.error {
      display: block;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #f87171;
    }
    .status-box.loading {
      display: block;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #60a5fa;
    }
    .user-info {
      margin-top: 12px;
      font-weight: 600;
      color: #fff;
    }
    .footer-note {
      margin-top: 24px;
      font-size: 12px;
      color: var(--text-muted);
      opacity: 0.8;
    }
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,0.3);
      border-radius: 50%;
      border-top-color: currentColor;
      animation: spin 0.8s linear infinite;
      vertical-align: middle;
      margin-right: 6px;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>

  <script type="module">
    import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js';
    import { getAuth, signInWithPopup, GoogleAuthProvider } from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js';

    const firebaseConfig = __FIREBASE_CONFIG__;
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    const provider = new GoogleAuthProvider();
    provider.addScope('email');
    provider.addScope('profile');
    provider.setCustomParameters({ prompt: 'select_account' });

    const btn = document.getElementById('loginBtn');
    const statusBox = document.getElementById('statusBox');

    function setStatus(type, msg, html = '') {
      statusBox.className = 'status-box ' + type;
      statusBox.innerHTML = msg + (html ? '<div class="user-info">' + html + '</div>' : '');
    }

    async function handleLogin() {
      btn.disabled = true;
      setStatus('loading', '<span class="spinner"></span> Opening Google Sign-In...');
      try {
        const result = await signInWithPopup(auth, provider);
        const user = result.user;
        const idToken = await user.getIdToken();
        const refreshToken = user.stsTokenManager?.refreshToken || user.refreshToken || '';
        
        setStatus('loading', '<span class="spinner"></span> Finalizing TIDOS session...');

        const payload = {
          email: user.email,
          displayName: user.displayName || '',
          localId: user.uid,
          idToken: idToken,
          refreshToken: refreshToken,
          providerId: 'google.com',
          photoURL: user.photoURL || '',
          emailVerified: user.emailVerified
        };

        const resp = await fetch('/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (resp.ok) {
          btn.style.display = 'none';
          setStatus('success', 
            '<strong>Authentication Successful!</strong><br>Connected to TIDOS with Google.',
            `${user.displayName || 'User'} (${user.email})<br><br><span style="font-size:12px;opacity:0.9;">You can safely close this browser window and return to your terminal.</span>`
          );
        } else {
          const errText = await resp.text();
          btn.disabled = false;
          setStatus('error', 'Server error saving session: ' + errText);
        }
      } catch (err) {
        btn.disabled = false;
        console.error(err);
        let msg = err.message || 'Authentication error';
        if (err.code === 'auth/popup-closed-by-user') {
          msg = 'Sign-in cancelled. Please click the button to try again.';
        }
        setStatus('error', msg);
      }
    }

    btn.addEventListener('click', handleLogin);
    // Auto-trigger on page load
    setTimeout(handleLogin, 500);
  </script>
</head>
<body>
  <div class="auth-card">
    <div class="badge">TIDOS Operating System</div>
    <h1>Sign In with Google</h1>
    <p class="subtitle">Authenticate with your Gmail / Google account to unlock TIDOS platform services.</p>

    <button id="loginBtn" class="google-btn">
      <svg class="google-icon" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
      </svg>
      Sign in with Google / Gmail
    </button>

    <div id="statusBox" class="status-box"></div>

    <div class="footer-note">
      Project: tidos-framework &bull; Firebase Zero-Trust Auth
    </div>
  </div>
</body>
</html>
"""


class AuthServerHandler(http.server.BaseHTTPRequestHandler):
    session_result = None

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP logs
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/login":
            html = HTML_PAGE.replace(
                "__FIREBASE_CONFIG__", json.dumps(FIREBASE_CONFIG)
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                email = data.get("email")
                uid = data.get("localId")
                refresh_token = data.get("refreshToken")
                id_token = data.get("idToken")

                if not email or not refresh_token:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing email or refreshToken")
                    return

                # Build session file
                session = {
                    "refreshToken": refresh_token,
                    "idToken": id_token,
                    "localId": uid,
                    "email": email,
                    "displayName": data.get("displayName", ""),
                    "photoURL": data.get("photoURL", ""),
                    "providerId": "google.com",
                    "emailVerified": data.get("emailVerified", True),
                    "authenticatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }

                os.makedirs(SESSION_DIR, exist_ok=True)
                with open(SESSION_FILE, "w", encoding="utf-8") as f:
                    json.dump(session, f, indent=2)

                AuthServerHandler.session_result = session

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_auth_flow(port=PORT, timeout=TIMEOUT_SECONDS):
    print("[TIDOS AUTH] Starting Google Authentication service...")
    try:
        server = socketserver.TCPServer((HOST, port), AuthServerHandler)
        server.allow_reuse_address = True
    except Exception as e:
        print(f"[TIDOS AUTH] Error binding to {HOST}:{port}: {e}", file=sys.stderr)
        return 2

    url = f"http://{HOST}:{port}/"
    print(f"[TIDOS AUTH] Opening browser to sign in: {url}")
    print("[TIDOS AUTH] Please select your Gmail / Google account in the browser window.")

    # Open the browser
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    # Wait for callback or timeout
    start_time = time.time()
    server.timeout = 1.0

    try:
        while time.time() - start_time < timeout:
            server.handle_request()
            if AuthServerHandler.session_result is not None:
                s = AuthServerHandler.session_result
                print(f"[TIDOS AUTH] Authenticated: {s.get('email')} (uid: {s.get('localId')}, provider: google.com)")
                print(f"[TIDOS AUTH] Session saved to {SESSION_FILE} (remember-me active).")
                server.server_close()
                return 0
        print("[TIDOS AUTH] Authentication timed out. No response received.", file=sys.stderr)
        server.server_close()
        return 1
    except KeyboardInterrupt:
        print("\n[TIDOS AUTH] Authentication cancelled by user.", file=sys.stderr)
        server.server_close()
        return 1


if __name__ == "__main__":
    port_arg = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    sys.exit(run_auth_flow(port=port_arg))
