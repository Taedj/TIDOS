"""Start the orb from START TIDOS: one instance per user, no console window, never blocks or breaks START."""
import os
import socket
import subprocess
import sys

PORT = 8769  # 127.0.0.1 only: the running orb listens here for "refresh" / "show" / "quit"
MESSAGES = (b"refresh", b"show", b"quit")


def should_start(env=None):
    env = os.environ if env is None else env
    if env.get("TIDOS_NO_ORB") or env.get("CI"):
        return False
    if os.name != "nt" and sys.platform != "darwin" and not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")):
        return False  # headless Linux: nowhere to float
    try:
        from tidos_brain import control
        return control.is_on("orb")
    except Exception:  # noqa: BLE001 - an unreadable control file must not break START TIDOS
        return False


def send(message, port=PORT, timeout=0.5):
    """Tell a running orb something; False when no orb is listening."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
            s.sendall(message)
        return True
    except OSError:
        return False


def _python():
    if os.name == "nt":  # pythonw has no console, so nothing flashes on screen
        windowless = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if os.path.isfile(windowless):
            return windowless
    return sys.executable


def spawn(port=PORT, show=False):
    """'running' (the open orb was refreshed), 'started', or 'off'. show=True: the user asked for it explicitly
    (the `orb` switch does not apply) and the panel opens."""
    if not show and not should_start():
        return "off"
    if send(b"show" if show else b"refresh", port):
        return "running"
    main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__main__.py")
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([_python(), "-I", main, "run", "--port", str(port)] + (["--show"] if show else []), **kwargs)
    return "started"


def open_control_center():
    """The Control Center (login in the browser) for everything that changes TIDOS."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        argv = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
                "-File", os.path.join(root, "scripts", "tidoszit.ps1")]
    else:
        kwargs["start_new_session"] = True
        argv = [sys.executable, "-I", os.path.join(root, "tidos_dashboard", "__main__.py")]
    subprocess.Popen(argv, **kwargs)
