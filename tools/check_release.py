"""Heuristic public-content checks. Not a substitute for a secret/license audit."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    ".env.example", ".gitignore", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "README.md", "README.ko.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "MANIFEST.in", "pyproject.toml",
}
FOLDERS = {"src", "tests", "tools", "docs", "examples", ".github"}
SUFFIXES = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".html", ".svg", ".png"}
IGNORED = {".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache", "screenshots", "traces", "secrets"}


def selected_files(root: Path = ROOT) -> list[Path]:
    files = []
    for item in sorted(root.iterdir()):
        if item.name not in ROOT_FILES | FOLDERS:
            continue
        if item.is_symlink():
            raise ValueError(f"symlink not allowed: {item.name}")
        candidates = [item] if item.is_file() else sorted(item.rglob("*"))
        for path in candidates:
            relative = path.relative_to(root)
            if any(p in IGNORED or p.endswith(".egg-info") for p in relative.parts):
                continue
            if path.name.startswith('.env') and relative.as_posix() != '.env.example':
                continue
            if path.is_symlink():
                raise ValueError(f"symlink not allowed: {relative}")
            if path.is_file() and (path.name in ROOT_FILES or path.suffix in SUFFIXES):
                files.append(path)
    return files


class _HTMLLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for name, value in attrs if name in {'src', 'href'} and value)


def markdown_anchors(text: str) -> set[str]:
    anchors, counts = set(), {}
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.MULTILINE):
        slug = re.sub(r'[^\w\- ]', '', re.sub(r'<[^>]+>', '', heading).lower()).replace(' ', '-')
        number = counts.get(slug, 0)
        counts[slug] = number + 1
        anchors.add(slug if number == 0 else f'{slug}-{number}')
    anchors.update(re.findall(r'\bid=["\x27]([^"\x27]+)', text))
    return anchors


def local_link_errors(path: Path, root: Path, included: set[Path]) -> list[str]:
    included = {item.resolve() for item in included}
    text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.DOTALL)
    html = _HTMLLinks()
    html.feed(text)
    targets = re.findall(r'\]\(([^\s)]+)\)', text) + html.targets
    errors = []
    for target in targets:
        parsed = urlsplit(target)
        if parsed.scheme in {'https', 'http', 'mailto'}:
            continue
        if parsed.scheme or parsed.netloc:
            errors.append('unsupported link scheme')
            continue
        destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
        if not destination.is_relative_to(root.resolve()) or destination not in included:
            errors.append(f'link outside release or missing: {target}')
        elif parsed.fragment and destination.suffix == '.md' and unquote(parsed.fragment) not in markdown_anchors(destination.read_text(encoding='utf-8')):
            errors.append(f'missing heading anchor: {target}')
    return errors


def check(root: Path = ROOT) -> list[Path]:
    files = selected_files(root)
    required = ROOT_FILES | {"src/rdp_cua/__init__.py", ".github/workflows/ci.yml"}
    present = {str(p.relative_to(root)).replace("\\", "/") for p in files}
    missing = required - present
    if missing:
        raise ValueError(f"missing release files: {sorted(missing)}")
    patterns = {
        "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "JWT-shaped value": r"eyJ[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}",
        "API-token-shaped value": r"(?:sk-[A-Za-z0-9_-]{32,}|gh[pousr]_[A-Za-z0-9]{30,})",
        "local user path": r"/Use" + r"rs/[^/\s]+/|[A-Za-z]:\\Use" + r"rs\\[^\\\s]+\\",
    }
    failures = []
    for path in files:
        if path.suffix == ".png":
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root)
        for label, pattern in patterns.items():
            if re.search(pattern, text):
                failures.append(f"{relative}: {label}")
        if path.suffix == ".md":
            failures.extend(f'{relative}: {error}' for error in local_link_errors(path, root, {p.resolve() for p in files}))
    if failures:
        raise ValueError("release-content checks failed:\n" + "\n".join(failures))
    return files


if __name__ == "__main__":
    try:
        print(f"PASS: {len(check())} allowlisted files; heuristic content and Markdown-link checks")
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
