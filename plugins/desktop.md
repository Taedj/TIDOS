# TIDOS Plugin: Desktop Cross-Platform (v3.0)

## 1. Detection Rules
- **Signature Files**: `src-tauri/tauri.conf.json`, `electron-builder.json`, `windows/runner/`
- **Keywords**: `tauri`, `electron`, `flutter_desktop`

## 2. Initialization Steps
- Verify desktop build toolchain (`cmake`, `cargo`, `node`, `msvc` / `clang`).
- Check target OS build parameters (Windows, macOS, Linux).

## 3. Documentation to Generate
- `DESKTOP_ARCHITECTURE.md`: Document window management, IPC bridges, and local filesystem permissions.

## 4. Best Practices
- Isolate main process from renderer process via explicit IPC whitelist channels.
- Persist window position, dimensions, and state across restarts.

## 5. Coding Standards
- Restrict filesystem access to designated app data directory bounds.
- Use OS Keychain / Credential Manager for secure token storage.

## 6. Review & Quality Rules
- Validate zero insecure IPC `nodeIntegration: true` in Electron webPreferences.
- Verify native installer generation pipelines (`MSI`, `DMG`, `AppImage`).

## 7. Research Topics
- Tauri 2.0 mobile/desktop unification, Rust IPC performance, Flutter Desktop multi-window support.
