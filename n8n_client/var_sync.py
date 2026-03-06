"""Variable sync between local files and remote n8n instance."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from n8n_client.client import N8nClient


def _get_all_variables(client: N8nClient) -> list[dict]:
    """Fetch all variables from remote, handling pagination."""
    result = client.list_variables()
    variables = result.get("data", [])
    while result.get("nextCursor"):
        result = client.list_variables(cursor=result["nextCursor"])
        variables.extend(result.get("data", []))
    return variables


def pull_variables(client: N8nClient, client_name: str, output_dir: str = "workflows/variables") -> dict:
    """Pull variables from remote and save to local file."""
    variables = _get_all_variables(client)

    var_list = [
        {"key": v["key"], "value": v.get("value", ""), "type": v.get("type", "string")}
        for v in variables
    ]

    data = {
        "client_name": client_name,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "variables": var_list,
    }

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{client_name}.vars.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return data


def push_variables(client: N8nClient, input_path: str) -> dict:
    """Sync variables from local file to remote."""
    with open(input_path, encoding="utf-8") as f:
        local_data = json.load(f)

    local_vars = {v["key"]: v for v in local_data.get("variables", [])}
    remote_vars_list = _get_all_variables(client)
    remote_vars = {v["key"]: v for v in remote_vars_list}

    created = []
    updated = []
    delete_candidates = []

    # Create or update
    for key, local_v in local_vars.items():
        if key not in remote_vars:
            client.create_variable(key, local_v["value"])
            created.append(key)
        elif remote_vars[key].get("value", "") != local_v["value"]:
            remote_id = remote_vars[key]["id"]
            client.update_variable(str(remote_id), key, local_v["value"])
            updated.append(key)

    # Detect delete candidates
    for key in remote_vars:
        if key not in local_vars:
            delete_candidates.append(key)

    return {"created": created, "updated": updated, "delete_candidates": delete_candidates}


def diff_variables(client: N8nClient, input_path: str | None = None, client_name: str = "") -> dict:
    """Compare remote variables vs local file."""
    if input_path is None:
        input_path = f"workflows/variables/{client_name}.vars.json"

    with open(input_path, encoding="utf-8") as f:
        local_data = json.load(f)

    local_vars = {v["key"]: v for v in local_data.get("variables", [])}
    remote_vars_list = _get_all_variables(client)
    remote_vars = {v["key"]: v for v in remote_vars_list}

    added = []
    changed = []
    removed = []

    for key, local_v in local_vars.items():
        if key not in remote_vars:
            added.append({"key": key, "value": local_v["value"]})
        elif remote_vars[key].get("value", "") != local_v["value"]:
            changed.append({
                "key": key,
                "local_value": local_v["value"],
                "remote_value": remote_vars[key].get("value", ""),
            })

    for key, remote_v in remote_vars.items():
        if key not in local_vars:
            removed.append({"key": key, "value": remote_v.get("value", "")})

    return {"added": added, "changed": changed, "removed": removed}


def format_diff(diff: dict) -> str:
    """Format diff for display."""
    lines = ["Variables diff:"]

    if not diff["added"] and not diff["changed"] and not diff["removed"]:
        lines.append("  No differences.")
        return "\n".join(lines)

    for item in diff["added"]:
        lines.append(f'  + {item["key"]} = "{item["value"]}"    (new)')

    for item in diff["changed"]:
        lines.append(f'  ~ {item["key"]}: "{item["remote_value"]}" -> "{item["local_value"]}"')

    for item in diff["removed"]:
        lines.append(f'  - {item["key"]} = "{item["value"]}"    (remote only)')

    return "\n".join(lines)


def export_env(client: N8nClient) -> str:
    """Export all variables as .env format."""
    variables = _get_all_variables(client)
    lines = [f'{v["key"]}={v.get("value", "")}' for v in variables]
    return "\n".join(lines)
