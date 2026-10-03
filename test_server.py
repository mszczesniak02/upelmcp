import os
import stat
from auth import save_session, load_session, SESSION_FILE
from upel_client import UpelClient, ALLOWED_HOST
from server import mcp

def test_auth_permissions_and_roundtrip():
    original = SESSION_FILE.read_text() if SESSION_FILE.exists() else None
    try:
        test_val = "test_token_12345"
        save_session(test_val)
        loaded = load_session()
        assert loaded == test_val

        # Verify permissions are strictly 0600 (owner read/write only)
        mode = stat.S_IMODE(os.stat(SESSION_FILE).st_mode)
        assert mode == 0o600, f"Expected permissions 0600, got {oct(mode)}"
    finally:
        if original is not None:
            SESSION_FILE.write_text(original)
            SESSION_FILE.chmod(0o600)

def test_security_url_validation():
    client = UpelClient("dummy")

    # SSRF / scheme attacks
    try:
        client._validate_upel_url("file:///etc/passwd")
        assert False, "Should reject file:// scheme"
    except ValueError as e:
        assert "Invalid URL scheme" in str(e)

    # Untrusted hosts
    try:
        client._validate_upel_url("https://malicious.site/phishing")
        assert False, "Should reject untrusted host"
    except ValueError as e:
        assert "Untrusted host" in str(e)

    # Valid UPeL URL
    valid = f"https://{ALLOWED_HOST}/course/view.php?id=1060"
    assert client._validate_upel_url(valid) == valid

def test_input_validation():
    client = UpelClient("dummy")

    for invalid in [0, -5, "abc"]:
        try:
            client.get_course(invalid)
            assert False, f"Should reject invalid course_id {invalid}"
        except (ValueError, TypeError):
            pass

    for invalid in [0, -1, None]:
        try:
            client.get_assignment(invalid)
            assert False, f"Should reject invalid assignment_id {invalid}"
        except (ValueError, TypeError):
            pass

def test_read_only_mcp_tools():
    tool_names = {t.name for t in mcp._tool_manager.list_tools()}
    expected = {
        "upel_check_session",
        "upel_login",
        "upel_list_courses",
        "upel_get_course",
        "upel_get_page",
        "upel_get_assignment",
        "upel_read_file"
    }
    assert tool_names == expected, f"Expected exactly {expected}, got {tool_names}"

    # Verify no file-writing tools exist
    assert "upel_download_file" not in tool_names
    assert "upel_save_page_markdown" not in tool_names

def test_live_read_operations():
    client = UpelClient()
    session = client.check_session()
    if session.get("authenticated"):
        courses = client.list_courses()
        assert len(courses) > 0
        # Read page 36059 (Task 100 warmup)
        page = client.get_page_content(36059)
        assert "markdown" in page
        assert "suggested_filename" in page
        assert " " not in page["suggested_filename"]  # No spaces in filename

def test_session_reloading():
    original = SESSION_FILE.read_text() if SESSION_FILE.exists() else None
    try:
        # Client initialized with dummy cookie
        client = UpelClient("old_stale_cookie")
        assert client.cookie == "old_stale_cookie"

        # Simulating external login saving session
        test_cookie = "newly_saved_session_cookie"
        save_session(test_cookie)

        # _ensure_session should detect updated session file
        client._ensure_session()
        assert client.cookie == test_cookie
    finally:
        if original is not None:
            SESSION_FILE.write_text(original)
            SESSION_FILE.chmod(0o600)

if __name__ == "__main__":
    test_auth_permissions_and_roundtrip()
    test_security_url_validation()
    test_input_validation()
    test_read_only_mcp_tools()
    test_session_reloading()
    test_live_read_operations()
    print("All read-only tests and checks passed!")
