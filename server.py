from mcp.server.fastmcp import FastMCP
from upel_client import UpelClient

mcp = FastMCP("upel-agh")
client = UpelClient()

@mcp.tool()
def upel_check_session() -> dict:
    """Check if the current UPeL session cookie is valid and return logged-in user name."""
    return client.check_session()

@mcp.tool()
def upel_login(cookie: str | None = None) -> str:
    """Authenticate with AGH UPeL.

    Args:
        cookie: Optional MoodleSession cookie value (for headless servers, remote SSH, or manual token entry).
                If omitted, opens an interactive browser window on the desktop.
    """
    if cookie and cookie.strip():
        from auth import save_session
        save_session(cookie.strip())
    else:
        try:
            import subprocess
            import sys
            from pathlib import Path

            auth_script = Path(__file__).parent / "auth.py"
            res = subprocess.run([sys.executable, str(auth_script)], capture_output=True, text=True)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or "").strip()
                return f"Login failed: {err}" if err else f"Login failed (exit code {res.returncode})"
        except Exception as e:
            return f"Login failed: {e}"

    client.reload_session()
    check_res = client.check_session()
    if check_res.get("authenticated"):
        return f"Authenticated successfully: {check_res.get('user', 'OK')}"
    return f"Login completed, but session check failed: {check_res.get('error', 'Unknown error')}"

@mcp.tool()
def upel_list_courses() -> list[dict]:
    """List all enrolled courses with IDs, titles, and links from UPeL."""
    return client.list_courses()

@mcp.tool()
def upel_get_course(course_id: int) -> dict:
    """Get course sections, resources, activities, and assignments for a course ID."""
    return client.get_course(course_id)

@mcp.tool()
def upel_get_page(page_id_or_url: str) -> dict:
    """Read content, markdown text, and image URLs for a Moodle Page (/mod/page/view.php?id=...)."""
    return client.get_page_content(page_id_or_url)

@mcp.tool()
def upel_get_assignment(assignment_id: int) -> dict:
    """Get assignment details including deadline, instructions, and submission status."""
    return client.get_assignment(assignment_id)

@mcp.tool()
def upel_download_file(file_url: str, output_path: str) -> dict:
    """Download a file or learning resource from UPeL directly to the local filesystem.

    Args:
        file_url: UPeL URL of the resource or file (e.g. https://upel.agh.edu.pl/mod/resource/view.php?id=...).
        output_path: Target directory or file path on local disk.

    Returns:
        dict with saved file_path, filename, size, and content_type.
    """
    return client.download_file(file_url, output_path)

@mcp.tool()
def upel_read_file(file_url: str) -> dict:
    """Read a remote UPeL file/attachment into memory (returns filename and base64-encoded data)."""
    return client.read_file(file_url)

@mcp.tool()
def upel_download_section(course_id: int, section_query: str, output_dir: str) -> dict:
    """Download an entire course section (markdown task pages, embedded images, and resource files) in one bulk operation.

    Args:
        course_id: ID of the course (e.g. 1060).
        section_query: Section name keyword (e.g. 'Part 1') or 1-based section number.
        output_dir: Local destination directory where all files and images will be saved.

    Returns:
        dict with course title, section name, saved pages, images, and resources.
    """
    return client.download_section(course_id, section_query, output_dir)

if __name__ == "__main__":
    mcp.run()
