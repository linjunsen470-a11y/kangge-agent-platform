"""Validate the checked-out files and every locally available Git object without loading skills."""
import ast
import configparser
import csv
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tomllib
import unicodedata

import yaml


def git(*args, data=None):
    return subprocess.run(["git", *args], input=data, check=True, stdout=subprocess.PIPE).stdout


SECRET_RULES = {
    "private key": r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----",
    "provider credential": r"(?:\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}|github_pat_[\w]{24,}|\bsk-(?:proj-)?[\w-]{18,}|\bAIza[\w-]{35}\b|\bxox[bpars]-[\w-]{12,}|\bglpat-[\w-]{15,})",
    "signed token": r"\beyJ[\w-]{6,}\.[\w-]{8,}\.[\w-]{8,}\b",
    "signed URL": r"(?i)[?&](?:X-Amz-(?:Signature|Credential)|X-Goog-Signature|sig|access_token|auth_token)=[a-zA-Z0-9%+/._=-]{8,}",
    "URL credential": r"(?i)\b(?:https?|postgres(?:ql)?|mongodb(?:\+srv)?|redis|mysql)://[^\s'\x22/:@]+:[^\s'\x22/@]+@",
    "bearer credential": r"(?i)\bBearer[ \t]+[\w+/.-]{14,}",
    "personal identifier": r"(?<![a-zA-Z0-9])(?:1[3-9]\d{9}|[1-9]\d{16}[Xx\d])(?![a-zA-Z0-9])",
    "machine home": r"(?i)(?:/Users/|/home/|[A-Z]:\\Users\\)[a-z0-9_.-][a-z0-9._-]+[/\\]",
    "contact address": r"(?i)\b[\w.+%-]+@(?![\w.-]*example\.(?:invalid|com|org|net)\b)[a-z0-9.-]+\.[a-z]{2,}\b",
    "session cookie": r"(?i)\b(?:set-cookie|cookie)\s*:\s*(?:session(?:id)?|auth|token)=[a-z0-9_+.-]{6,}",
}
RULES = [(label, re.compile(pattern)) for label, pattern in SECRET_RULES.items()]
ASSIGNMENT = re.compile(
    r"""(?ix)(?<![\w-])(?:api[_-]?key|password|passwd|client[_-]?secret|app[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|private[_-]?key|session[_-]?cookie|secret[_-]?key)["']?\s*[:=]\s*["']([^"'\r\n]{4,})["']"""
)
UNQUOTED = re.compile(
    r"(?im)^\s*(?:export\s+)?(?:[A-Z][A-Z0-9_]*_)?(?:API_KEY|ACCESS_TOKEN|REFRESH_TOKEN|CLIENT_SECRET|PASSWORD|SECRET_KEY|SESSION_COOKIE)\s*=\s*([A-Za-z0-9][^\s#]{4,})\s*(?:#.*)?$"
)
PLACEHOLDER = re.compile(r"^(?:<[A-Z0-9_ -]+>|\$\{?[A-Za-z_][\w]*\}?|\{\{\s*[\w.-]+\s*\}\})$")
FORBIDDEN_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".cache", ".pytest_cache", "quarantine", "raw", ".ssh"}
FORBIDDEN_SUFFIX = {".zip", ".tgz", ".tar", ".gz", ".7z", ".rar", ".p12", ".pfx", ".pem", ".key", ".sqlite", ".db", ".log", ".pyc", ".bundle"}
FORBIDDEN_NAMES = {"credentials.json", "cookies.txt", "id_rsa", "id_ed25519", ".npmrc", ".netrc", "thumbs.db"}
ARCHIVE_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"\x1f\x8b", b"Rar!\x1a\x07", b"7z\xbc\xaf\x27\x1c", b"\x7fELF")
errors = []
counts = {}


def fail(where, category):
    # Object positions and counters support investigation without printing private text or paths.
    errors.append((where, category))


def check_text(raw, where):
    if raw.startswith(ARCHIVE_MAGIC) or b"\x00" in raw:
        fail(where, "binary/archive")
        return None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        fail(where, "non-UTF-8 content")
        return None
    if re.search("[\u202a-\u202e\u2066-\u2069]", text):
        fail(where, "bidirectional control")
    for name, rule in RULES:
        if rule.search(text):
            fail(where, name)
    if UNQUOTED.search(text) or any(not PLACEHOLDER.fullmatch(m[1]) for m in ASSIGNMENT.finditer(text)):
        fail(where, "credential assignment")
    return text


def check_path(path, where):
    parts = PurePosixPath(path).parts
    if not parts or path.startswith("/") or any(
        p in {".", ".."} or p.casefold() in FORBIDDEN_DIRS or p.casefold() in FORBIDDEN_NAMES
        or p.rstrip(" .") != p or re.search(r'[\x00-\x1f\x7f<>:"|?*\\]', p)
        or re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p, re.I)
        or (p.startswith(".env") and p != ".env.example")
        for p in parts
    ) or PurePosixPath(path).suffix.lower() in FORBIDDEN_SUFFIX:
        fail(where, "prohibited path")
    check_text(path.encode(), where)


def scan_git_database():
    types = {"blob": 0, "commit": 0, "tree": 0, "tag": 0}
    oid_bytes = 32 if git("rev-parse", "--show-object-format").strip() == b"sha256" else 20
    with subprocess.Popen(["git", "cat-file", "--batch-all-objects", "--batch"], stdout=subprocess.PIPE) as proc:
        stream = proc.stdout
        for index, header in enumerate(iter(stream.readline, b""), 1):
            _, obj_type, size = header.split()
            kind = obj_type.decode("ascii")
            types[kind] += 1
            raw = stream.read(int(size))
            if len(raw) != int(size) or stream.read(1) != b"\n":
                raise ValueError("truncated object stream")
            where = f"object {index}"
            if kind != "tree":
                if kind in {"commit", "tag"}:
                    header, delimiter, message = raw.partition(b"\n\n")
                    header = re.sub(
                        rb"(?m)^((?:author|committer|tagger) [^\n<]*<)(?:noreply@github\.com|[A-Za-z0-9+_-]+@users\.noreply\.github\.com)(> [0-9]+ [+-][0-9]{4})$",
                        rb"\1public-bot@example.invalid\2",
                        header,
                    )
                    raw = header + delimiter + message
                check_text(raw, where)
                continue
            pos = 0
            names = set()
            while pos < len(raw):
                end = raw.index(0, pos)
                mode, name = raw[pos:end].split(b" ", 1)
                label = name.decode("utf-8")
                check_path(label, where)
                norm = unicodedata.normalize("NFKC", label).casefold()
                if norm in names or "/" in label:
                    fail(where, "tree path collision")
                names.add(norm)
                if mode not in (b"40000", b"100644", b"100755"):
                    fail(where, "non-regular Git object mode")
                pos = end + 1 + oid_bytes
            if pos != len(raw):
                raise ValueError("invalid tree record")
        if proc.wait():
            raise ValueError("git cat-file failed")
    counts.update(types)


def read_yaml(text):
    return list(yaml.safe_load_all(text))


def verify_checkout():
    keys = {"python": 0, "config": 0, "skill_entries": 0, "partial_modules": 0}
    modes = git("ls-files", "--stage", "-z").split(b"\0")
    paths = set()
    for i, item in enumerate(filter(None, modes), 1):
        metadata, raw_name = item.split(b"\t", 1)
        path = raw_name.decode("utf-8")
        paths.add(path)
        where = f"index {i}"
        check_path(path, where)
        p = Path(path)
        mode, _, stage = metadata.split()
        if stage != b"0" or mode not in (b"100644", b"100755") or p.is_symlink() or not p.is_file():
            fail(where, "index mode or missing regular file")
            continue
        text = check_text(p.read_bytes(), where)
        if text is None:
            continue
        try:
            if p.suffix == ".py":
                ast.parse(text)
                compile(text, "<checked file>", "exec", dont_inherit=True)
                keys["python"] += 1
            elif p.suffix in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg") or p.name == ".env.example":
                if p.suffix == ".json":
                    json.loads(text)
                elif p.suffix in (".yaml", ".yml"):
                    read_yaml(text)
                elif p.suffix == ".toml":
                    tomllib.loads(text)
                elif p.name == ".env.example":
                    for line in text.splitlines():
                        if not line.strip() or line.lstrip().startswith("#"):
                            continue
                        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*=(?:<[A-Z0-9_]+>)?", line):
                            raise ValueError("environment example")
                else:
                    configparser.ConfigParser(interpolation=None).read_string(text)
                keys["config"] += 1
            if p.name == "SKILL.md" and p.parts[0] == "skills":
                lines = text.splitlines()
                if not lines or lines[0].strip() != "---":
                    raise ValueError("missing front matter")
                meta = yaml.safe_load("\n".join(lines[1:lines.index("---", 1)]))
                if not isinstance(meta, dict) or any(not isinstance(meta.get(k), str) or not meta[k].strip() for k in ("name", "description")):
                    raise ValueError("missing skill metadata")
                keys["skill_entries"] += 1
        except (SyntaxError, ValueError, yaml.YAMLError, configparser.Error):
            fail(where, "syntax or configuration")
    manifest = "docs/skill-modules.tsv"
    if manifest not in paths:
        fail("module catalog", "missing")
    else:
        with open(manifest, encoding="utf-8", newline="") as f:
            records = list(csv.DictReader(f, delimiter="\t"))
        mapped = {r["directory"]: r["status"] for r in records if r["directory"]}
        dirs = {p.split("/")[1] for p in paths if p.startswith("skills/") and len(p.split("/")) > 2}
        expected = {d for d, state in mapped.items() if state in {"entry", "partial"}}
        if dirs != expected or sum(bool(r["directory"]) for r in records) != len(mapped):
            fail("module catalog", "directories disagree")
        for d, state in mapped.items():
            if (f"skills/{d}/SKILL.md" in paths) != (state == "entry"):
                fail("module catalog", "entry/partial mismatch")
            keys["partial_modules"] += state == "partial"
    counts.update(keys)
    counts["tracked"] = len(paths)


if __name__ == "__main__":
    os.chdir(git("rev-parse", "--show-toplevel").decode().strip())
    scan_git_database()
    verify_checkout()
    for where, reason in errors:
        print(f"{where}: {reason}", file=sys.stderr)
    print(json.dumps(counts, sort_keys=True))
    sys.exit(bool(errors))
