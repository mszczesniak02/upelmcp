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

## 4. Downloading & Saving Task Contents & Materials
When the user asks to download tasks, sections, or course materials:
1. **Ask for destination path:**
   - Ask the user where to save the files (or confirm default: `./<course_name_with_underscores>/`).
2. **Bulk Section Download (Preferred - Only 1 Permission Prompt):**
   - When downloading an entire section, lab, or set of tasks (e.g. "Part 1", "Getting started", "Exercises"), **always prefer calling `upel_download_section`**:
     `upel_download_section(course_id=<id>, section_query="<section_name_or_keyword>", output_dir="<dest_path>")`
   - **Why:** This downloads all markdown pages, diagram images (into `<output_dir>/images/`), and resource files in a **single bulk operation**. The user is prompted only once for permission instead of once per file.
3. **Single File / Page Downloads:**
   - For an individual file or attachment: call `upel_download_file(file_url="<url>", output_path="<dest_path>")`.
   - For an individual web page instruction: call `upel_get_page(page_id_or_url="<id>")` and save via `write_to_file`.
