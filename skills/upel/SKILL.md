---
name: upel
description: >-
  Interact with the AGH UPeL (Moodle) learning platform: authenticating sessions,
  listing enrolled courses, inspecting course contents and assignments, and downloading materials.
  Use when the user asks about UPeL, AGH courses, course materials, assignments, or downloads from upel.agh.edu.pl.
---

# AGH UPeL Agent Workflow

This skill connects to the UPeL MCP server (read-only against UPeL) and guides the agent through the complete workflow.

## 1. Automatic Authentication Check (Always Run First)
Whenever invoked or asked about UPeL, **immediately check the session status first**:
- Call MCP tool `upel_check_session`.
- If the session is invalid, expired, or missing:
  - Call MCP tool `upel_login` (which launches the browser window for the user).
  - Inform the user that the AGH SSO login window has been opened and wait for them to log in.
  - Re-verify session validity with `upel_check_session` before proceeding.

## 2. Listing Courses
- Call `upel_list_courses` to retrieve all enrolled courses.
- Present courses cleanly by name with numbers (no links), for example:
  ```text
  1. [1060] Operating systems for embedded systems
  2. [1114] Metodyki Zarządzania Projektami
  3. [11584] Narzędzia Komputerowe w Rozwiązywaniu ...
  ```
- Ask the user which course number or ID to inspect.

## 3. Inspecting Course Contents
- Call `upel_get_course(course_id=<id>)` to retrieve sections, tasks, and page IDs.
- Present the sections and items clearly to the user.

## 4. Downloading & Saving Task Contents
When the user selects tasks or pages to download:
1. **Ask for destination path:**
   - Ask the user where to save the files.
   - **Default suggestion:** The current directory with a subfolder named after the course using underscores instead of spaces:
     `./<course_name_with_underscores>/` (e.g. `./operating_systems_for_embedded_systems/`).
2. **Fetch and Save:**
   - Call `upel_get_page(page_id_or_url="<id_or_url>")` to receive `title`, `markdown`, `suggested_filename`, and `images`.
   - The MCP server is strictly read-only and does not write to disk.
   - **The agent must use its native file writing tool (`write_to_file`)** to save the markdown file into the destination folder.
   - Ensure the filename has no spaces (e.g. `task_100_warmup.md`).
   - If there are diagram images in `images`, call `upel_read_file(file_url="...")` and save them under `<dest_dir>/images/<image_name>`.
