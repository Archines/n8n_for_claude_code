"""Workflow dependency map — downstream/upstream analysis."""

from __future__ import annotations

from n8n_client.client import N8nClient
from n8n_client.validator import extract_sub_workflows


def _resolve_sub_workflow_id(ref) -> str | None:
    """Extract workflow ID from an executeWorkflow node reference."""
    if isinstance(ref, str):
        return ref if ref else None
    if isinstance(ref, dict):
        return ref.get("value") or ref.get("id") or None
    return None


def build_dependency_tree(
    client: N8nClient,
    workflow_id: str,
    _visited: set | None = None,
) -> dict:
    """Recursively build a downstream dependency tree.

    Returns: {
        "id": workflow_id,
        "name": "WF name",
        "children": [...],
        "circular": False
    }
    """
    if _visited is None:
        _visited = set()

    if workflow_id in _visited:
        return {
            "id": workflow_id,
            "name": "(circular)",
            "children": [],
            "circular": True,
        }

    _visited.add(workflow_id)

    try:
        wf = client.get_workflow(workflow_id)
    except Exception:
        return {
            "id": workflow_id,
            "name": "(not found)",
            "children": [],
            "circular": False,
        }

    wf_name = wf.get("name", "(unnamed)")
    sub_refs = extract_sub_workflows(wf)

    children = []
    for ref in sub_refs:
        sub_id = _resolve_sub_workflow_id(ref["sub_workflow_ref"])
        if sub_id:
            child = build_dependency_tree(client, sub_id, _visited)
            children.append(child)

    return {
        "id": workflow_id,
        "name": wf_name,
        "children": children,
        "circular": False,
    }


def find_dependents(client: N8nClient, workflow_id: str) -> list[dict]:
    """Find upstream workflows that reference this workflow.

    Scans all workflows for Execute Workflow nodes pointing to workflow_id.
    Returns: [{"id": "...", "name": "...", "node_name": "..."}]
    """
    dependents: list[dict] = []
    cursor = None

    while True:
        result = client.list_workflows(limit=100, cursor=cursor)
        workflows = result.get("data", [])

        for wf_summary in workflows:
            wf_id = str(wf_summary.get("id", ""))
            if wf_id == workflow_id:
                continue

            try:
                wf = client.get_workflow(wf_id)
            except Exception:
                continue

            sub_refs = extract_sub_workflows(wf)
            for ref in sub_refs:
                sub_id = _resolve_sub_workflow_id(ref["sub_workflow_ref"])
                if sub_id == workflow_id:
                    dependents.append({
                        "id": wf_id,
                        "name": wf.get("name", "(unnamed)"),
                        "node_name": ref["node_name"],
                    })

        next_cursor = result.get("nextCursor")
        if not next_cursor:
            break
        cursor = next_cursor

    return dependents


def format_dependency_tree(tree: dict, indent: int = 0) -> str:
    """Format dependency tree as text with box-drawing characters.

    MyWorkflow (abc123)
    ├─ Sub WF A (def456)
    │  └─ Sub Sub WF (ghi789)
    └─ Sub WF B (jkl012)
    """
    lines: list[str] = []
    _render_tree(tree, lines, "", is_root=True)
    return "\n".join(lines)


def _render_tree(
    tree: dict,
    lines: list[str],
    prefix: str,
    is_root: bool = False,
    connector: str = "",
) -> None:
    label = f"{tree['name']} ({tree['id']})"
    if tree.get("circular"):
        label += " [circular]"

    if is_root:
        lines.append(label)
    else:
        lines.append(f"{prefix}{connector}{label}")

    children = tree.get("children", [])
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        if is_root:
            child_prefix = ""
            child_connector = "└─ " if is_last else "├─ "
            next_prefix = "   " if is_last else "│  "
        else:
            child_connector = "└─ " if is_last else "├─ "
            next_prefix = prefix + ("   " if is_last else "│  ")

        _render_tree(
            child,
            lines,
            next_prefix if not is_root else next_prefix,
            is_root=False,
            connector=child_connector,
        )


def format_dependency_summary(
    workflow_id: str,
    workflow_name: str,
    upstream: list[dict],
    downstream: dict,
) -> str:
    """Format a combined upstream/downstream summary.

    Workflow: MyWorkflow (abc123)

    Downstream (calls):
      ├─ Sub WF A
      └─ Sub WF B

    Upstream (called by):
      ├─ Parent WF 1
      └─ Parent WF 2
    """
    lines: list[str] = [f"Workflow: {workflow_name} ({workflow_id})", ""]

    # Downstream
    children = downstream.get("children", [])
    lines.append("Downstream (calls):")
    if children:
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└─" if is_last else "├─"
            label = f"{child['name']} ({child['id']})"
            if child.get("circular"):
                label += " [circular]"
            lines.append(f"  {connector} {label}")
    else:
        lines.append("  (none)")

    lines.append("")

    # Upstream
    lines.append("Upstream (called by):")
    if upstream:
        for i, dep in enumerate(upstream):
            is_last = i == len(upstream) - 1
            connector = "└─" if is_last else "├─"
            lines.append(f"  {connector} {dep['name']} ({dep['id']}) via [{dep['node_name']}]")
    else:
        lines.append("  (none)")

    return "\n".join(lines)
