import json
import os
import sys
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".session"

def save_session(cookie_value: str):
    SESSION_FILE.write_text(json.dumps({"MoodleSession": cookie_value.strip()}, indent=2), encoding="utf-8")
    SESSION_FILE.chmod(0o600)
    print(f"Session saved to {SESSION_FILE}")

def load_session() -> str | None:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        return data.get("MoodleSession")
    except Exception:
        return None

def setup_gui_environment():
    """Ensure GUI display environment variables exist across Linux desktop environments."""
    if sys.platform.startswith("linux"):
        # Auto-detect Wayland socket if missing
        if "WAYLAND_DISPLAY" not in os.environ:
            try:
                uid = os.getuid()
                user_run = Path(f"/run/user/{uid}")
                for w in [f"wayland-{i}" for i in range(5)]:
                    if (user_run / w).exists():
                        os.environ["WAYLAND_DISPLAY"] = w
                        break
            except Exception:
                pass

        # Auto-detect X11 display socket if missing
        if "DISPLAY" not in os.environ:
            for i in range(5):
                if Path(f"/tmp/.X11-unix/X{i}").exists():
                    os.environ["DISPLAY"] = f":{i}"
                    break

def get_browser_profile_dir() -> Path:
    """Return standard OS-specific cache directory for persistent browser profile."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    profile_dir = base / "upel_mcp" / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir

def bring_window_to_front(page):
    """Attempt to bring browser window to the foreground across OSes."""
    try:
        page.bring_to_front()
    except Exception:
        pass

    if sys.platform == "darwin":
        try:
            import subprocess
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'], capture_output=True)
        except Exception:
            pass

def launch_persistent_browser(p):
    """Launch persistent context using system browser if available, falling back to bundled chromium."""
    setup_gui_environment()
    user_data_dir = get_browser_profile_dir()

    # Determine channel priority by platform
    if sys.platform == "darwin":
        channels = ["chrome", "msedge", None]
    elif sys.platform == "win32":
        channels = ["msedge", "chrome", None]
    else:
        channels = ["chrome", "chromium", None]

    args = ["--new-window", "--start-maximized"]

    for channel in channels:
        try:
            kwargs = {
                "user_data_dir": str(user_data_dir),
                "headless": False,
                "args": args,
                "viewport": None,
            }
            if channel:
                kwargs["channel"] = channel
            return p.chromium.launch_persistent_context(**kwargs)
        except Exception:
            continue

    raise RuntimeError("No compatible browser (Chrome, Edge, or Playwright Chromium) could be launched.")

def login_browser():
    try:
        import asyncio
        asyncio.get_running_loop()
        in_loop = True
    except RuntimeError:
        in_loop = False

    if in_loop:
        import subprocess
        res = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True)
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(f"Login process failed or was cancelled: {err}" if err else "Login process failed.")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed in environment.")
        sys.exit(1)

    print("Opening browser for UPeL AGH SSO login...")
    print("Please log in using your AGH credentials.")

    with sync_playwright() as p:
        context = launch_persistent_browser(p)
        page = context.pages[0] if context.pages else context.new_page()

        page.goto("https://upel.agh.edu.pl/my/courses.php")
        bring_window_to_front(page)

        # If redirected to Moodle login page, automatically click SSO-AGH
        try:
            sso_btn = page.locator("a:has-text('Zaloguj się z SSO-AGH'), a.login-identityprovider-btn").first
            if sso_btn.is_visible(timeout=3000):
                sso_btn.click()
        except Exception:
            pass

        try:
            page.wait_for_url(
                lambda url: "upel.agh.edu.pl" in url and "login" not in url and ("my" in url or "course" in url),
                timeout=180000
            )
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            print("Finished waiting or page redirected.")

        cookies = context.cookies()
        moodle_session = next((c["value"] for c in cookies if c["name"] == "MoodleSession"), None)
        context.close()

        if not moodle_session:
            print("Failed to capture MoodleSession cookie.")
            sys.exit(1)

        save_session(moodle_session)
        print("Login successful! MoodleSession captured.")

if __name__ == "__main__":
    if "--cookie" in sys.argv and len(sys.argv) > sys.argv.index("--cookie") + 1:
        save_session(sys.argv[sys.argv.index("--cookie") + 1])
    elif "-h" in sys.argv or "--help" in sys.argv:
        print("Usage: python auth.py [--cookie <token>]")
    else:
        login_browser()
