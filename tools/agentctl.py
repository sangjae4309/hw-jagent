#!/usr/bin/env python3
"""Repository-local Codex environment tooling. Python 3.8+, standard library only.

This CLI never launches a hardware tool, model, scheduler, network request or job.
Agents make semantic decisions; this program performs auditable file operations.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import uuid

VERSION = "0.2.0"
ENVIRONMENT_ID = "portable-hardware-agent-environment"
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "sim", "build", "dist", ".Xil", "_x"}
ROLES = ["hw-runner", "rtl-analyst", "hw-emu-analyst", "evidence-integrator", "env-curator"]
STAGES = {"csim", "csynth", "rtl_sim", "hw_emu", "implementation", "board"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
IGNORE_BLOCK = """
# codex-env machine-local settings and drafts
.agent/upstream.local.json
.agent/staging/
.agent/.lock/
.agent/drafts/
.agent/block-plan.json
.agent/migration-plan.json
"""


class EnvError(Exception):
    """An actionable validation or safety failure."""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise EnvError("Cannot read JSON {}: {}".format(path, exc)) from exc


def require(condition, message):
    if not condition:
        raise EnvError(message)


def valid_id(value):
    require(isinstance(value, str) and ID_RE.fullmatch(value), "Invalid ID: {!r}".format(value))
    return value


def safe(root, relative):
    """Reject absolute/parent paths and symlinks for every managed read/write."""
    require(isinstance(relative, str) and relative and "\\" not in relative, "Invalid relative path")
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and ".." not in parts.parts and parts.parts[0] != ".git", "Unsafe path: " + relative)
    path = root
    for part in parts.parts:
        path = path / part
        require(not path.is_symlink(), "Refusing symlink traversal: " + str(path))
    require(path != root, "A file path, not the repository root, is required")
    return path


def read_bytes(root, relative):
    path = safe(root, relative)
    if path.exists():
        require(path.is_file(), "Expected file: " + relative)
        return path.read_bytes()
    return None


def atomic(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".agentctl-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def locked(root):
    lock = safe(root, ".agent/.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise EnvError("Another agentctl operation holds .agent/.lock. Inspect owner.json; remove a stale lock only after checking that process.") from exc
    try:
        atomic(lock / "owner.json", dump({"pid": os.getpid(), "host": socket.gethostname(), "time": now()}))
        yield
    finally:
        (lock / "owner.json").unlink(missing_ok=True)
        lock.rmdir()


def walk(root, include_agent=False):
    """Bounded to regular repository files; never follow symbolic links."""
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and (include_agent or d != ".agent") and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            p = Path(base) / name
            if p.is_file() and not p.is_symlink():
                yield p


def transaction(root, changes, reason, dry_run=False):
    """Apply checked files without any disk backup or persistent rollback data.

    Original bytes live only in RAM for best-effort recovery from a caught error.
    A process kill or machine failure can leave a partial multi-file operation.
    """
    changes = {rel: data for rel, data in changes.items() if read_bytes(root, rel) != data}
    if not changes:
        print("No changes required.")
        return 0
    operations = [{"path": rel, "action": "remove" if data is None else "write"} for rel, data in sorted(changes.items())]
    if dry_run:
        print(dump({"reason": reason, "backup": False, "changes": operations}).decode(), end="")
        return 0
    originals = {}
    for rel in changes:
        original = read_bytes(root, rel)
        mode = stat.S_IMODE(safe(root, rel).stat().st_mode) if original is not None else 0o644
        originals[rel] = (original, mode)
    written = []
    try:
        # Write destinations before removing source files during a relocation.
        ordered = sorted(changes, key=lambda rel: (changes[rel] is None, rel))
        for rel in ordered:
            content = changes[rel]
            if content is None:
                safe(root, rel).unlink(missing_ok=True)
            else:
                atomic(safe(root, rel), content, originals[rel][1])
            written.append(rel)
    except Exception:
        for rel in reversed(written):
            data, mode = originals[rel]
            if data is None:
                safe(root, rel).unlink(missing_ok=True)
            else:
                atomic(safe(root, rel), data, mode)
        raise
    # Remove empty obsolete directories, but never walk outside the project.
    parents = {safe(root, rel).parent for rel, data in changes.items() if data is None}
    for parent in sorted(parents, key=lambda v: len(v.parts), reverse=True):
        while parent != root and parent.name not in {".agent", ".git"}:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    print("Applied {} file changes: {}. No backup or rollback snapshot created.".format(len(changes), reason))
    return len(changes)


def package_root():
    package = Path(__file__).resolve().parent.parent
    require((package / "VERSION").is_file() and (package / "templates").is_dir(),
            "Run install/transfer from the external environment source or staged CLI, not the installed CLI. See upstream show.")
    return package


def payload(package):
    files = {}
    for folder, destination in [("policies", ".agent/system/policies"), ("templates", ".agent/system/templates"),
                                ("general", ".agent/rules"), ("agents", ".codex/agents"), ("skills", ".agents/skills")]:
        for p in walk(package / folder):
            files[destination + "/" + p.relative_to(package / folder).as_posix()] = p.read_bytes()
    for p in (package / "tools").glob("*.py"):
        require(not p.is_symlink(), "Source toolkit scripts may not be symlinks")
        files[".agent/system/" + p.name] = p.read_bytes()
    files["AGENTS.md"] = (package / "templates/AGENTS.md").read_bytes()
    return files


def normalized_ignore(data):
    text = data.decode("utf-8")
    text = re.sub(r"\n# codex-env local recovery and drafts\n(?:\.agent/[^\n]*\n)*", "\n", text)
    if "# codex-env machine-local settings and drafts" not in text:
        text += IGNORE_BLOCK
    return text.encode()


def install_changes(root, package, replacing=None, update=False, reset=False):
    replacing = set(replacing or [])
    managed = payload(package)
    old_lock = load(root / ".agent/environment.lock.json") if (root / ".agent/environment.lock.json").is_file() and not reset else None
    old_hashes = old_lock.get("managed", {}) if old_lock else {}
    conflicts = []
    for rel, data in managed.items():
        current = read_bytes(root, rel)
        if current is not None and current != data and rel not in replacing:
            if not old_lock or rel not in old_hashes or digest(current) != old_hashes[rel]:
                conflicts.append(rel)
    require(not conflicts, "Locally edited/unmanaged files would be replaced:\n  " + "\n  ".join(conflicts) + "\nUse the reviewed clean-transfer workflow or reconcile the edits.")
    hashes = {k: digest(v) for k, v in sorted(managed.items())}
    if old_lock and hashes != old_hashes:
        require(update, "Environment changed. Use install.sh --update; project memory stays untouched.")
    changes = dict(managed)
    for p in walk(package / "templates/memory"):
        rel = ".agent/memory/" + p.relative_to(package / "templates/memory").as_posix()
        if reset or read_bytes(root, rel) is None:
            changes[rel] = p.read_bytes()
    for p in sorted((package / "agents").glob("*.toml")):
        role = parse_agent(p.read_text(), p.name)["name"]
        rel = ".agent/memory/agents/{}/MEMORY.md".format(valid_id(role))
        if reset or read_bytes(root, rel) is None:
            changes[rel] = ("# " + role + " project lessons\n\nNo material lessons recorded. Link canonical experiments/findings; do not duplicate metrics.\n").encode()
    for rel, data in [(".agent/project.json", (package / "templates/project.json").read_bytes()),
                      (".agent/blocks.json", dump({"schema_version": 1, "blocks": {}}))]:
        if reset or read_bytes(root, rel) is None:
            changes[rel] = data
    changes[".gitignore"] = normalized_ignore(read_bytes(root, ".gitignore") or b"")
    fingerprint = digest(dump(hashes))
    if reset or not old_lock or old_lock.get("package_fingerprint") != fingerprint:
        changes[".agent/environment.lock.json"] = dump({"schema_version": 2, "environment_id": ENVIRONMENT_ID,
            "version": (package / "VERSION").read_text().strip(), "installed_at": now(),
            "package_fingerprint": fingerprint, "managed": hashes})
    for rel in set(old_hashes) - set(hashes):
        current = read_bytes(root, rel)
        require(current is None or digest(current) == old_hashes[rel], "Obsolete managed file was edited; reconcile before update: " + rel)
        changes[rel] = None
    # A source checkout can be renamed; no upstream directory name is hard-coded.
    if ".agent/staging/" not in package.as_posix():
        changes[".agent/upstream.local.json"] = dump({"schema_version": 1, "environment_id": ENVIRONMENT_ID, "path": str(package.resolve())})
    return changes


CONTROL_NAMES = {"AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", ".clinerules", ".windsurfrules"}
CONTROL_PREFIXES = (".codex/agents/", ".codex/skills/", ".codex/rules/", ".codex/hooks/",
                    ".agents/skills/", ".claude/agents/", ".claude/skills/", ".claude/commands/", ".claude/rules/", ".claude/hooks/",
                    ".cursor/rules/", ".github/instructions/", ".agent/system/", ".agent/rules/")
CONTROL_FILES = {".codex/config.toml", ".codex/hooks.json", ".claude/settings.json", ".claude/settings.local.json",
                 ".github/copilot-instructions.md", ".agent/environment.lock.json", ".agent/blocks.json", ".agent/project.json", "docs/AGENT_MEMORY.md"}
KNOWLEDGE_PREFIXES = (".agent/memory/", ".codex/memory/", ".claude/memory/", ".agents/memory/", "docs/")


def classify_legacy(rel):
    if rel.startswith((".agent/staging/", ".agent/.lock/", ".agent/drafts/")) or rel in {".agent/upstream.local.json", ".agent/block-plan.json", ".agent/migration-plan.json"}:
        return None
    if rel.startswith(".agent/backups/"):
        return "obsolete-backup"
    if PurePosixPath(rel).name in CONTROL_NAMES or rel in CONTROL_FILES or rel.startswith(CONTROL_PREFIXES):
        return "active-control"
    if rel.startswith(KNOWLEDGE_PREFIXES):
        return "knowledge"
    return None


def inventory(root):
    entries, symlinks = [], []
    staged = {}
    marker = safe(root, ".agent/staging/bootstrap.json")
    if marker.is_file():
        staged = load(marker).get("bootstrap_skill_hashes", {})
    for p in walk(root, include_agent=True):
        rel = p.relative_to(root).as_posix()
        kind = classify_legacy(rel)
        if not kind:
            continue
        sha = file_digest(p)
        if staged.get(rel) == sha:
            continue
        entries.append({"path": rel, "sha256": sha, "bytes": p.stat().st_size, "kind": kind})
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP and d not in {"staging", ".lock", "drafts"}]
        for name in dirs + names:
            p = Path(base) / name
            if p.is_symlink():
                rel = p.relative_to(root).as_posix()
                if classify_legacy(rel) == "active-control" or any((prefix.rstrip("/") == rel or prefix.startswith(rel + "/")) for prefix in CONTROL_PREFIXES):
                    symlinks.append(rel)
    return {"files": sorted(entries, key=lambda x: x["path"]), "blocked_symlinks": sorted(set(symlinks))}


def bootstrap(root, package, dry_run=False):
    changes = {}
    for folder in ["tools", "templates", "policies", "general", "agents", "skills"]:
        for p in walk(package / folder):
            rel = ".agent/staging/codex-env/" + p.relative_to(package).as_posix()
            changes[rel] = p.read_bytes()
    for name in ["VERSION", "ENVIRONMENT_ID"]:
        changes[".agent/staging/codex-env/" + name] = (package / name).read_bytes()
    cli_rel = ".agent/staging/codex-env/tools/agentctl.py"
    skill_changes = {}
    for p in walk(package / "skills/jagent-transfer"):
        rel = ".agents/skills/jagent-transfer/" + p.relative_to(package / "skills/jagent-transfer").as_posix()
        # The user requested this replacement system. Only its bootstrap entry is replaced here.
        skill_changes[rel] = p.read_bytes()
    changes.update(skill_changes)
    changes[".agent/staging/bootstrap.json"] = dump({"schema_version": 2, "source": str(package),
        "bootstrap_skill_hashes": {k: digest(v) for k, v in skill_changes.items()}})
    changes[".agent/upstream.local.json"] = dump({"schema_version": 1, "environment_id": ENVIRONMENT_ID, "path": str(package.resolve())})
    changes[".gitignore"] = normalized_ignore(read_bytes(root, ".gitignore") or b"")
    transaction(root, changes, "stage clean-transfer tooling (no backups)", dry_run=dry_run)
    print("Existing agent controls detected. Root AGENTS and project files are not replaced yet.\nRestart Codex if needed and invoke $jagent-transfer. Staged CLI: " + cli_rel)


def cmd_install(args, root):
    package = package_root()
    require(root != package and root not in package.parents and package not in root.parents,
            "Use a separate project directory outside the environment source checkout.")
    lockpath = root / ".agent/environment.lock.json"
    existing = load(lockpath) if lockpath.is_file() else {}
    native = existing.get("schema_version") == 2 and existing.get("environment_id") == ENVIRONMENT_ID
    inv = inventory(root) if not native else {"files": [], "blocked_symlinks": []}
    require(not inv["blocked_symlinks"], "Resolve active instruction symlinks without following them before transfer: " + ", ".join(inv["blocked_symlinks"]))
    legacy = [x for x in inv["files"] if x["kind"] in {"active-control", "obsolete-backup"} or x["path"].startswith(".agent/memory/")]
    if legacy:
        return bootstrap(root, package, args.dry_run)
    changes = install_changes(root, package, update=args.update)
    transaction(root, changes, "install/update portable environment", dry_run=args.dry_run)
    print("Installed. Use $jagent-block-scan or $jagent-block-add in Codex. No hardware tool was run.")


def output_json(root, value, out=None):
    if out:
        atomic(safe(root, out), dump(value))
        print(out)
    else:
        print(dump(value).decode(), end="")


def cmd_migration_plan(args, root):
    inv = inventory(root)
    require(not inv["blocked_symlinks"], "Active instruction symlinks need explicit resolution: " + ", ".join(inv["blocked_symlinks"]))
    knowledge = []
    for item in inv["files"]:
        if item["kind"] != "knowledge":
            continue
        rel = item["path"]
        old_memory = not rel.startswith("docs/")
        historical = old_memory or any(x in rel.lower() for x in ["history", "experiment", "pitfall", "incident"])
        dest = ".agent/memory/history/" + ("previous-memory/" + rel.lstrip(".") if old_memory else rel)
        knowledge.append({"path": rel, "action": "move" if historical else "retain", "destination": dest if historical else None,
                          "reason": "Review this classification and preserve useful evidence."})
    plan = {"schema_version": 2, "mode": "replace-no-backup", "created_at": now(), "approved": False,
            "approval_note": "", "controls_reviewed": False, "discard_knowledge_acknowledged": False,
            "inventory": inv["files"], "knowledge": knowledge, "memory_edits": [], "runner_config": None,
            "instructions": "All inventoried old agent controls (including AGENTS.md) are removed/replaced. No backups or rollback. Review knowledge: move into canonical history, integrate into approved memory edits, retain unrelated project docs, or explicitly discard. Preserve source, fixtures and unrelated documents. Review with jagent-grill before approval."}
    output_json(root, plan, args.out)


def migration_destination(rel):
    return (rel.startswith(".agent/memory/") and rel.endswith((".md", ".json", ".txt", ".csv", ".log")))


def relocate_markdown(data, source, destination, moves, root):
    """Retarget ordinary relative Markdown links after moving a history file.

    Do not alter code snippets, prose paths, reference-style links or unknown targets.
    Their original path context is retained in migration-map.json.
    """
    if not source.endswith(".md"):
        return data
    import posixpath
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return data
    def link(match):
        target = match.group(1)
        if ":" in target or target.startswith(("#", "/")) or " " in target:
            return match.group(0)
        filepart, sep, anchor = target.partition("#")
        old = posixpath.normpath(posixpath.join(posixpath.dirname(source), filepart))
        if old.startswith("../") or not (root / old).exists():
            return match.group(0)
        mapped = moves.get(old, old)
        relative = posixpath.relpath(mapped, posixpath.dirname(destination))
        return "](" + relative + (sep + anchor if sep else "") + ")"
    return re.sub(r"\]\(([^)\n]+)\)", link, text).encode()


def cmd_migration_apply(args, root):
    plan = load(args.plan)
    require(plan.get("schema_version") == 2 and plan.get("mode") == "replace-no-backup", "Regenerate a v2 clean-transfer plan")
    require(plan.get("controls_reviewed") is True, "Review existing control rules and resolve project constraints first")
    if not args.dry_run:
        require(args.approve and args.confirm_no_backup and plan.get("approved") is True and str(plan.get("approval_note", "")).strip(),
                "Final approval, approved=true, approval_note and --confirm-no-backup are required. There is no rollback.")
    package = package_root()
    inv = inventory(root)
    require(not inv["blocked_symlinks"], "Active instruction symlinks changed; resolve them before transfer")
    expected = {x["path"]: (x["sha256"], x["kind"]) for x in plan["inventory"]}
    current = {x["path"]: (x["sha256"], x["kind"]) for x in inv["files"]}
    require(expected == current, "Control/history files changed after planning. Regenerate or reconcile the plan.")
    controls = {x["path"] for x in inv["files"] if x["kind"] in {"active-control", "obsolete-backup"}}
    knowledge = {x["path"] for x in inv["files"] if x["kind"] == "knowledge"}
    choices = plan.get("knowledge", [])
    require(len({x["path"] for x in choices}) == len(choices) and {x["path"] for x in choices} == knowledge, "Every inventoried knowledge file needs exactly one decision")
    edits = plan.get("memory_edits", [])
    edit_sources = set()
    for edit in edits:
        rel = edit["path"]
        safe(root, rel)
        require(migration_destination(rel) and isinstance(edit.get("content"), str) and len(edit["content"]) <= 2000000, "Invalid canonical memory edit")
        edit_sources.update(edit.get("sources", []))
    changes = {rel: None for rel in controls}
    moves, removed, retained, discarded = {}, set(), [], []
    destinations = set()
    for choice in choices:
        rel, action = choice["path"], choice.get("action")
        require(action in {"move", "integrate", "retain", "discard"} and str(choice.get("reason", "")).strip(), "Unresolved knowledge decision: " + rel)
        if action == "retain":
            require(rel.startswith("docs/"), "Old agent memories must move or integrate, not remain under an obsolete route: " + rel)
            retained.append(rel)
            continue
        removed.add(rel)
        changes[rel] = None
        if action == "move":
            dest = choice.get("destination", "")
            safe(root, dest)
            require(dest.startswith(".agent/memory/history/") and dest != rel and dest not in destinations, "Invalid/duplicate history destination")
            require(read_bytes(root, dest) is None or dest in knowledge, "History destination already exists: " + dest)
            require(dest not in knowledge, "History destination overlaps a migration input; choose a fresh canonical path")
            destinations.add(dest)
            moves[rel] = dest
        elif action == "integrate":
            require(rel in edit_sources, "Integrated knowledge needs a memory_edit with this file in sources: " + rel)
        else:
            require(plan.get("discard_knowledge_acknowledged") is True, "Discarding knowledge needs explicit acknowledgement: " + rel)
            discarded.append(rel)
    require(len({x["path"] for x in edits}) == len(edits) and not destinations.intersection(x["path"] for x in edits), "Duplicate/overlapping memory destinations")
    # Materialize the new system, then overlay user-approved canonical knowledge.
    changes.update(install_changes(root, package, replacing=controls | removed, update=True, reset=True))
    for rel, dest in moves.items():
        changes[dest] = relocate_markdown(read_bytes(root, rel), rel, dest, moves, root)
    for edit in edits:
        changes[edit["path"]] = edit["content"].encode()
    if plan.get("runner_config") is not None:
        config = plan["runner_config"]
        require(isinstance(config, dict) and isinstance(config.get("runners"), dict), "runner_config requires inspected runner interfaces")
        changes[".agent/project.json"] = dump(config)
    changes[".agent/memory/migration-map.json"] = dump({"schema_version": 2, "migrated_at": now(),
        "mode": "canonical relocation, not a backup", "moves": moves, "retained_project_docs": retained,
        "integrated": sorted(removed - set(moves) - set(discarded)), "discarded": discarded,
        "path_note": "Unchanged prose/reference links inside moved files may use their original root-relative path context. Use moves to resolve them. Old instructions are historical evidence, not authority."})
    changes[".agent/memory/project/MIGRATION.md"] = ("# Clean transfer\n\n" + str(plan.get("approval_note", "Preview")) +
        "\n\nOld agent controls were removed; AGENTS.md was replaced. No backup or rollback exists. Retained knowledge is canonical memory, not an active legacy rule system. Consult migration-map.json; recreate block owners from current source.\n").encode()
    for p in walk(root / ".agent/staging", include_agent=True):
        changes[p.relative_to(root).as_posix()] = None
    plan_path = Path(args.plan).resolve()
    try:
        rel = plan_path.relative_to(root).as_posix()
        if rel.startswith((".agent/drafts/", ".agent/staging/")) or rel == ".agent/migration-plan.json":
            changes[rel] = None
    except ValueError:
        pass
    transaction(root, changes, "approved clean transfer; old agent controls removed", dry_run=args.dry_run)
    if not args.dry_run:
        print("Transfer complete. No backup or rollback. Restart Codex, run doctor, then $jagent-block-scan or $jagent-block-add.")


def registry(root):
    return load(safe(root, ".agent/blocks.json"))


def fingerprints(root, paths):
    result = {}
    for rel in paths:
        path = safe(root, rel)
        require(path.exists(), "Missing source path: " + rel)
        if path.is_dir():
            for p in walk(path):
                result[p.relative_to(root).as_posix()] = file_digest(p)
        else:
            result[rel] = file_digest(path)
    return dict(sorted(result.items()))


def overlaps(a, b):
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def cmd_block_scan(args, root):
    found = {}
    extensions = {".cpp", ".cc", ".c", ".h", ".hpp", ".cu", ".v", ".sv", ".vhd", ".vhdl"}
    for p in walk(root):
        rel = p.relative_to(root).as_posix()
        if rel.startswith(("docs/", ".codex/", ".agents/")) or p.suffix.lower() not in extensions or p.stat().st_size > 2 * 1024 * 1024:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        signals = []
        if re.search(r"#\s*pragma\s+HLS\s+(INTERFACE|DATAFLOW|PIPELINE|UNROLL)", text):
            signals.append("HLS pragmas")
        if p.suffix.lower() in {".v", ".sv", ".vhd", ".vhdl"}:
            signals.append("RTL source (verify generated vs authored)")
        if "adf::graph" in text or "aie::" in text:
            signals.append("AIE source/graph")
        if "__global__" in text:
            signals.append("CUDA kernel; decide whether software reference or owner block")
        if signals:
            parent = p.parent.relative_to(root).as_posix()
            item = found.setdefault(parent, {"directory": parent, "files": [], "signals": set()})
            item["files"].append(rel)
            item["signals"].update(signals)
    known = registry(root)["blocks"]
    used = set(known)
    candidates, blocks = [], []
    for folder, data in sorted(found.items()):
        base = re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-")[-65:] or "root-hardware"
        bid = base
        counter = 2
        while bid in used:
            bid = base + "-" + str(counter)
            counter += 1
        used.add(bid)
        candidates.append({"suggested_id": bid, "directory": folder, "files": data["files"], "signals": sorted(data["signals"])})
        blocks.append({"id": bid, "description": "Candidate boundary; review interfaces and variants with the user.", "owned_paths": data["files"], "shared_read_paths": [], "dependencies": [], "interfaces": [], "style_profiles": ["common"], "approved_boundary": False})
    output_json(root, {"schema_version": 1, "approved": False, "approval_note": "", "scan_scope": "lexical regular-file candidates; sim/build/symlinks excluded", "existing_blocks": list(known), "candidates": candidates, "blocks": blocks}, args.out)


def cmd_block_add(args, root):
    """Create a draft for exactly one block; never scan or approve implicitly."""
    bid = valid_id(args.id)
    reg = registry(root)["blocks"]
    require(bid not in reg, "Block already registered; existing memory will not be overwritten")
    for rel in args.path:
        require(safe(root, rel).exists(), "Inspect/create the approved source path before registering it: " + rel)
        require(not rel.startswith((".agent/", ".agents/", ".codex/", "docs/")) and PurePosixPath(rel).parts[0] not in SKIP,
                "Ownership must target source paths")
        for owner, block in reg.items():
            require(not any(overlaps(rel, old) for old in block["owned_paths"]), "Path already owned by block " + owner + ": " + rel)
    profiles = list(dict.fromkeys(["common"] + args.profile))
    for profile in profiles:
        require(safe(root, ".agent/rules/code-style/" + profile + ".md").is_file(), "Unknown style profile: " + profile)
    for rel in args.shared_path:
        require(safe(root, rel).exists(), "Missing shared read path: " + rel)
    require(set(args.depends_on) <= set(reg), "A dependency must be an existing block ID")
    block = {"id": bid, "description": args.description, "owned_paths": args.path, "shared_read_paths": args.shared_path,
             "dependencies": args.depends_on, "interfaces": args.interface, "style_profiles": profiles, "approved_boundary": False}
    output_json(root, {"schema_version": 1, "approved": False, "approval_note": "", "blocks": [block],
                      "scope": "single block; no repository-wide scan"}, args.out)


def block_memory(block):
    return ("# Block: {id}\n\n## Responsibility\n{description}\n\n## Current design\nNot yet summarized from source. Boundary approval is not hardware verification.\n\n## Interfaces and dependencies\nSee .agent/blocks.json. Confirm semantics from actual source before using.\n\n## Design decisions and rejected alternatives\nNone recorded. Link ADRs and experiments, including failures.\n\n## Performance and area\nNo verified measurements recorded. Link immutable experiment IDs; unknown is not zero.\n\n## Next-design checks\nRead code-style and code-pitfall indexes, applicable pitfall notes, pending inbox findings and historical experiments before changing the design.\n\n## Accepted feedback\n<!-- feedback:start -->\nNo owner-reviewed findings yet.\n<!-- feedback:end -->\n").format(**block).encode()


def cmd_block_apply(args, root):
    plan = load(args.plan)
    require(plan.get("schema_version") == 1, "Unsupported block plan schema")
    require(args.approve and plan.get("approved") is True and plan.get("approval_note"), "User-confirmed boundaries and --approve are required")
    reg = registry(root)
    proposed = plan.get("blocks", [])
    require(proposed, "No blocks selected")
    ids = [valid_id(b.get("id")) for b in proposed]
    require(len(ids) == len(set(ids)), "Duplicate proposed block ID")
    require(not set(ids) & set(reg["blocks"]), "Existing blocks will not be overwritten; revise the plan to add only new owners")
    all_ids = set(ids) | set(reg["blocks"])
    owners = [(path, bid) for bid, b in reg["blocks"].items() for path in b["owned_paths"]]
    changes = {}
    template = safe(root, ".agent/system/templates/block-agent.txt").read_text()
    for b in proposed:
        bid = b["id"]
        require(b.get("approved_boundary") is True and b.get("description"), "Boundary not confirmed: " + bid)
        require(isinstance(b.get("owned_paths"), list) and b["owned_paths"], "Block needs explicit owned paths")
        for rel in b["owned_paths"]:
            safe(root, rel)
            require(not rel.startswith((".agent/", ".agents/", ".codex/", "docs/")) and PurePosixPath(rel).parts[0] not in SKIP, "Block ownership must target source, not memory/build/control files")
            for oldpath, owner in owners:
                require(not overlaps(rel, oldpath), "Overlapping write ownership: {} ({}) vs {} ({})".format(rel, bid, oldpath, owner))
            owners.append((rel, bid))
        for rel in b.get("shared_read_paths", []):
            require(safe(root, rel).exists(), "Missing shared-read path: " + rel)
        deps = b.get("dependencies", [])
        require(set(deps) <= all_ids and bid not in deps, "Unknown/self dependency for " + bid)
        profiles = b.get("style_profiles", ["common"])
        require(isinstance(profiles, list) and all(safe(root, ".agent/rules/code-style/" + p + ".md").is_file() for p in profiles), "Unknown style profile")
        b = dict(b)
        b.update({"agent": "block-" + bid, "source_hashes": fingerprints(root, b["owned_paths"]), "last_reviewed_at": now(), "review_note": "Initial boundary registration; functional design summary remains unverified"})
        reg["blocks"][bid] = b
        role = "name = " + json.dumps("block-" + bid) + "\ndescription = " + json.dumps("Design owner for " + bid + ": " + b["description"]) + "\ndeveloper_instructions = " + json.dumps(template.format(block_id=bid)) + "\n"
        rel = ".codex/agents/block-" + bid + ".toml"
        require(read_bytes(root, rel) is None, "Existing unregistered role: " + rel)
        mem = ".agent/memory/blocks/" + bid + "/MEMORY.md"
        require(read_bytes(root, mem) is None, "Existing unregistered block memory: " + bid)
        changes[rel] = role.encode()
        changes[mem] = block_memory(b)
    changes[".agent/blocks.json"] = dump(reg)
    transaction(root, changes, "register user-confirmed block owners")
    print("Block roles and separate memories created. No synthesis or functional verification was performed.")


def cmd_block_refresh(args, root):
    reg = registry(root)
    require(args.block in reg["blocks"], "Unknown block")
    require(args.note.strip(), "A source-review scope note is required")
    b = reg["blocks"][args.block]
    b.update({"source_hashes": fingerprints(root, b["owned_paths"]), "last_reviewed_at": now(), "review_note": args.note})
    transaction(root, {".agent/blocks.json": dump(reg)}, "owner source review: " + args.block)
    print("Source fingerprint refreshed; this is not synthesis/runtime verification.")


def git_identity(root):
    result = {"revision": None, "dirty": None, "snapshot_sha256": None}
    if shutil.which("git"):
        try:
            proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                result["revision"] = proc.stdout.strip()
                status = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"], capture_output=True, text=True, timeout=5)
                result["dirty"] = bool(status.stdout.strip()) if status.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            pass
    return result


def cmd_experiment_draft(args, root):
    eid = valid_id(args.id)
    reg = registry(root)["blocks"]
    require(all(b in reg for b in args.block), "Unknown block in experiment draft")
    record = load(safe(root, ".agent/system/templates/experiment.json"))
    record.update({"id": eid, "blocks": args.block, "stage": args.stage})
    record["source"] = git_identity(root)
    hashes = {}
    for bid in args.block:
        hashes.update(fingerprints(root, reg[bid]["owned_paths"] + reg[bid].get("shared_read_paths", [])))
    if hashes:
        record["source"]["snapshot_sha256"] = digest(dump(hashes))
        record["source"]["files"] = hashes
    record["config"]["variant"] = args.variant
    record["metrics"] = {}  # The agent must choose metrics and scope from actual evidence.
    out = args.out or ".agent/drafts/" + eid + ".json"
    require(read_bytes(root, out) is None, "Draft already exists; refusing to overwrite: " + out)
    transaction(root, {out: dump(record)}, "create unmeasured experiment draft")
    print("Draft: {}. Fill observed evidence and metadata, then experiment record --file {}".format(out, out))


def validate_experiment(record, root):
    require(record.get("schema_version") == 1, "Unsupported experiment schema")
    valid_id(record.get("id"))
    require(record.get("stage") in STAGES, "Unknown verification stage")
    require(record.get("status") in {"pass", "fail", "timeout", "incomplete", "analysis_only", "historical"}, "Invalid run status")
    require(record.get("numerical_status") in {"pass", "fail", "unverified", "not_applicable"}, "Invalid numerical_status")
    require(isinstance(record.get("summary"), str) and record["summary"].strip(), "Experiment summary is required")
    require(isinstance(record.get("blocks"), list) and all(b in registry(root)["blocks"] for b in record["blocks"]), "Unknown block in experiment")
    require(isinstance(record.get("source"), dict) and isinstance(record.get("config"), dict), "Source and config objects are required")
    source = record["source"]
    for key in ["snapshot_sha256"]:
        require(source.get(key) is None or HEX_RE.fullmatch(str(source[key])), "Invalid source digest")
    require(source.get("dirty") is None or isinstance(source["dirty"], bool), "source.dirty must be boolean or null")
    for key in ["input_sha256", "build_config_sha256"]:
        val = record["config"].get(key)
        require(val is None or HEX_RE.fullmatch(str(val)), "Invalid config digest: " + key)
    period = record["config"].get("clock_period_ns")
    require(period is None or (isinstance(period, (int, float)) and not isinstance(period, bool) and math.isfinite(period) and period > 0), "clock_period_ns must be positive or null")
    evidence = record.get("evidence")
    require(isinstance(evidence, list), "evidence must be a list")
    evidence_ids = [valid_id(e.get("id")) for e in evidence]
    require(len(evidence_ids) == len(set(evidence_ids)), "Duplicate evidence ID")
    metrics = record.get("metrics")
    require(isinstance(metrics, dict), "metrics must be an object")
    for name, metric in metrics.items():
        valid_id(name)
        require(isinstance(metric, dict), "Metric must include value/unit/scope/kind/evidence_ids: " + name)
        value = metric.get("value")
        require(value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)), "Metric must be finite numeric or null: " + name)
        require(metric.get("kind") in {"measured", "simulated", "estimated", "reported"}, "Invalid metric kind: " + name)
        require(isinstance(metric.get("unit"), str) and metric["unit"] and isinstance(metric.get("scope"), str) and metric["scope"], "Metric units and scope are required: " + name)
        refs = metric.get("evidence_ids", [])
        require(isinstance(refs, list) and set(refs) <= set(evidence_ids), "Unknown metric evidence: " + name)
        require(value is None or refs, "Every non-null metric needs evidence: " + name)
        if name in {"latency_cycles", "ii", "lut", "ff", "dsp", "bram18", "bram36", "uram", "latency_ns", "kernel_time_ns"}:
            require(value is None or value >= 0, "Negative hardware count/time")
        if record["stage"] == "csynth":
            require(metric["kind"] in {"estimated", "reported"}, "C-synthesis results are estimates/reports, not observed runtime")
        if name in {"wns_ns", "tns_ns"}:
            require(record["stage"] in {"implementation", "board"}, "WNS/TNS require implementation evidence")
    if record.get("supersedes"):
        old = valid_id(record["supersedes"])
        require(safe(root, ".agent/memory/experiments/" + old + "/record.json").is_file(), "Unknown superseded experiment")


def capture_evidence(root, record, allow_external=False):
    """Capture explicitly selected small reports; never sweep an artifact directory."""
    changes, evidence, total = {}, [], 0
    for supplied in record["evidence"]:
        entry = dict(supplied)
        eid = valid_id(entry["id"])
        require(isinstance(entry.get("locator"), str) and entry["locator"].strip(), "Evidence needs a report/line/signal locator")
        retention = entry.get("retention", "copy")
        require(retention in {"copy", "external"}, "Evidence retention must be copy or external")
        if "path" in entry:
            raw = entry["path"]
            require(isinstance(raw, str), "Evidence path must be a string")
            path = Path(raw)
            if not path.is_absolute():
                path = root / path
            if not allow_external:
                try:
                    rel = path.relative_to(root).as_posix()
                except ValueError as exc:
                    raise EnvError("External evidence needs --allow-external-evidence and an explicitly authorized exact path") from exc
                path = safe(root, rel)
            else:
                path = path.resolve()  # Explicitly requested single artifact only.
            require(path.is_file(), "Evidence is not a readable regular file: " + str(path))
            size = path.stat().st_size
            if retention == "copy":
                require(size <= 5 * 1024 * 1024, "Evidence exceeds 5 MiB; use retained external artifact + digest, or a scoped exported report")
                total += size
                require(total <= 25 * 1024 * 1024, "Evidence bundle exceeds 25 MiB; keep large raw artifacts externally")
                data = path.read_bytes()
                sha = digest(data)
                name = re.sub(r"[^A-Za-z0-9_.-]", "_", path.name)
                saved = ".agent/memory/experiments/{}/evidence/{}-{}".format(record["id"], eid, name)
                changes[saved] = data
                entry["stored_path"] = saved
            else:
                require(entry.get("retention_note"), "External evidence needs a retention/availability note")
                sha = file_digest(path)
                entry["artifact_uri"] = path.as_uri() if path.is_absolute() else str(path)
            require(entry.get("sha256") in {None, sha}, "Evidence changed or hash is incorrect: " + eid)
            entry["sha256"] = sha
            entry["bytes"] = size
        else:
            require(retention == "external" and entry.get("artifact_uri") and entry.get("retention_note"), "URI-only evidence needs external retention, URI and retention note")
            require(HEX_RE.fullmatch(str(entry.get("sha256", ""))), "External URI evidence needs a supplied SHA-256")
            entry["availability"] = "not fetched by agentctl; caller-provided provenance"
        entry["retention"] = retention
        evidence.append(entry)
    return changes, evidence


def cmd_experiment_record(args, root):
    record = load(args.file)
    validate_experiment(record, root)
    folder = ".agent/memory/experiments/" + record["id"]
    require(not safe(root, folder).exists(), "Experiment ID already exists. Use a new ID and supersedes; records are immutable.")
    changes, evidence = capture_evidence(root, record, args.allow_external_evidence)
    record["evidence"] = evidence
    record["recorded_at"] = now()
    record["provenance_complete"] = bool((record["source"].get("revision") or record["source"].get("snapshot_sha256")) and all(record["config"].get(k) is not None for k in ["tool", "tool_version", "device", "precision", "clock_period_ns", "workload", "input_sha256", "shape", "build_config_sha256"]))
    raw = dump(record)
    changes[folder + "/record.json"] = raw
    changes[folder + "/record.sha256"] = (digest(raw) + "\n").encode()
    changes[folder + "/REPORT.md"] = ("# " + record["id"] + "\n\n" + record["summary"] + "\n\nCanonical values, scope and evidence hashes: [record.json](record.json).\n\nStatus: " + record["status"] + "; numerical status: " + record["numerical_status"] + ".\nThis generated summary contains no independent metric table. Corrections require a new record ID.\n").encode()
    transaction(root, changes, "freeze experiment " + record["id"])
    if not record["provenance_complete"]:
        print("Recorded with incomplete provenance. Matched-condition comparisons will reject unknown mandatory fields.")


def get_experiment(root, eid):
    valid_id(eid)
    path = safe(root, ".agent/memory/experiments/" + eid + "/record.json")
    record = load(path)
    expected = safe(root, ".agent/memory/experiments/" + eid + "/record.sha256").read_text().strip()
    require(file_digest(path) == expected, "Experiment record integrity failure: " + eid)
    return record


def compare_records(a, b):
    reasons = []
    if a["stage"] != b["stage"]:
        reasons.append("stage differs")
    for key in ["tool", "tool_version", "device", "precision", "clock_period_ns", "workload", "input_sha256", "shape"]:
        x, y = a["config"].get(key), b["config"].get(key)
        if x is None or y is None:
            reasons.append(key + " unknown")
        elif x != y:
            reasons.append(key + " differs")
    for key in ["board", "parameters", "seed"]:
        if a["config"].get(key) != b["config"].get(key):
            reasons.append(key + " differs")
    # A build hash may differ with the variant; a human must identify intentional
    # settings changes instead of silently calling them controlled conditions.
    for key in ["build_config_sha256"]:
        x, y = a["config"].get(key), b["config"].get(key)
        if not x or not y:
            reasons.append(key + " unknown")
        elif x != y:
            reasons.append(key + " differs (inspect non-design configuration before a causal claim)")
    for item, label in [(a, "before"), (b, "after")]:
        source = item["source"]
        if not source.get("revision") and not source.get("snapshot_sha256"):
            reasons.append(label + " source identity unknown")
        if source.get("dirty") is not False and not source.get("snapshot_sha256"):
            reasons.append(label + " dirty/unknown working tree lacks content digest")
        if item["status"] != "pass":
            reasons.append(label + " run not passing")
        if item["numerical_status"] != "pass":
            reasons.append(label + " numerical equivalence unverified/failed")
    metrics = {}
    for name in sorted(set(a["metrics"]) & set(b["metrics"])):
        x, y = a["metrics"][name], b["metrics"][name]
        compatible = all(x.get(k) == y.get(k) for k in ["unit", "scope", "kind", "clock_domain"])
        numeric = x.get("value") is not None and y.get("value") is not None
        metrics[name] = {"before": x.get("value"), "after": y.get("value"), "unit": x.get("unit"), "metric_scope_matched": compatible,
                         "before_over_after": x["value"] / y["value"] if compatible and numeric and y["value"] != 0 else None}
    return {"matched_conditions": not reasons, "reasons": reasons, "metrics": metrics,
            "interpretation": "Matched recorded conditions; ratios still do not prove architectural causality." if not reasons else "Unpaired artifact comparison only. Do not call ratios architecture speedup."}


def cmd_experiment_compare(args, root):
    output_json(root, compare_records(get_experiment(root, args.before), get_experiment(root, args.after)))


def cmd_experiment_list(args, root):
    base = safe(root, ".agent/memory/experiments")
    records = []
    if base.exists():
        for p in sorted(base.glob("*/record.json")):
            rec = get_experiment(root, p.parent.name)
            if args.block is None or args.block in rec["blocks"]:
                records.append({k: rec[k] for k in ["id", "blocks", "stage", "status", "numerical_status"]})
    output_json(root, records)


def cmd_finding_publish(args, root):
    finding = load(args.file)
    require(finding.get("schema_version") == 1, "Unsupported finding schema")
    fid = valid_id(finding.get("id"))
    require(finding.get("confidence") in {"observation", "inference", "hypothesis"}, "Finding confidence must be observation/inference/hypothesis")
    require(finding.get("title") and finding.get("summary"), "Finding title and summary required")
    blocks = finding.get("affected_blocks")
    require(isinstance(blocks, list) and blocks and len(blocks) == len(set(blocks)), "Unique affected_blocks required")
    require(set(blocks) <= set(registry(root)["blocks"]), "Unknown affected block")
    exps = finding.get("experiment_ids")
    require(isinstance(exps, list) and exps, "Link at least one recorded evidence experiment")
    for eid in exps:
        get_experiment(root, eid)
    require(isinstance(finding.get("evidence_locators"), list) and finding["evidence_locators"], "Finding needs specific evidence locators")
    require(isinstance(finding.get("next_design_checks"), list) and finding["next_design_checks"], "Finding needs next-design checks")
    if finding.get("supersedes"):
        old = valid_id(finding["supersedes"])
        require(safe(root, ".agent/memory/findings/" + old + ".json").is_file(), "Unknown superseded finding")
    rel = ".agent/memory/findings/" + fid + ".json"
    require(read_bytes(root, rel) is None, "Finding exists; publish a new superseding ID")
    finding["created_at"] = now()
    raw = dump(finding)
    changes = {rel: raw, rel + ".sha256": (digest(raw) + "\n").encode()}
    for block in blocks:
        inbox = ".agent/memory/blocks/" + block + "/inbox/" + fid + ".json"
        changes[inbox] = dump({"finding_id": fid, "finding_path": rel, "finding_sha256": digest(raw), "state": "pending", "delivered_at": now()})
    transaction(root, changes, "publish finding " + fid)
    print("Reference inboxes delivered to {}. Coordinator must invoke owners; no background notification was sent.".format(", ".join(blocks)))


def get_finding(root, fid):
    valid_id(fid)
    rel = ".agent/memory/findings/" + fid + ".json"
    data = read_bytes(root, rel)
    require(data is not None, "Finding not found")
    expected = safe(root, rel + ".sha256").read_text().strip()
    require(digest(data) == expected, "Finding integrity failure")
    return json.loads(data)


def feedback_section(root, block, changed_inbox):
    folder = safe(root, ".agent/memory/blocks/" + block + "/inbox")
    items = {p.name: load(p) for p in folder.glob("*.json")} if folder.exists() else {}
    items[changed_inbox["finding_id"] + ".json"] = changed_inbox
    lines = []
    for _, item in sorted(items.items()):
        if item["state"] in {"accept", "reject", "defer"}:
            f = get_finding(root, item["finding_id"])
            lines.append("- [{}; {}] [{}](../../findings/{}.json). Owner reason: {}. Acceptance is not validation.".format(item["state"], f["confidence"], f["title"], f["id"], " ".join(item["note"].split())))
    return "\n".join(lines) if lines else "No owner-reviewed findings yet."


def cmd_finding_ack(args, root):
    finding = get_finding(root, args.id)
    require(args.block in finding["affected_blocks"], "This block is not a finding recipient")
    require(args.note.strip(), "Owner rationale is required")
    inbox_rel = ".agent/memory/blocks/" + args.block + "/inbox/" + args.id + ".json"
    inbox = load(safe(root, inbox_rel))
    receipt = {"finding_id": args.id, "block": args.block, "decision": args.decision, "note": args.note, "decided_at": now(), "previous_state": inbox["state"]}
    rid = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    receipt_rel = ".agent/memory/blocks/{}/receipts/{}/{}.json".format(args.block, args.id, rid)
    inbox.update({"state": args.decision, "note": args.note, "receipt_path": receipt_rel, "decided_at": receipt["decided_at"]})
    memory_rel = ".agent/memory/blocks/" + args.block + "/MEMORY.md"
    text = safe(root, memory_rel).read_text()
    require(text.count("<!-- feedback:start -->") == 1 and text.count("<!-- feedback:end -->") == 1, "Block feedback markers were edited; restore/reconcile before acknowledging")
    content = "<!-- feedback:start -->\n" + feedback_section(root, args.block, inbox) + "\n<!-- feedback:end -->"
    text = re.sub(r"<!-- feedback:start -->.*?<!-- feedback:end -->", lambda _: content, text, flags=re.S)
    transaction(root, {inbox_rel: dump(inbox), receipt_rel: dump(receipt), memory_rel: text.encode()}, "owner feedback " + args.block + "/" + args.id)


def cmd_memory_search(args, root):
    query = args.query.casefold()
    base = safe(root, ".agent/memory")
    results = []
    if base.exists():
        for p in walk(base):
            if p.suffix not in {".md", ".json"} or p.stat().st_size > 2 * 1024 * 1024:
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if query in line.casefold():
                    results.append({"path": p.relative_to(root).as_posix(), "line": n, "text": line[:350]})
                    if len(results) >= args.limit:
                        output_json(root, {"results": results, "limit_reached": True})
                        return
    output_json(root, {"results": results, "limit_reached": False})


def parse_agent(data, path):
    try:
        import tomllib
    except ImportError:
        values = {}
        for key in ["name", "description", "developer_instructions"]:
            require(re.search(r"^" + key + r"\s*=", data, re.M), "Missing role field {} in {}".format(key, path))
        m = re.search(r'^name\s*=\s*"([^"]+)"', data, re.M)
        require(m, "Cannot parse role name: " + path)
        return {"name": m.group(1), "syntax_check": "limited; Python 3.11+ enables full TOML validation"}
    try:
        values = tomllib.loads(data)
    except ValueError as exc:
        raise EnvError("Invalid agent TOML {}: {}".format(path, exc)) from exc
    for key in ["name", "description", "developer_instructions"]:
        require(isinstance(values.get(key), str) and values[key], "Missing role field: " + key)
    return values


def cmd_doctor(args, root):
    issues, warnings = [], []
    lockpath = safe(root, ".agent/environment.lock.json")
    if not lockpath.is_file():
        if safe(root, ".agent/staging/codex-env/VERSION").is_file():
            output_json(root, {"status": "migration_pending", "message": "Transfer tooling staged; invoke $jagent-transfer. Legacy system remains active."})
            return
        raise EnvError("No installed environment")
    lock = load(lockpath)
    for rel, sha in lock["managed"].items():
        data = read_bytes(root, rel)
        if data is None:
            issues.append("Missing installed file: " + rel)
        elif digest(data) != sha:
            warnings.append("Managed file edited; update will preserve/refuse overwrite: " + rel)
    names = {}
    for p in sorted(safe(root, ".codex/agents").glob("*.toml")):
        try:
            rel = p.relative_to(root).as_posix()
            a = parse_agent(safe(root, rel).read_text(), rel)
            require(a["name"] not in names, "Duplicate native agent name: " + a["name"])
            names[a["name"]] = rel
            if "syntax_check" in a:
                warnings.append(a["syntax_check"])
        except EnvError as exc:
            issues.append(str(exc))
    for name in ["jagent-grill", "grilling", "domain-modeling", "jagent-block-scan", "jagent-transfer", "jagent-experiment", "jagent-bottleneck", "jagent-memory-sync", "jagent-block-add", "jagent-env-promote"]:
        if not safe(root, ".agents/skills/" + name + "/SKILL.md").is_file():
            issues.append("Missing skill: " + name)
    for needed in [".agent/rules/code-style/INDEX.md", ".agent/rules/code-pitfall/INDEX.md", ".agent/rules/code-pitfall/hls-signed-index.md"]:
        if not safe(root, needed).is_file():
            issues.append("Missing rule index/pitfall: " + needed)
    reg = registry(root)
    owners = []
    for bid, b in reg["blocks"].items():
        try:
            require(b["agent"] in names, "Missing block role: " + bid)
            require(safe(root, ".agent/memory/blocks/" + bid + "/MEMORY.md").is_file(), "Missing block memory: " + bid)
            current = fingerprints(root, b["owned_paths"])
            if current != b.get("source_hashes"):
                warnings.append("Source changed since owner review: " + bid)
            for path in b["owned_paths"]:
                for old, who in owners:
                    require(not overlaps(path, old), "Ownership overlap: " + bid + " / " + who)
                owners.append((path, bid))
        except EnvError as exc:
            issues.append(str(exc))
        for p in safe(root, ".agent/memory/blocks/" + bid + "/inbox").glob("*.json"):
            inbox = load(p)
            if inbox["state"] in {"pending", "defer"}:
                warnings.append("Pending/deferred finding: " + bid + "/" + inbox["finding_id"])
    for p in safe(root, ".agent/memory/experiments").glob("*/record.json"):
        try:
            rec = get_experiment(root, p.parent.name)
            for e in rec["evidence"]:
                if e.get("stored_path"):
                    report = safe(root, e["stored_path"])
                    require(report.is_file() and file_digest(report) == e["sha256"], "Evidence missing/changed: " + e["id"])
                else:
                    warnings.append("External artifact availability not checked: " + rec["id"] + "/" + e["id"])
        except EnvError as exc:
            issues.append(str(exc))
    for p in safe(root, ".agent/memory/findings").glob("*.json"):
        try:
            get_finding(root, p.stem)
        except EnvError as exc:
            issues.append(str(exc))
    binding = safe(root, ".agent/upstream.local.json")
    if not binding.is_file():
        warnings.append("No external environment source binding; run upstream set before promoting rules")
    else:
        source_path = Path(load(binding).get("path", ""))
        if not source_path.is_dir():
            warnings.append("External environment path unavailable; rebind with upstream set")
    # Report active overrides without pretending to inspect global plugin state.
    for p in walk(root):
        rel = p.relative_to(root).as_posix()
        if p.name in {"AGENTS.override.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md"} and rel != "AGENTS.md" and not rel.startswith((".agents/", ".codex/")) and "/archive/" not in rel:
            warnings.append("Additional active/scoped instructions need review: " + rel)
    output_json(root, {"status": "error" if issues else "ok", "environment_version": lock["version"], "roles": sorted(names), "blocks": sorted(reg["blocks"]), "issues": issues, "warnings": sorted(set(warnings)), "scope": "repository-local file/schema/evidence checks only; not Codex runtime, user-global plugin state or hardware validation"})
    if issues:
        raise EnvError("doctor found integrity/schema errors")


def resolve_upstream(root, explicit=None):
    candidate = explicit or os.environ.get("CODEX_ENV_HOME")
    if not candidate:
        path = safe(root, ".agent/upstream.local.json")
        require(path.is_file(), "Bind the external environment with upstream set --path /path/to/env or CODEX_ENV_HOME")
        candidate = load(path).get("path")
    require(isinstance(candidate, str) and candidate, "Missing upstream path")
    source = Path(candidate).expanduser().resolve()
    require(source.is_dir() and source != root and root not in source.parents and source not in root.parents,
            "The environment must be a separate external checkout, not this project or its ancestor/descendant")
    require((source / "ENVIRONMENT_ID").is_file() and (source / "ENVIRONMENT_ID").read_text().strip() == ENVIRONMENT_ID,
            "Not a compatible environment SOURCE checkout: " + str(source))
    for rel in ["VERSION", "install.sh", "templates/AGENTS.md", "tools/agentctl.py"]:
        require(safe(source, rel).is_file(), "Incomplete source checkout: " + rel)
    return source


def cmd_upstream_set(args, root):
    source = resolve_upstream(root, args.path)
    transaction(root, {".agent/upstream.local.json": dump({"schema_version": 1, "environment_id": ENVIRONMENT_ID, "path": str(source)})}, "bind external environment source")
    print("Source bound locally: " + str(source))


def cmd_upstream_show(args, root):
    source = resolve_upstream(root)
    output_json(root, {"path": str(source), "version": (source / "VERSION").read_text().strip(),
                       "environment_id": ENVIRONMENT_ID, "writes_require_approval": True,
                       "note": "This is the external source; .agent/rules and .codex/agents are installed project snapshots."})


def validate_promotion(draft, root, source):
    require(draft.get("schema_version") == 1 and draft.get("kind") in {"style", "pitfall", "agent", "policy"}, "Unsupported promotion kind/schema")
    for key in ["title", "rationale", "applicability"]:
        require(isinstance(draft.get(key), str) and draft[key].strip(), "Promotion needs " + key)
    evidence = draft.get("evidence", [])
    require(isinstance(evidence, list) and evidence, "Reference real local evidence before generalizing")
    evidence_hashes = {}
    for entry in evidence:
        rel = entry["path"]
        require(safe(root, rel).is_file(), "Missing local promotion evidence: " + rel)
        evidence_hashes[rel] = file_digest(safe(root, rel))
    edits = draft.get("edits", [])
    require(isinstance(edits, list) and edits, "No generalized edits proposed")
    require(len({x["path"] for x in edits}) == len(edits), "Duplicate promotion target")
    forbidden = draft.get("project_identifiers", [])
    require(isinstance(forbidden, list) and all(isinstance(x, str) and len(x) >= 3 for x in forbidden), "project_identifiers must contain nonempty specific identifiers")
    if root.name.casefold() not in {"project", "repo", "workspace", "test-project"}:
        forbidden = forbidden + [root.name]
    output = []
    allowed = {"style": "general/code-style/", "pitfall": "general/code-pitfall/", "agent": "agents/", "policy": "policies/"}
    for edit in edits:
        rel, content = edit["path"], edit.get("content")
        safe(source, rel)
        require(rel.startswith(allowed[draft["kind"]]), "Target does not match promotion kind: " + rel)
        require(isinstance(content, str) and content.strip() and len(content) <= 200000, "Empty/oversized generalized content")
        if draft["kind"] == "agent":
            require(PurePosixPath(rel).parent.as_posix() == "agents" and rel.endswith(".toml"), "General agents must be standalone agents/<name>.toml")
            role = parse_agent(content, rel)
            valid_id(role["name"])
            require(role["name"] == Path(rel).stem and not role["name"].startswith("block-"), "Promote a general role, not a project block-owner identity")
            require("code-style" in content and "code-pitfall" in content, "General design/review roles must route to style and pitfall rules")
            for existing in (source / "agents").glob("*.toml"):
                if existing.name != Path(rel).name:
                    require(parse_agent(existing.read_text(), existing.name)["name"] != role["name"], "Duplicate upstream role name")
        else:
            require(rel.endswith(".md"), "Portable rules must be Markdown")
        for identifier in forbidden:
            require(identifier.casefold() not in content.casefold(), "Project-specific identifier remains in candidate: " + identifier)
        require(not re.search(r"(?i)(?:/(?:home|users|scratch(?:\.[\w-]+)?|mnt|tmp)/|[a-z]:\\\\users\\\\)", content), "Machine-specific absolute path remains in candidate")
        require(not re.search(r"(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY-----)", content), "Possible credential in candidate")
        before = read_bytes(source, rel)
        output.append({"path": rel, "content": content, "before_sha256": digest(before) if before is not None else None,
                       "after_sha256": digest(content.encode())})
    return output, evidence_hashes


def cmd_promote_plan(args, root):
    source = resolve_upstream(root)
    draft = load(args.file)
    edits, evidence = validate_promotion(draft, root, source)
    plan = {"schema_version": 1, "created_at": now(), "approved": False, "approval_note": "",
            "source_path": str(source), "environment_id": ENVIRONMENT_ID, "draft": draft,
            "evidence_sha256": evidence, "edits": edits,
            "notice": "Review semantic generality and the diff. Only listed external files will change. No backups, commits, push or automatic project updates."}
    output_json(root, plan, args.out)


@contextlib.contextmanager
def source_locked(source):
    folder = safe(source, ".env-write.lock")
    try:
        folder.mkdir()
    except FileExistsError as exc:
        raise EnvError("Another promotion holds the source lock. Inspect it before removing a stale lock.") from exc
    try:
        atomic(folder / "owner.json", dump({"pid": os.getpid(), "host": socket.gethostname(), "time": now()}))
        yield
    finally:
        (folder / "owner.json").unlink(missing_ok=True)
        folder.rmdir()


def cmd_promote_apply(args, root):
    plan = load(args.plan)
    require(plan.get("schema_version") == 1 and plan.get("environment_id") == ENVIRONMENT_ID, "Invalid promotion plan")
    source = resolve_upstream(root)
    require(str(source) == plan.get("source_path"), "External source binding changed; regenerate the promotion plan")
    require(plan.get("draft", {}).get("reviewed_generalization") is True, "The curator must review portability/generalization first")
    if not args.dry_run:
        require(args.approve and plan.get("approved") is True and str(plan.get("approval_note", "")).strip(), "Explicit approval of the external diff is required")
    with source_locked(source):
        edits, evidence = validate_promotion(plan["draft"], root, source)
        require(evidence == plan.get("evidence_sha256"), "Local supporting evidence changed; review again")
        require(edits == plan.get("edits"), "Upstream files or proposal changed; reconcile and regenerate the plan")
        changes = {x["path"]: x["content"].encode() for x in edits}
        transaction(source, changes, "approved generalized promotion from a separate project", dry_run=args.dry_run)
    if not args.dry_run:
        receipt_id = "promotion-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + digest(dump(plan))[:8]
        rel = ".agent/memory/agents/env-curator/promotions/" + receipt_id + ".json"
        require(read_bytes(root, rel) is None, "Promotion already has a receipt")
        receipt = {"schema_version": 1, "created_at": now(), "title": plan["draft"]["title"], "kind": plan["draft"]["kind"],
                   "environment_id": ENVIRONMENT_ID, "paths": [{k: e[k] for k in ["path", "before_sha256", "after_sha256"]} for e in edits],
                   "evidence_sha256": evidence, "scope": plan["draft"]["applicability"], "approval_note": plan["approval_note"],
                   "git_commit": "not performed", "git_push": "not performed", "installed_projects": "not updated"}
        transaction(root, {rel: dump(receipt)}, "record promotion outcome (metadata only)")
        print("Updated only the approved external source files. Review git diff there. No commit/push was performed. Use install.sh --update to distribute the change.")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Project root (default: current directory)")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    def leaf(parent, name, function, helptext):
        p = parent.add_parser(name, help=helptext)
        p.add_argument("--repo", default=argparse.SUPPRESS, help="Project root")
        p.set_defaults(func=function)
        return p

    p = leaf(sub, "install", cmd_install, "Install a managed snapshot or stage reviewed no-backup transfer")
    p.add_argument("--update", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p = leaf(sub, "doctor", cmd_doctor, "Check installed roles, memory ownership and evidence integrity")

    p = sub.add_parser("migration", help="Plan and apply user-approved migration")
    m = p.add_subparsers(dest="operation", required=True)
    p = leaf(m, "plan", cmd_migration_plan, "Plan a clean replacement; no backups")
    p.add_argument("--out", help="Relative output path; default stdout")
    p = leaf(m, "apply", cmd_migration_apply, "Apply a completed, approved transfer plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--confirm-no-backup", action="store_true")

    p = sub.add_parser("block", help="Discover and register hardware block owners")
    b = p.add_subparsers(dest="operation", required=True)
    p = leaf(b, "scan", cmd_block_scan, "Suggest lexical candidates; no automatic boundary approval")
    p.add_argument("--out")
    p = leaf(b, "add", cmd_block_add, "Draft one explicit block without scanning the repository")
    p.add_argument("id")
    p.add_argument("--description", required=True)
    p.add_argument("--path", action="append", required=True)
    p.add_argument("--shared-path", action="append", default=[])
    p.add_argument("--profile", action="append", default=[])
    p.add_argument("--depends-on", action="append", default=[])
    p.add_argument("--interface", action="append", default=[])
    p.add_argument("--out")
    p = leaf(b, "apply", cmd_block_apply, "Create agents/memory from user-confirmed block plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--approve", action="store_true")
    p = leaf(b, "refresh", cmd_block_refresh, "Record an owner's completed source review")
    p.add_argument("--block", required=True)
    p.add_argument("--note", required=True)

    p = sub.add_parser("experiment", help="Preserve quantitative results and compare scopes")
    e = p.add_subparsers(dest="operation", required=True)
    p = leaf(e, "draft", cmd_experiment_draft, "Create an unmeasured provenance/metrics draft")
    p.add_argument("id")
    p.add_argument("--block", action="append", default=[])
    p.add_argument("--stage", choices=sorted(STAGES), required=True)
    p.add_argument("--variant", default=None)
    p.add_argument("--out")
    p = leaf(e, "record", cmd_experiment_record, "Freeze an immutable result and copy scoped evidence")
    p.add_argument("--file", required=True)
    p.add_argument("--allow-external-evidence", action="store_true", help="Explicitly authorize reading exact external/symlink artifact files specified in this record")
    p = leaf(e, "compare", cmd_experiment_compare, "Compare two records with strict condition checks")
    p.add_argument("before")
    p.add_argument("after")
    p = leaf(e, "list", cmd_experiment_list, "List recorded runs")
    p.add_argument("--block")

    p = sub.add_parser("finding", help="Deliver analysis to block owners and record their responses")
    f = p.add_subparsers(dest="operation", required=True)
    p = leaf(f, "publish", cmd_finding_publish, "Publish immutable evidence-backed finding and inbox links")
    p.add_argument("--file", required=True)
    p = leaf(f, "ack", cmd_finding_ack, "Accept/reject/defer feedback as the assigned block owner")
    p.add_argument("id")
    p.add_argument("--block", required=True)
    p.add_argument("--decision", choices=["accept", "reject", "defer"], required=True)
    p.add_argument("--note", required=True)

    p = sub.add_parser("memory", help="Targeted durable memory lookup")
    m = p.add_subparsers(dest="operation", required=True)
    p = leaf(m, "search", cmd_memory_search, "Search bounded Markdown/JSON memory")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=30)
    p = sub.add_parser("upstream", help="Bind the external reusable environment source, independent of its name")
    u = p.add_subparsers(dest="operation", required=True)
    p = leaf(u, "show", cmd_upstream_show, "Resolve the external source checkout")
    p = leaf(u, "set", cmd_upstream_set, "Store a machine-local source path; never publish it")
    p.add_argument("--path", required=True)

    p = sub.add_parser("promote", help="Review and promote generalized local lessons to the external environment")
    u = p.add_subparsers(dest="operation", required=True)
    p = leaf(u, "plan", cmd_promote_plan, "Hash a curated proposal against the bound upstream files")
    p.add_argument("--file", required=True, help="Reviewed draft JSON, not raw project files")
    p.add_argument("--out")
    p = leaf(u, "apply", cmd_promote_apply, "Apply only approved generalized edits to the external source")
    p.add_argument("--plan", required=True)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        root = Path(args.repo).expanduser().resolve()
        require(root.is_dir(), "Project directory does not exist: " + str(root))
        mutating = args.func in {cmd_install, cmd_migration_apply, cmd_upstream_set, cmd_promote_apply, cmd_block_apply, cmd_block_refresh, cmd_experiment_draft, cmd_experiment_record, cmd_finding_publish, cmd_finding_ack}
        if mutating and not getattr(args, "dry_run", False):
            with locked(root):
                args.func(args, root)
        else:
            args.func(args, root)
        return 0
    except (EnvError, OSError, KeyError, TypeError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
