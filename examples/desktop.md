# TIDOS + Desktop Application Integration Example

## Project Type
Cross-platform desktop application using Tauri (Rust) or Electron.

## TIDOS Connection

```bash
cd desktop_app
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/desktop.md` - Desktop specification
- `plugins/react.md` or `plugins/flutter.md` - UI framework
- `plugins/docker.md` - Containerization (if used)

## Key Rules Applied

- Native API access patterns (file system, window management)
- IPC communication between main and renderer processes
- Platform-specific build configurations
- Auto-update mechanisms
- Performance optimization for desktop environments

## Startup Report

```
Detected Stack: Tauri + React
Active Plugins: desktop.md, react.md
```
