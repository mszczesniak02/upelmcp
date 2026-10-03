import base64
import mimetypes
import re
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from auth import load_session

BASE_URL = "https://upel.agh.edu.pl"
ALLOWED_HOST = "upel.agh.edu.pl"

def _slug(text: str) -> str:
    return re.sub(r'[^\w\.-]+', '_', text).strip('_')

def _clean_filename(name: str) -> str:
    p = Path(name)
    stem_clean = _slug(p.stem) or "file"
    suffix = p.suffix.lower()
    return f"{stem_clean}{suffix}"

class UpelClient:
    def __init__(self, session_cookie: str | None = None):
        self.reload_session(session_cookie)

    def reload_session(self, session_cookie: str | None = None):
        self.cookie = session_cookie or load_session()
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            cookies={"MoodleSession": self.cookie} if self.cookie else {},
            follow_redirects=True,
            timeout=20.0
        )

    def _ensure_authenticated(self, resp: httpx.Response):
        final_url = str(resp.url)
        if "login" in final_url or resp.status_code in (401, 403):
            raise PermissionError("UPeL session is invalid or expired. Run 'pyenv/bin/python auth.py' to authenticate.")

    def _validate_upel_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
        if parsed.netloc and parsed.netloc != ALLOWED_HOST:
            raise ValueError(f"Untrusted host: {parsed.netloc}. Requests restricted to {ALLOWED_HOST}.")
        return url

    def _get_sesskey(self, html: str) -> str | None:
        match = re.search(r'["\']sesskey["\']:\s*["\']([^"\']+)["\']', html)
        return match.group(1) if match else None

    def _ensure_session(self):
        latest = load_session()
        if latest != self.cookie:
            self.reload_session(latest)

    def check_session(self) -> dict:
        self.reload_session()
        if not self.cookie:
            return {"authenticated": False, "error": "No session cookie found. Run 'pyenv/bin/python auth.py'."}

        resp = self.client.get(f"{BASE_URL}/my/courses.php")
        if "login" in str(resp.url) or resp.status_code in (401, 403):
            return {"authenticated": False, "error": "Session expired. Run 'pyenv/bin/python auth.py'."}

        soup = BeautifulSoup(resp.text, "html.parser")
        user_elem = soup.select_one(".userbutton .usertext, .logininfo a, span.usertext")
        username = user_elem.get_text(strip=True) if user_elem else "Logged in user"
        return {"authenticated": True, "user": username}

    def list_courses(self) -> list[dict]:
        self._ensure_session()
        resp = self.client.get(f"{BASE_URL}/my/courses.php")
        self._ensure_authenticated(resp)

        sesskey = self._get_sesskey(resp.text)
        if not sesskey:
            raise RuntimeError("Could not find Moodle sesskey on courses page.")

        payload = [{
            "index": 0,
            "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
            "args": {"offset": 0, "limit": 0, "classification": "all", "sort": "fullname"}
        }]
        ajax_res = self.client.post(f"{BASE_URL}/lib/ajax/service.php?sesskey={sesskey}", json=payload)
        if ajax_res.status_code != 200:
            raise RuntimeError(f"Failed to fetch courses from Moodle service: {ajax_res.status_code}")

        data = ajax_res.json()
        if not (isinstance(data, list) and len(data) > 0 and "data" in data[0]):
            raise RuntimeError("Unexpected response structure from Moodle course service.")

        courses = []
        for c in data[0]["data"].get("courses", []):
            courses.append({
                "id": int(c["id"]),
                "name": c["fullname"],
                "shortname": c.get("shortname", ""),
                "url": f"{BASE_URL}/course/view.php?id={c['id']}"
            })
        return courses

    def get_course(self, course_id: int) -> dict:
        if not isinstance(course_id, int) or course_id <= 0:
            raise ValueError(f"Invalid course_id: {course_id}. Must be a positive integer.")

        self._ensure_session()
        resp = self.client.get(f"{BASE_URL}/course/view.php?id={course_id}")
        self._ensure_authenticated(resp)

        soup = BeautifulSoup(resp.text, "html.parser")
        title_elem = soup.select_one("h1, .page-header-headings h1")
        course_title = title_elem.get_text(strip=True) if title_elem else f"Course {course_id}"

        sections = []
        for sec in soup.select("li.section, .course-section"):
            sec_name_elem = sec.select_one(".sectionname, .section-title, h3")
            sec_name = sec_name_elem.get_text(strip=True) if sec_name_elem else "General"

            items = []
            seen_urls = set()

            for act in sec.select("li.activity, .activity-item"):
                link = act.select_one("a[href*='/mod/']")
                if not link:
                    continue

                href = link.get("href", "")
                clean_url = href.split("&redirect=")[0]
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                name_elem = act.select_one(".instancename, .activityname") or link
                for hidden in name_elem.select(".accesshide"):
                    hidden.decompose()

                item_name = name_elem.get_text(strip=True)
                mod_match = re.search(r"/mod/([a-zA-Z0-9]+)/", clean_url)
                item_type = mod_match.group(1) if mod_match else "unknown"

                items.append({
                    "name": item_name,
                    "type": item_type,
                    "url": clean_url
                })

            if items:
                sections.append({"section": sec_name, "items": items})

        return {
            "course_id": course_id,
            "title": course_title,
            "sections": sections
        }

    def get_page_content(self, page_id_or_url: str | int) -> dict:
        url = page_id_or_url if str(page_id_or_url).startswith("http") else f"{BASE_URL}/mod/page/view.php?id={page_id_or_url}"
        self._validate_upel_url(str(url))

        self._ensure_session()
        resp = self.client.get(url)
        self._ensure_authenticated(resp)

        soup = BeautifulSoup(resp.text, "html.parser")
        title_elem = soup.select_one("h2, .page-header-headings h1")
        title = title_elem.get_text(strip=True) if title_elem else "Page"

        content_box = soup.select_one(".page-content, #intro, [role='main'] .box.generalbox") or soup

        # Extract images metadata and embed markdown image references
        images = []
        for img in content_box.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue
            alt = img.get("alt", "Diagram")
            parsed_src = urlparse(src)
            clean_filename = _slug(Path(parsed_src.path).name) or "image.png"
            images.append({"url": src, "alt": alt, "suggested_filename": clean_filename})
            img.replace_with(f"\n\n![{alt}](images/{clean_filename})\n\n")

        # Convert links to markdown
        for a in content_box.find_all("a"):
            href = a.get("href", "")
            link_text = a.get_text(strip=True)
            if href and link_text:
                a.replace_with(f" [{link_text}]({href}) ")

        body_text = content_box.get_text("\n\n", strip=True)
        body_text = re.sub(r'\n{3,}', '\n\n', body_text)

        # Suggested filename with no spaces
        clean_title = _slug(title).lower()
        suggested_filename = f"{clean_title}.md" if clean_title else "page.md"

        return {
            "title": title,
            "url": str(resp.url),
            "suggested_filename": suggested_filename,
            "markdown": f"# {title}\n\n**Source:** {resp.url}\n\n{body_text}\n",
            "images": images
        }

    def get_assignment(self, assign_id: int) -> dict:
        if not isinstance(assign_id, int) or assign_id <= 0:
            raise ValueError(f"Invalid assign_id: {assign_id}. Must be a positive integer.")

        self._ensure_session()
        url = f"{BASE_URL}/mod/assign/view.php?id={assign_id}"
        resp = self.client.get(url)
        self._ensure_authenticated(resp)

        soup = BeautifulSoup(resp.text, "html.parser")
        title_elem = soup.select_one("h2, .page-header-headings h1")
        title = title_elem.get_text(strip=True) if title_elem else f"Assignment {assign_id}"

        intro_elem = soup.select_one("#intro, .activity-description, .submissionstatustable")
        intro = intro_elem.get_text("\n", strip=True) if intro_elem else ""

        status = {}
        for row in soup.select(".generaltable tr"):
            th = row.select_one("th, td.cell.c0")
            td = row.select_one("td.lastcol, td.cell.c1")
            if th and td:
                status[th.get_text(strip=True)] = td.get_text(strip=True)

        return {
            "assignment_id": assign_id,
            "title": title,
            "description": intro,
            "status": status,
            "url": url
        }

    def _extract_filename(self, resp: httpx.Response, fallback_url: str = "") -> str:
        # 1. Content-Disposition header
        cd = resp.headers.get("content-disposition", "")
        if cd:
            match_star = re.search(r"filename\*\s*=\s*(?:UTF-8''|utf-8'')([^;\s]+)", cd, re.IGNORECASE)
            if match_star:
                fname = urllib.parse.unquote(match_star.group(1).strip("\"'"))
                if fname:
                    return _clean_filename(fname)
            match = re.search(r'filename\s*=\s*"([^"]+)"|filename\s*=\s*([^\s;]+)', cd, re.IGNORECASE)
            if match:
                fname = (match.group(1) or match.group(2)).strip("\"'")
                if fname:
                    return _clean_filename(fname)

        # 2. Redirected final URL
        final_path = Path(urlparse(str(resp.url)).path)
        if final_path.suffix and final_path.name != "view.php":
            return _clean_filename(final_path.name)

        # 3. Initial URL path
        if fallback_url:
            init_path = Path(urlparse(fallback_url).path)
            if init_path.suffix and init_path.name != "view.php":
                return _clean_filename(init_path.name)

        # 4. Content-Type extension fallback
        ct = resp.headers.get("content-type", "").split(";")[0].strip()
        ext = mimetypes.guess_extension(ct) or ".bin"
        if ext == ".jpe":
            ext = ".jpg"
        return f"downloaded_file{ext}"

    def read_file(self, file_url: str) -> dict:
        """Pure read operation: downloads resource into memory as base64 without writing to disk."""
        self._validate_upel_url(file_url)
        self._ensure_session()
        resp = self.client.get(file_url)
        self._ensure_authenticated(resp)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "application/octet-stream")
        clean_name = self._extract_filename(resp, file_url)

        return {
            "filename": clean_name,
            "content_type": content_type,
            "size": len(resp.content),
            "data_base64": base64.b64encode(resp.content).decode("ascii")
        }

    def download_file(self, file_url: str, output_path: str) -> dict:
        """Download remote resource from UPeL directly to a local target file or directory.

        Args:
            file_url: UPeL URL of the resource/file.
            output_path: Destination file path or directory on local disk.

        Returns:
            dict containing file_path, filename, size, and content_type.
        """
        self._validate_upel_url(file_url)
        self._ensure_session()

        dest_path = Path(output_path).expanduser().resolve()

        with self.client.stream("GET", file_url) as resp:
            self._ensure_authenticated(resp)
            resp.raise_for_status()

            resolved_filename = self._extract_filename(resp, file_url)

            if dest_path.is_dir() or str(output_path).endswith(("/", "\\")):
                dest_file = dest_path / resolved_filename
            else:
                dest_file = dest_path

            dest_file.parent.mkdir(parents=True, exist_ok=True)

            bytes_written = 0
            with open(dest_file, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    bytes_written += len(chunk)

            return {
                "file_path": str(dest_file),
                "filename": dest_file.name,
                "size": bytes_written,
                "content_type": resp.headers.get("content-type", "application/octet-stream")
            }
