"""Validate tracked repository files, configs, skill entries, and basic hygiene using Python stdlib only."""
import configparser
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tomllib
import unicodedata


def git(*args):
    return subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE).stdout


GUARD_RULES = [
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
    (
        "provider credential",
        re.compile(
            r"(?:\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
            r"|\bgh[pousr]_[A-Za-z0-9]{20,}\b"
            r"|\bgithub_pat_\w{24,}\b"
            r"|\bsk-(?:proj-)?[\w-]{18,}\b"
            r"|\bAIza[\w-]{35}\b"
            r"|\bxox[bpars]-[\w-]{12,}\b"
            r"|\bglpat-[\w-]{15,}\b)"
        ),
    ),
    ("signed token", re.compile(r"\beyJ[\w-]{6,}\.[\w-]{8,}\.[\w-]{8,}\b")),
    ("URL credential", re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mongodb(?:\+srv)?|redis|mysql)://[^\s'\x22/:@]+:[^\s'\x22/@]+@")),
    ("machine home", re.compile(r"(?i)(?:/Users/|/home/|[A-Z]:\\Users\\)[a-z0-9_.-][a-z0-9._-]+[/\\]")),
]
ASSIGNMENT = re.compile(
    r"""(?ix)(?<![\w-])(?:api[_-]?key|password|passwd|client[_-]?secret|app[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|private[_-]?key|session[_-]?cookie|secret[_-]?key)["']?\s*[:=]\s*["']([^"'\r\n]{4,})["']"""
)
UNQUOTED = re.compile(
    r"(?im)^\s*(?:export\s+)?(?:[A-Z][A-Z0-9_]*_)?(?:API_KEY|ACCESS_TOKEN|REFRESH_TOKEN|CLIENT_SECRET|PASSWORD|SECRET_KEY|SESSION_COOKIE)\s*=\s*([A-Za-z0-9][^\s#]{4,})\s*(?:#.*)?$"
)
PLACEHOLDER = re.compile(r"^(?:<[A-Z0-9_ -]+>|\$\{?[A-Za-z_][\w]*\}?|\{\{\s*[\w.-]+\s*\}\})$")
BIDI_CONTROL = re.compile("[\u202a-\u202e\u2066-\u2069]")

FORBIDDEN_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".cache", ".pytest_cache", "quarantine", "raw", "outputs", "scratch", ".ssh",
}
FORBIDDEN_SUFFIX = {
    ".zip", ".tgz", ".tar", ".gz", ".7z", ".rar",
    ".p12", ".pfx", ".pem", ".key",
    ".sqlite", ".sqlite3", ".db", ".log", ".pyc", ".pyo", ".pyd", ".bundle",
}
FORBIDDEN_NAMES = {
    "credentials.json", "cookies.txt", "id_rsa", "id_ed25519",
    ".npmrc", ".netrc", "thumbs.db", ".ds_store",
}
ARCHIVE_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"\x1f\x8b", b"Rar!\x1a\x07", b"7z\xbc\xaf\x27\x1c", b"\x7fELF")

errors = []
counts = {}


def fail(where, reason):
    # Report file paths and violation categories without echoing potentially sensitive matched text.
    errors.append((where, reason))


def check_text(raw, where):
    if raw.startswith(ARCHIVE_MAGIC):
        fail(where, "prohibited archive or executable binary")
        return None
    if b"\x00" in raw:
        fail(where, "unexpected binary content")
        return None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        fail(where, "non-UTF-8 content")
        return None
    if BIDI_CONTROL.search(text):
        fail(where, "bidirectional control character")
    for label, rule in GUARD_RULES:
        if rule.search(text):
            fail(where, label)
    if UNQUOTED.search(text) or any(not PLACEHOLDER.fullmatch(m[1]) for m in ASSIGNMENT.finditer(text)):
        fail(where, "credential assignment")
    return text


def check_path(path):
    parts = PurePosixPath(path).parts
    if (
        not parts
        or path.startswith("/")
        or any(
            p in {".", ".."}
            or p.casefold() in FORBIDDEN_DIRS
            or p.casefold() in FORBIDDEN_NAMES
            or p.rstrip(" .") != p
            or re.search(r'[\x00-\x1f\x7f<>:"|?*\\]', p)
            or re.fullmatch(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p, re.I)
            or p.startswith(".env")
            for p in parts
        )
        or PurePosixPath(path).suffix.lower() in FORBIDDEN_SUFFIX
    ):
        fail(path, "prohibited path")
    check_text(path.encode("utf-8"), path)


def parse_skill_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening front matter delimiter")
    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break
    if end_index is None:
        raise ValueError("missing closing front matter delimiter")
    meta = {}
    for line in lines[1:end_index]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError("invalid front matter entry")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1].strip()
        if key:
            meta[key] = value
    for required in ("name", "description"):
        if not meta.get(required):
            raise ValueError(f"missing skill metadata: {required}")
    return meta


def verify_workspace_lockfile(paths):
    pkg_path = "workspace/package.json"
    lock_path = "workspace/package-lock.json"
    if pkg_path not in paths or lock_path not in paths:
        return
    try:
        pkg = json.loads(Path(pkg_path).read_text(encoding="utf-8"))
        lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    pkg_deps = pkg.get("dependencies", {})
    lock_root_deps = lock.get("packages", {}).get("", {}).get("dependencies", {})
    if pkg_deps != lock_root_deps:
        fail(lock_path, "dependencies out of sync with workspace/package.json")


def verify_checkout():
    keys = {"python": 0, "config": 0, "skill_entries": 0, "partial_modules": 0}
    modes = git("ls-files", "--stage", "-z").split(b"\0")
    paths = set()
    norm_paths = set()

    for item in filter(None, modes):
        metadata, raw_name = item.split(b"\t", 1)
        path = raw_name.decode("utf-8")
        paths.add(path)
        norm = unicodedata.normalize("NFKC", path).casefold()
        if norm in norm_paths:
            fail(path, "case/Unicode path collision")
        norm_paths.add(norm)
        check_path(path)

        p = Path(path)
        mode, _, stage = metadata.split()
        if stage != b"0" or mode not in (b"100644", b"100755") or p.is_symlink() or not p.is_file():
            fail(path, "invalid Git index mode or missing regular file")
            continue

        text = check_text(p.read_bytes(), path)
        if text is None:
            continue

        try:
            if p.suffix == ".py":
                compile(text, path, "exec", dont_inherit=True)
                keys["python"] += 1
            elif p.suffix in (".json", ".toml", ".ini", ".cfg"):
                if p.suffix == ".json":
                    json.loads(text)
                elif p.suffix == ".toml":
                    tomllib.loads(text)
                else:
                    configparser.ConfigParser(interpolation=None).read_string(text)
                keys["config"] += 1
            if p.name == "SKILL.md" and len(p.parts) == 3 and p.parts[0] == "skills":
                parse_skill_frontmatter(text)
                keys["skill_entries"] += 1
        except SyntaxError as exc:
            fail(path, f"Python syntax error at line {exc.lineno}")
        except (ValueError, configparser.Error) as exc:
            fail(path, f"configuration error: {exc}")

    skill_dirs = sorted({p.split("/")[1] for p in paths if p.startswith("skills/") and len(p.split("/")) > 2})
    for directory in skill_dirs:
        has_entry = f"skills/{directory}/SKILL.md" in paths
        has_requirements = f"skills/{directory}/requirements.txt" in paths
        if not has_entry and has_requirements:
            keys["partial_modules"] += 1
        elif not has_entry:
            fail(f"skills/{directory}", "skill directory missing SKILL.md or requirements.txt")

    verify_workspace_lockfile(paths)
    counts.update(keys)
    counts["tracked"] = len(paths)


if __name__ == "__main__":
    os.chdir(git("rev-parse", "--show-toplevel").decode("utf-8").strip())
    verify_checkout()
    for where, reason in errors:
        print(f"{where}: {reason}", file=sys.stderr)
    print(json.dumps(counts, sort_keys=True))
    sys.exit(bool(errors))
