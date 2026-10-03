from mcp.server.fastmcp import FastMCP
from upel_client import UpelClient

mcp = FastMCP("upel-agh")
client = UpelClient()

@mcp.tool()
def upel_check_session() -> dict:
    """Check if the current UPeL session cookie is valid and return logged-in user name."""
    return client.check_session()

@mcp.tool()
def upel_login() -> str:
    """Launch interactive browser window for AGH SSO login and save new MoodleSession."""
    try:
        from auth import login_browser
        login_browser()
        client.reload_session()
        res = client.check_session()
        return f"Authenticated successfully: {res.get('user', 'OK')}"
    except Exception as e:
        return f"Login failed: {e}"

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
def upel_read_file(file_url: str) -> dict:
    """Read a remote UPeL file/attachment into memory (returns filename and base64-encoded data)."""
    return client.read_file(file_url)

if __name__ == "__main__":
    mcp.run()
