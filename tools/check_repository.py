"""Validate tracked files and scan reachable Git history without loading business code."""
import configparser
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tomllib
import unicodedata
import warnings

import yaml


def git(*args):
    return subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE).stdout


SIGNED_QUERY_KEYS = (
    "X-Amz-Signature", "X-Amz-Credential", "X-Goog-Signature",
    "sig", "access_token", "auth_token",
)
SIGNED_QUERY = re.compile(r"[?&](?:" + "|".join(SIGNED_QUERY_KEYS) + r")=[a-z0-9%+/._=-]{8,}", re.I)
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
    ("signed URL", SIGNED_QUERY),
    ("bearer credential", re.compile(r"(?i)\bBearer[ \t]+[\w+/.-]{14,}")),
    ("session cookie", re.compile(r"(?i)\b(?:set-cookie|cookie)\s*:\s*(?:session(?:id)?|auth|token)=[a-z0-9_+.-]{6,}")),
    ("personal identifier", re.compile(r"(?<![a-zA-Z0-9])(?:1[3-9]\d{9}|[1-9]\d{16}[Xx\d])(?![a-zA-Z0-9])")),
    ("URL credential", re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mongodb(?:\+srv)?|redis|mysql)://[^\s'\x22/:@]+:[^\s'\x22/@]+@")),
    ("machine home", re.compile(r"(?i)(?:/Users/|/home/|[A-Z]:\\Users\\)[a-z0-9_.-][a-z0-9._-]+[/\\]")),
]
CONTACT = re.compile(r"(?i)\b[\w.+%-]+@(?!example\.(?:invalid|com|org|net)\b)[a-z0-9.-]+\.[a-z]{2,}\b")
# Git generates these identity fields separately from user-written messages and file contents.
GIT_IDENTITY_EMAIL = re.compile(r"(?m)^((?:author|committer|tagger) [^\n<>]*<)[^<>\s@]+@[^<>\s@]+(> -?\d+ [+-]\d{4})$")
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


def check_text(raw, where, *, git_metadata=False):
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
    contact_text = text
    if git_metadata:
        header, separator, message = text.partition("\n\n")
        contact_text = GIT_IDENTITY_EMAIL.sub(r"\1\2", header) + separator + message
    if CONTACT.search(contact_text):
        fail(where, "contact address")
    if UNQUOTED.search(text) or any(not PLACEHOLDER.fullmatch(m[1]) for m in ASSIGNMENT.finditer(text)):
        fail(where, "credential assignment")
    return text


def check_path(path, where, *, historical=False):
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
            or (p.casefold().startswith(".env") and not (historical and p == ".env.example"))
            for p in parts
        )
        or PurePosixPath(path).suffix.lower() in FORBIDDEN_SUFFIX
    ):
        fail(where, "prohibited path")
    check_text(path.encode("utf-8"), where)


def normalized(component):
    return unicodedata.normalize("NFKC", component).casefold()


def check_tree(raw, oid_bytes, where):
    pos = 0
    names = set()
    while pos < len(raw):
        end = raw.index(0, pos)
        mode, name = raw[pos:end].split(b" ", 1)
        pos = end + 1 + oid_bytes
        try:
            label = name.decode("utf-8")
        except UnicodeDecodeError:
            fail(where, "non-UTF-8 path")
            continue
        check_path(label, where, historical=True)
        key = normalized(label)
        if key in names:
            fail(where, "case/Unicode path collision")
        names.add(key)
        if mode not in (b"40000", b"100644", b"100755"):
            fail(where, "non-regular Git object mode")


def scan_history():
    if git("rev-parse", "--is-shallow-repository").strip() == b"true":
        fail("Git history", "shallow checkout; fetch full history before running checks")
        return
    counts.update(blob=0, commit=0, tree=0, tag=0)
    # Stream the refs and HEAD (including a detached PR merge), visiting shared objects once.
    with subprocess.Popen(
        ["git", "rev-list", "--objects", "--no-object-names", "--all", "HEAD"], stdout=subprocess.PIPE
    ) as listing, subprocess.Popen(
        ["git", "cat-file", "--batch"], stdin=listing.stdout, stdout=subprocess.PIPE
    ) as objects:
        listing.stdout.close()
        stream = objects.stdout
        for header in stream:
            oid, kind, size = header.split()
            kind = kind.decode("ascii")
            raw = stream.read(int(size))
            if len(raw) != int(size) or stream.read(1) != b"\n":
                raise RuntimeError("incomplete Git object")
            where = f"{kind} {oid[:12].decode('ascii')}"
            counts[kind] += 1
            if kind == "tree":
                check_tree(raw, len(oid) // 2, where)
            else:
                check_text(raw, where, git_metadata=kind in {"commit", "tag"})
        if objects.wait() or listing.wait():
            fail("Git history", "could not enumerate all reachable objects")


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
    # Preserve document line numbers in parser diagnostics, including the opening delimiter.
    meta = yaml.safe_load("\n" + "\n".join(lines[1:end_index]))
    for required in ("name", "description"):
        if not isinstance(meta, dict) or not isinstance(meta.get(required), str) or not meta[required].strip():
            raise ValueError("invalid skill metadata")
    return meta


PACKAGE = "workspace/package.json"
LOCKFILE = "workspace/package-lock.json"


def verify_workspace_lockfile(manifests):
    if not manifests:
        return
    if PACKAGE not in manifests or LOCKFILE not in manifests:
        fail("workspace", "package.json and package-lock.json must both be present and valid")
        return
    try:
        declared = manifests[PACKAGE].get("dependencies", {})
        locked = manifests[LOCKFILE]["packages"][""].get("dependencies", {})
    except (AttributeError, KeyError, TypeError):
        fail("workspace", "invalid npm manifest structure")
        return
    if not isinstance(declared, dict) or not isinstance(locked, dict) or declared != locked:
        fail(LOCKFILE, "dependencies out of sync with workspace/package.json")


def error_location(exc):
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        return f" at line {mark.line + 1}, column {mark.column + 1}"
    line = getattr(exc, "lineno", None)
    if not line and isinstance(exc, configparser.ParsingError) and exc.errors:
        line = exc.errors[0][0]
    col = getattr(exc, "colno", None)
    if isinstance(line, int):
        return f" at line {line}" + (f", column {col}" if isinstance(col, int) else "")
    return ""


def verify_checkout():
    keys = {"python": 0, "config": 0, "skill_entries": 0, "partial_modules": 0}
    modes = git("ls-files", "--stage", "-z").split(b"\0")
    paths = set()
    spelling = {}
    manifests = {}

    for number, item in enumerate(filter(None, modes), 1):
        metadata, raw_name = item.split(b"\t", 1)
        index_label = f"index entry {number}"
        try:
            path = raw_name.decode("utf-8")
        except UnicodeDecodeError:
            fail(index_label, "non-UTF-8 path")
            continue
        paths.add(path)
        before = len(errors)
        check_path(path, index_label)
        where = path if len(errors) == before else index_label

        p = Path(path)
        for component in (*reversed(p.parents), p):
            key = normalized(component.as_posix())
            if spelling.setdefault(key, component) != component:
                fail(index_label, "case/Unicode path collision")
                break
        mode, _, stage = metadata.split()
        if (stage != b"0" or mode not in (b"100644", b"100755") or
                p.is_symlink() or any(parent.is_symlink() for parent in p.parents) or not p.is_file()):
            fail(where, "invalid Git index mode or missing regular file")
            continue

        text = check_text(p.read_bytes(), where)
        if text is None:
            continue

        try:
            if p.suffix == ".py":
                # Python may otherwise echo the source line for a compilation warning.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    compile(text, "<tracked file>", "exec", dont_inherit=True)
                keys["python"] += 1
            elif p.suffix in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"):
                if p.suffix == ".json":
                    doc = json.loads(text)
                    if path in (PACKAGE, LOCKFILE):
                        manifests[path] = doc
                elif p.suffix in (".yaml", ".yml"):
                    for _ in yaml.safe_load_all(text):
                        pass
                elif p.suffix == ".toml":
                    tomllib.loads(text)
                else:
                    configparser.ConfigParser(interpolation=None).read_string(text)
                keys["config"] += 1
            if p.name == "SKILL.md" and len(p.parts) == 3 and p.parts[0] == "skills":
                parse_skill_frontmatter(text)
                keys["skill_entries"] += 1
        except SyntaxError as exc:
            fail(where, "Python syntax error" + error_location(exc))
        except (ValueError, OverflowError, RecursionError, yaml.YAMLError, configparser.Error) as exc:
            fail(where, "configuration error" + error_location(exc))

    skill_dirs = sorted({p.split("/")[1] for p in paths if p.startswith("skills/") and len(p.split("/")) > 2})
    for directory in skill_dirs:
        has_entry = f"skills/{directory}/SKILL.md" in paths
        has_requirements = f"skills/{directory}/requirements.txt" in paths
        if not has_entry and has_requirements:
            keys["partial_modules"] += 1
        elif not has_entry:
            fail("skills", "skill directory missing SKILL.md or requirements.txt")

    verify_workspace_lockfile(manifests)
    counts.update(keys)
    counts["tracked"] = len(paths)


if __name__ == "__main__":
    os.chdir(git("rev-parse", "--show-toplevel").decode("utf-8").strip())
    scan_history()
    verify_checkout()
    for where, reason in errors:
        print(f"{where}: {reason}", file=sys.stderr)
    print(json.dumps(counts, sort_keys=True))
    sys.exit(bool(errors))
