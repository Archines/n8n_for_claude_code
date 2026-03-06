"""Workflow visualization — text tree and summary."""

from __future__ import annotations

from n8n_client.validator import (
    extract_trigger_type,
    extract_webhook_paths,
    extract_required_credentials,
)

_SHORT_TYPES = {
    "n8n-nodes-base.webhook": "Webhook",
    "n8n-nodes-base.code": "Code",
    "n8n-nodes-base.slack": "Slack",
    "n8n-nodes-base.httpRequest": "HTTP",
    "n8n-nodes-base.if": "If",
    "n8n-nodes-base.switch": "Switch",
    "n8n-nodes-base.set": "Set",
}

_BRANCH_LABELS = {
    "n8n-nodes-base.if": {0: "true", 1: "false"},
}


def _short_type(node_type: str) -> str:
    if node_type in _SHORT_TYPES:
        return _SHORT_TYPES[node_type]
    # Take the last segment after '.' and capitalize
    parts = node_type.rsplit(".", 1)
    return parts[-1].capitalize() if len(parts) > 1 else node_type.capitalize()


def _node_suffix(node: dict) -> str:
    """Extra info shown after the node name."""
    node_type = node.get("type", "")
    params = node.get("parameters", {})

    if node_type in ("n8n-nodes-base.webhook", "n8n-nodes-base.webhookTest"):
        method = params.get("httpMethod", "GET")
        path = params.get("path", "")
        return f" ({method} /{path})"

    if node_type == "n8n-nodes-base.code":
        lang = params.get("language", "javaScript")
        if lang == "pythonNative":
            return " (Python)"
        return " (JS)"

    return ""


def visualize_workflow(wf: dict) -> str:
    """Generate a text tree from a workflow JSON."""
    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})

    if not nodes:
        return "(empty workflow)"

    node_map = {n["name"]: n for n in nodes}

    # Find root nodes (no incoming connections)
    targets = set()
    for src_name, conn_data in connections.items():
        for output_group in conn_data.get("main", []):
            for link in output_group:
                targets.add(link["node"])

    roots = [n["name"] for n in nodes if n["name"] not in targets]
    if not roots:
        roots = [nodes[0]["name"]]

    lines: list[str] = []
    visited: set[str] = set()

    def _render(name: str, prefix: str, connector: str):
        if name not in node_map:
            return
        if name in visited:
            lines.append(f"{prefix}{connector}({name} - loop)")
            return
        visited.add(name)

        node = node_map[name]
        short = _short_type(node.get("type", ""))
        suffix = _node_suffix(node)
        lines.append(f"{prefix}{connector}[{short}] {name}{suffix}")

        # Get outgoing connections
        node_conns = connections.get(name, {}).get("main", [])
        if not node_conns:
            return

        node_type = node.get("type", "")
        branch_labels = _BRANCH_LABELS.get(node_type)
        is_switch = node_type == "n8n-nodes-base.switch"

        # Collect all branches with their targets
        branches: list[tuple[str | None, list[dict]]] = []
        for idx, output_group in enumerate(node_conns):
            if not output_group:
                continue
            if branch_labels and idx in branch_labels:
                label = branch_labels[idx]
            elif is_switch:
                label = str(idx)
            elif len(node_conns) > 1:
                label = str(idx)
            else:
                label = None
            branches.append((label, output_group))

        # Calculate child prefix based on current indentation
        if not connector:
            child_prefix = ""
        else:
            child_prefix = prefix + "  "

        if len(branches) == 1 and branches[0][0] is None:
            # Single output, no branching
            for link in branches[0][1]:
                _render(link["node"], child_prefix, "-> ")
        else:
            # Multiple branches with tree characters
            for bi, (label, targets_list) in enumerate(branches):
                is_last = bi == len(branches) - 1
                connector_char = "\u2514\u2500" if is_last else "\u251c\u2500"
                cont_char = "  " if is_last else "\u2502 "
                label_str = f" {label} " if label else " "
                for ti, link in enumerate(targets_list):
                    if ti == 0:
                        _render(
                            link["node"],
                            child_prefix + cont_char,
                            f"{connector_char}{label_str}-> ",
                        )
                    else:
                        _render(
                            link["node"],
                            child_prefix + cont_char,
                            f"  {' ' * len(label_str)}-> ",
                        )

    for ri, root in enumerate(roots):
        if ri > 0:
            lines.append("")
        _render(root, "", "")

    return "\n".join(lines)


def summarize_workflow(wf: dict) -> str:
    """Generate a 1-3 line summary of a workflow."""
    name = wf.get("name", "(unnamed)")
    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})

    # Trigger info
    trigger_type = extract_trigger_type(wf)
    trigger_str = trigger_type or "none"
    webhooks = extract_webhook_paths(wf)
    if webhooks:
        wh = webhooks[0]
        trigger_str = f"webhook ({wh['method']} /{wh['path']})"

    # Credentials
    creds = extract_required_credentials(wf)
    cred_types = [c["type"] for c in creds]
    cred_str = ", ".join(cred_types) if cred_types else "none"

    # Connection chain summary
    node_map = {n["name"]: n for n in nodes}
    targets = set()
    for src_name, conn_data in connections.items():
        for output_group in conn_data.get("main", []):
            for link in output_group:
                targets.add(link["node"])
    roots = [n["name"] for n in nodes if n["name"] not in targets]

    chain_parts: list[str] = []
    if roots:
        current = roots[0]
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            chain_parts.append(current)
            node_conns = connections.get(current, {}).get("main", [])
            if not node_conns:
                break
            # Count total branches
            non_empty = [g for g in node_conns if g]
            if len(non_empty) > 1:
                chain_parts.append(f"[{len(non_empty)} branches]")
                break
            if non_empty and non_empty[0]:
                current = non_empty[0][0]["node"]
            else:
                break

    chain_str = " -> ".join(chain_parts) if chain_parts else "-"

    lines = [
        f"[{name}] {chain_parts[0] if chain_parts else '-'}",
        f"  Nodes: {len(nodes)} | Trigger: {trigger_str} | Credentials: {cred_str}",
        f"  Connections: {chain_str}",
    ]
    return "\n".join(lines)
