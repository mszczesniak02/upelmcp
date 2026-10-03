import json
import os
import sys
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".session"

def save_session(cookie_value: str):
    data = {"MoodleSession": cookie_value.strip()}
    # Write with strict user-only read/write permissions (0600)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(SESSION_FILE, flags, 0o600)
    with open(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
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

def login_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed in environment.")
        sys.exit(1)

    print("Opening browser for UPeL AGH SSO login...")
    print("Please log in using your AGH credentials.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://upel.agh.edu.pl/my/courses.php")

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
        browser.close()

        if not moodle_session:
            print("Failed to capture MoodleSession cookie.")
            sys.exit(1)

        save_session(moodle_session)
        print("Login successful! MoodleSession captured.")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--cookie":
        save_session(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print("  python auth.py                 # Open browser for AGH SSO login")
        print("  python auth.py --cookie <val>  # Manually set MoodleSession cookie")
    else:
        login_browser()
