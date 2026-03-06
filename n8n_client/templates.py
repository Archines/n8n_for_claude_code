"""Template management for n8n workflows."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "workflows" / "templates"


def list_templates() -> list[dict]:
    """Return available templates. Each dict: {name, description, trigger_type, nodes_count}."""
    templates = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        meta = data.get("_metadata", {})
        templates.append({
            "name": meta.get("template_name", path.stem),
            "description": meta.get("description", ""),
            "trigger_type": meta.get("trigger_type", ""),
            "nodes_count": len(data.get("nodes", [])),
        })
    return templates


def get_template(name: str) -> dict:
    """Return template JSON by name."""
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {name}")
    with open(path) as f:
        return json.load(f)


def instantiate_template(name: str, *, workflow_name: str | None = None) -> dict:
    """Generate a workflow from a template. Re-assigns all node IDs with uuid4."""
    import copy
    template = get_template(name)
    wf = copy.deepcopy(template)

    # Remove template metadata from output
    wf.pop("_metadata", None)

    # Override workflow name if provided
    if workflow_name:
        wf["name"] = workflow_name

    # Build old->new ID mapping and reassign
    id_map: dict[str, str] = {}
    for node in wf.get("nodes", []):
        old_id = node.get("id", "")
        new_id = str(uuid.uuid4())
        id_map[old_id] = new_id
        node["id"] = new_id

    # Reassign webhookId if present
    for node in wf.get("nodes", []):
        if "webhookId" in node:
            node["webhookId"] = str(uuid.uuid4())

    return wf
