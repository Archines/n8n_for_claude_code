"""Local version management for workflow files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _versions_dir(wf_name: str, base_dir: str = "workflows") -> Path:
    """Return the version storage directory for a workflow."""
    return Path(base_dir) / ".versions" / wf_name


def save_version(
    wf_name: str,
    wf_data: dict,
    operation: str,
    source_id: str = "",
    base_dir: str = "workflows",
) -> int:
    """Save a new version of a workflow. Returns the version number.

    Args:
        wf_name: Workflow name (stem of the filename, e.g. "my-workflow")
        wf_data: Workflow JSON data
        operation: One of "pull", "push", "deploy", "rollback", "edit", "pre-rollback"
        source_id: Optional workflow ID on the remote instance
        base_dir: Base directory for workflows
    """
    vdir = _versions_dir(wf_name, base_dir)
    vdir.mkdir(parents=True, exist_ok=True)

    meta_path = vdir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {"versions": []}

    # Determine next version number
    if meta["versions"]:
        next_num = meta["versions"][-1]["number"] + 1
    else:
        next_num = 1

    # Save version file
    version_file = vdir / f"v{next_num:03d}.json"
    version_file.write_text(
        json.dumps(wf_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Update metadata
    meta["versions"].append({
        "number": next_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "source_id": source_id,
    })
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return next_num


def list_versions(wf_name: str, base_dir: str = "workflows") -> list[dict]:
    """Return version metadata list for a workflow."""
    meta_path = _versions_dir(wf_name, base_dir) / "meta.json"
    if not meta_path.exists():
        return []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("versions", [])


def get_version(wf_name: str, version_number: int, base_dir: str = "workflows") -> dict:
    """Return the workflow JSON for a specific version."""
    vdir = _versions_dir(wf_name, base_dir)
    version_file = vdir / f"v{version_number:03d}.json"
    if not version_file.exists():
        raise FileNotFoundError(f"Version {version_number} not found for '{wf_name}'")
    return json.loads(version_file.read_text(encoding="utf-8"))


def get_latest_version(wf_name: str, base_dir: str = "workflows") -> tuple[int, dict] | None:
    """Return the latest version (number, data) or None if no versions exist."""
    versions = list_versions(wf_name, base_dir)
    if not versions:
        return None
    latest = versions[-1]
    data = get_version(wf_name, latest["number"], base_dir)
    return latest["number"], data


def rollback_workflow(
    client,
    wf_name: str,
    workflow_id: str,
    version_number: int | None = None,
    base_dir: str = "workflows",
) -> dict:
    """Rollback a workflow to a specific version.

    1. Save current state as "pre-rollback" version
    2. Load the target version
    3. Restore the local file
    4. Push to remote

    Args:
        client: N8nClient instance
        wf_name: Workflow name (filename stem)
        workflow_id: Remote workflow ID
        version_number: Target version (None = previous version)
        base_dir: Base directory

    Returns:
        Dict with rollback details
    """
    versions = list_versions(wf_name, base_dir)
    if not versions:
        raise ValueError(f"No versions found for '{wf_name}'")

    # Determine target version
    if version_number is None:
        if len(versions) < 2:
            raise ValueError("No previous version to rollback to")
        version_number = versions[-2]["number"]

    # Verify target exists
    target_data = get_version(wf_name, version_number, base_dir)

    # Save current state as pre-rollback
    local_path = Path(base_dir) / f"{wf_name}.json"
    if local_path.exists():
        current_data = json.loads(local_path.read_text(encoding="utf-8"))
        save_version(wf_name, current_data, "pre-rollback", source_id=workflow_id, base_dir=base_dir)

    # Restore local file
    local_path.write_text(
        json.dumps(target_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Push to remote
    result = client.update_workflow(workflow_id, target_data)

    # Save as rollback version
    rollback_ver = save_version(
        wf_name, target_data, "rollback",
        source_id=workflow_id, base_dir=base_dir,
    )

    return {
        "rolled_back_to": version_number,
        "new_version": rollback_ver,
        "workflow_id": workflow_id,
        "remote_update": result,
    }
