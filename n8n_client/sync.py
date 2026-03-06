"""Workflow sync — pull, push, and diff between local files and remote n8n."""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

from n8n_client.client import N8nClient
from n8n_client.validator import ALLOWED_NODE_KEYS

# Remote WF fields to strip for local storage
_STRIP_WORKFLOW_KEYS = {
    "createdAt", "updatedAt", "versionId", "active", "hash",
    "meta", "tags", "shared", "statistics", "triggerCount",
    "updatedBy", "homeProject", "usedCredentials",
}


def clean_workflow_for_local(wf: dict) -> dict:
    """Remove server-only fields from a workflow for local storage."""
    wf = copy.deepcopy(wf)
    for key in _STRIP_WORKFLOW_KEYS:
        wf.pop(key, None)

    cleaned_nodes = []
    for node in wf.get("nodes", []):
        cleaned = {k: v for k, v in node.items() if k in ALLOWED_NODE_KEYS}
        cleaned_nodes.append(cleaned)
    wf["nodes"] = cleaned_nodes

    return wf


def workflow_filename(wf: dict) -> str:
    """Generate a filename from the workflow name."""
    name = wf.get("name", "untitled")
    name = name.replace(" ", "-")
    # Keep Japanese, alphanumeric, hyphens, underscores
    name = re.sub(r"[^\w\-\u3000-\u9fff\uff00-\uffef]", "", name)
    name = re.sub(r"-+", "-", name).strip("-")
    if not name:
        name = "untitled"
    return f"{name}.json"


def pull_workflow(client: N8nClient, workflow_id: str, output_dir: str = "workflows") -> str:
    """Pull a single workflow from remote and save locally."""
    wf = client.get_workflow(workflow_id)
    cleaned = clean_workflow_for_local(wf)

    os.makedirs(output_dir, exist_ok=True)
    filename = workflow_filename(cleaned)
    path = os.path.join(output_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return path


def pull_all_workflows(
    client: N8nClient,
    output_dir: str = "workflows",
    project_id: str | None = None,
) -> list[str]:
    """Pull all workflows from remote. Handles pagination via cursor."""
    saved_paths: list[str] = []
    cursor: str | None = None

    while True:
        result = client.list_workflows(project_id=project_id, cursor=cursor)
        workflows = result.get("data", [])

        for wf_summary in workflows:
            wf_id = str(wf_summary["id"])
            path = pull_workflow(client, wf_id, output_dir)
            saved_paths.append(path)

        next_cursor = result.get("nextCursor")
        if not next_cursor:
            break
        cursor = next_cursor

    return saved_paths


def diff_workflow(client: N8nClient, workflow_id: str, local_path: str) -> dict:
    """Compare remote workflow with local file and return structured diff."""
    remote = client.get_workflow(workflow_id)
    remote_clean = clean_workflow_for_local(remote)

    with open(local_path, "r", encoding="utf-8") as f:
        local = json.load(f)

    # Build node maps by name
    remote_nodes = {n["name"]: n for n in remote_clean.get("nodes", []) if "name" in n}
    local_nodes = {n["name"]: n for n in local.get("nodes", []) if "name" in n}

    remote_names = set(remote_nodes.keys())
    local_names = set(local_nodes.keys())

    nodes_added = sorted(local_names - remote_names)
    nodes_removed = sorted(remote_names - local_names)

    nodes_changed: list[dict] = []
    for name in sorted(remote_names & local_names):
        changes = _diff_node(remote_nodes[name], local_nodes[name])
        if changes:
            nodes_changed.append({"name": name, "changes": changes})

    connections_changed = remote_clean.get("connections", {}) != local.get("connections", {})
    settings_changed = remote_clean.get("settings", {}) != local.get("settings", {})

    # Build summary
    parts: list[str] = []
    if nodes_added:
        parts.append(f"{len(nodes_added)} node(s) added")
    if nodes_removed:
        parts.append(f"{len(nodes_removed)} node(s) removed")
    if nodes_changed:
        parts.append(f"{len(nodes_changed)} node(s) changed")
    if connections_changed:
        parts.append("connections changed")
    if settings_changed:
        parts.append("settings changed")
    summary = ", ".join(parts) if parts else "no changes"

    return {
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "nodes_changed": nodes_changed,
        "connections_changed": connections_changed,
        "settings_changed": settings_changed,
        "summary": summary,
    }


def _diff_node(remote: dict, local: dict) -> list[str]:
    """Compare two nodes and return list of change descriptions."""
    changes: list[str] = []
    all_keys = set(remote.keys()) | set(local.keys())
    for key in sorted(all_keys):
        rv = remote.get(key)
        lv = local.get(key)
        if rv != lv:
            changes.append(f"{key} differs")
    return changes


def format_diff(diff: dict) -> str:
    """Format a diff result as human-readable text."""
    lines: list[str] = []
    lines.append(f"Summary: {diff['summary']}")

    if diff["nodes_added"]:
        lines.append("\nAdded nodes:")
        for name in diff["nodes_added"]:
            lines.append(f"  + {name}")

    if diff["nodes_removed"]:
        lines.append("\nRemoved nodes:")
        for name in diff["nodes_removed"]:
            lines.append(f"  - {name}")

    if diff["nodes_changed"]:
        lines.append("\nChanged nodes:")
        for entry in diff["nodes_changed"]:
            lines.append(f"  ~ {entry['name']}")
            for change in entry["changes"]:
                lines.append(f"      {change}")

    if diff["connections_changed"]:
        lines.append("\nConnections: changed")

    if diff["settings_changed"]:
        lines.append("\nSettings: changed")

    return "\n".join(lines)


def push_workflow(client: N8nClient, workflow_id: str, local_path: str) -> dict:
    """Push local workflow to remote. Returns diff info and update result."""
    diff = diff_workflow(client, workflow_id, local_path)

    with open(local_path, "r", encoding="utf-8") as f:
        local_data = json.load(f)

    result = client.update_workflow(workflow_id, local_data)

    return {
        "diff": diff,
        "update_result": result,
    }
