#!/usr/bin/env python3
"""Create and verify a local artifact manifest; never performs network probes.

The analyst supplies the experiment status. A matching hash does not authenticate
the capture source, establish a chain of custody, or validate an interpretation.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

FORMAT = "northguard.reverse-observer.artifacts.v1"
STATUSES = ("unverified", "observed", "falsified_under_tested_conditions", "structurally_invalid")


def safe_artifact(base: Path, name: str) -> Path:
    rel = Path(name)
    if not name or rel.is_absolute() or ".." in rel.parts or rel == Path("."):
        raise ValueError(f"Artifact path must be relative and remain inside the working directory: {name!r}")
    full = base / rel
    if full.is_symlink() or not full.is_file():
        raise ValueError(f"Artifact must be an existing regular, non-symlink file: {name!r}")
    # Also reject a symlinked parent directory, even when the file itself is regular.
    if not full.resolve().is_relative_to(base.resolve()):
        raise ValueError(f"Artifact escapes the working directory: {name!r}")
    return full


def digest(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
            count += len(chunk)
    return h.hexdigest(), count


def build_manifest(experiment_id: str, artifacts: list[str], base: Path, status: str = "unverified") -> dict:
    if not experiment_id.strip() or not artifacts:
        raise ValueError("A non-empty experiment ID and at least one artifact are required")
    if status not in STATUSES:
        raise ValueError(f"Unsupported analyst status: {status}")
    if len(artifacts) != len(set(artifacts)):
        raise ValueError("Duplicate artifact paths are not permitted")

    entries = []
    for name in sorted(artifacts):
        path = safe_artifact(base, name)
        checksum, size = digest(path)
        entries.append({"path": Path(name).as_posix(), "sha256": checksum, "bytes": size})

    return {
        "format": FORMAT,
        "experiment_id": experiment_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analyst_status": status,
        "status_basis": "analyst_supplied_not_automatically_validated",
        "artifacts": entries,
    }


def verify_manifest(manifest: dict, base: Path) -> int:
    if manifest.get("format") != FORMAT:
        raise ValueError("Unknown artifact manifest format")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Manifest must contain artifacts")
    seen = set()
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("Malformed artifact entry")
        name = item["path"]
        if name in seen:
            raise ValueError("Duplicate artifact in manifest")
        seen.add(name)
        actual_hash, actual_bytes = digest(safe_artifact(base, name))
        if actual_hash != item.get("sha256") or actual_bytes != item.get("bytes"):
            raise ValueError(f"Evidence mismatch: {name}")
    return len(artifacts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline artifact integrity records for authorized lab measurements")
    parser.add_argument("--experiment", help="Analyst-defined experiment identifier")
    parser.add_argument("--artifact", action="append", default=[], help="Artifact path relative to current directory (repeatable)")
    parser.add_argument("--status", choices=STATUSES, default="unverified", help="Analyst-supplied hypothesis status")
    parser.add_argument("--out", type=Path, help="New manifest path; never overwritten")
    parser.add_argument("--verify", type=Path, help="Verify an existing manifest against its local artifacts")
    args = parser.parse_args()
    try:
        if args.verify:
            if args.experiment or args.artifact or args.out:
                parser.error("--verify must be used alone")
            manifest = json.loads(args.verify.read_text(encoding="utf-8"))
            count = verify_manifest(manifest, Path.cwd())
            print(f"ARTIFACT_HASHES_MATCH: {count} file(s); interpretation not verified")
        else:
            if not args.experiment or not args.out:
                parser.error("creation requires --experiment, --artifact, and --out")
            result = build_manifest(args.experiment, args.artifact, Path.cwd(), args.status)
            with args.out.open("x", encoding="utf-8") as output:
                json.dump(result, output, indent=2)
                output.write("\n")
            print(f"ARTIFACT_MANIFEST_CREATED: {args.out}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ARTIFACT_MANIFEST_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
