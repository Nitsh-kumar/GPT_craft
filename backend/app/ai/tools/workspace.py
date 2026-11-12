import os
import difflib
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from langchain_core.tools import tool
from langgraph.types import interrupt

MAX_TOOL_OUTPUT_CHARS = 4000

IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    ".pytest_cache",
    ".idea",
    ".vscode",
}

IGNORED_FILE_EXTENSIONS = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
}


def get_workspace_root() -> Path:
    """
    Returns the resolved workspace root directory.
    Uses GPTCRAFT_WORKSPACE_ROOT environment variable if set,
    otherwise resolves the repository root relative to this file.
    """
    env_root = os.getenv("GPTCRAFT_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root).resolve()

    # backend/app/ai/tools/workspace.py -> parents[4] is repo root
    file_path = Path(__file__).resolve()
    candidate = Path.cwd().resolve()
    if len(file_path.parents) >= 5:
        candidate = file_path.parents[4]
        if (candidate / "backend").exists() or (candidate / "frontend").exists():
            return candidate

    # Fallback to current working directory or its parent
    cwd = Path.cwd().resolve()
    if (cwd / "backend").exists() or (cwd / "frontend").exists():
        return cwd
    if (cwd.parent / "backend").exists():
        return cwd.parent

    return candidate


def resolve_workspace_path(relative_path: str = ".") -> Path:
    """
    Safely resolves a relative path within the workspace root.
    Raises ValueError if the path escapes the workspace root.
    """
    root = get_workspace_root()
    # Normalize path
    target = (root / relative_path).resolve()
    try:
        if not target.is_relative_to(root):
            raise ValueError(f"Access denied: path '{relative_path}' is outside the workspace root.")
    except AttributeError:
        # Python < 3.9 fallback
        try:
            target.relative_to(root)
        except ValueError:
            raise ValueError(f"Access denied: path '{relative_path}' is outside the workspace root.")

    return target


def truncate_tool_output(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    """
    Truncates tool output to limit characters with a truncation marker.
    Guarantees len(result) <= limit.
    """
    if len(text) <= limit:
        return text
    suffix = "\n...[Truncated to 4,000 chars]"
    cut_length = limit - len(suffix)
    if cut_length < 0:
        return text[:limit]
    return text[:cut_length] + suffix


@tool
def read_workspace_file(path: str, start_line: int = 1, end_line: int = 200, max_lines: Optional[int] = None) -> str:
    """
    Read lines from a text file within the workspace repository.
    path: relative path to the file within workspace root
    start_line: 1-indexed starting line number (inclusive)
    end_line: 1-indexed ending line number (inclusive)
    max_lines: optional maximum count of lines to read starting from start_line
    """
    if max_lines is not None:
        end_line = start_line + max_lines - 1
    try:
        resolved = resolve_workspace_path(path)
    except ValueError as exc:
        return f"Error: {str(exc)}"

    if not resolved.exists():
        return f"Error: File '{path}' not found."

    if not resolved.is_file():
        return f"Error: '{path}' is not a regular file."

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as exc:
        return f"Error: Could not read file '{path}': {str(exc)}"

    total_lines = len(lines)
    s_idx = max(1, start_line)
    e_idx = min(total_lines, end_line)

    if s_idx > total_lines:
        return f"File '{path}' has {total_lines} lines; start_line {start_line} exceeds total lines."

    output_lines = []
    for line_num in range(s_idx, e_idx + 1):
        line_content = lines[line_num - 1].rstrip("\r\n")
        output_lines.append(f"{line_num}: {line_content}")

    result = "\n".join(output_lines)
    return truncate_tool_output(result)


@tool
def list_workspace_directory(path: str = ".") -> str:
    """
    List files and folders within a directory inside the workspace repository.
    path: relative directory path within workspace root (default '.')
    """
    try:
        resolved = resolve_workspace_path(path)
    except ValueError as exc:
        return f"Error: {str(exc)}"

    if not resolved.exists():
        return f"Error: Directory '{path}' not found."

    if not resolved.is_dir():
        return f"Error: '{path}' is not a directory."

    try:
        entries = sorted(list(resolved.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
    except Exception as exc:
        return f"Error reading directory '{path}': {str(exc)}"

    root = get_workspace_root()
    dirs = []
    files = []
    for entry in entries:
        try:
            rel_parts = entry.relative_to(root).parts
        except ValueError:
            rel_parts = entry.parts
        if entry.name in IGNORED_DIRS or any(part in IGNORED_DIRS for part in rel_parts):
            continue
        if entry.is_dir():
            dirs.append(f"{entry.name}/")
        else:
            if entry.suffix.lower() not in IGNORED_FILE_EXTENSIONS:
                files.append(entry.name)

    items = dirs + files
    if not items:
        return f"(Empty directory: {path})"

    return truncate_tool_output("\n".join(items))


@tool
def search_workspace_symbols(query: str, path: str = ".") -> str:
    """
    Search text files under path for case-insensitive occurrences of query.
    query: string or symbol name to search for
    path: relative directory path to search within (default '.')
    """
    try:
        resolved = resolve_workspace_path(path)
    except ValueError as exc:
        return f"Error: {str(exc)}"

    if not resolved.exists():
        return f"Error: Path '{path}' not found."

    root = get_workspace_root()
    matches = []
    query_lower = query.lower()

    if resolved.is_file():
        file_candidates = [resolved]
    else:
        file_candidates = []
        for curr_root, dirnames, filenames in os.walk(resolved):
            # Prune ignored directories in-place
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for f in filenames:
                file_path = Path(curr_root) / f
                if file_path.suffix.lower() not in IGNORED_FILE_EXTENSIONS:
                    file_candidates.append(file_path)

    for file_path in file_candidates:
        try:
            rel_path = file_path.relative_to(root).as_posix()
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, start=1):
                    if query_lower in line.lower():
                        clean_line = line.strip("\r\n")
                        matches.append(f"{rel_path}:{line_idx}: {clean_line}")
                        if len(matches) >= 200:
                            break
        except Exception:
            continue
        if len(matches) >= 200:
            break

    if not matches:
        return f"No matches found for '{query}' in '{path}'."

    return truncate_tool_output("\n".join(matches))


@tool
def edit_workspace_file(
    path: str,
    content: str,
    mode: str = "write",
    rationale: str = "Modifying workspace file",
) -> str:
    """
    Create or modify a workspace text file with human-in-the-loop approval.
    path: relative path to the file within workspace root
    content: full text content to write or append
    mode: write mode ('write' to replace or create, 'append' to append)
    rationale: explanation of why this file mutation is needed
    """
    try:
        resolved = resolve_workspace_path(path)
    except ValueError as exc:
        return f"Error: {str(exc)}"

    old_lines = []
    old_content = ""
    if resolved.exists():
        if not resolved.is_file():
            return f"Error: '{path}' is not a regular file."
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                old_lines = f.readlines()
                old_content = "".join(old_lines)
        except Exception as exc:
            return f"Error reading existing file '{path}': {str(exc)}"

    effective_mode = (mode or "write").lower()
    if effective_mode == "append":
        target_content = old_content + content
    else:
        target_content = content

    new_lines = target_content.splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"
    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )
    diff_text = "".join(diff_lines) if diff_lines else "(No textual changes)"

    action_id = f"act_{uuid.uuid4().hex[:8]}"
    interrupt_payload = {
        "actionId": action_id,
        "tool": "edit_workspace_file",
        "tier": 2,
        "parameters": {
            "path": path,
            "content": content,
            "mode": effective_mode,
        },
        "rationale": rationale,
        "diff": diff_text,
    }

    resume_payload = interrupt(interrupt_payload)
    if not isinstance(resume_payload, dict):
        resume_payload = {}

    decision = str(resume_payload.get("decision", "approve")).lower()
    if decision == "reject":
        feedback = resume_payload.get("feedback") or "Action rejected by user"
        return f"Action rejected by user. Feedback: {feedback}"

    final_path = path
    final_content = content
    final_mode = effective_mode

    if decision == "modify":
        modified_params = resume_payload.get("modifiedParams") or {}
        final_path = modified_params.get("path", final_path)
        final_content = modified_params.get("content", final_content)
        final_mode = str(modified_params.get("mode", final_mode)).lower()

    try:
        final_resolved = resolve_workspace_path(final_path)
    except ValueError as exc:
        return f"Error: {str(exc)}"

    try:
        final_resolved.parent.mkdir(parents=True, exist_ok=True)
        write_flag = "a" if final_mode == "append" else "w"
        with open(final_resolved, write_flag, encoding="utf-8") as f:
            f.write(final_content)
    except Exception as exc:
        return f"Error writing to file '{final_path}': {str(exc)}"

    return f"Successfully updated '{final_path}'."


TIER_1_TOOLS = [read_workspace_file, list_workspace_directory, search_workspace_symbols]
TIER_2_TOOLS = [edit_workspace_file]

TOOL_CAPABILITY_TIERS: Dict[str, int] = {
    "read_workspace_file": 1,
    "list_workspace_directory": 1,
    "search_workspace_symbols": 1,
    "edit_workspace_file": 2,
}

TOOL_TIERS = TOOL_CAPABILITY_TIERS


def get_tool_tier(tool_name: str) -> int:
    """Returns the capability tier for a given tool (defaults to Tier 1)."""
    return TOOL_CAPABILITY_TIERS.get(tool_name, 1)
