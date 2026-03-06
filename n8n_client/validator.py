"""Workflow JSON validator — Cloud compatibility checks and auto-fix."""

from __future__ import annotations

import re
import uuid

# Cloud で許可されるノードのトップレベルプロパティ
ALLOWED_NODE_KEYS = {
    "id", "name", "parameters", "position", "type", "typeVersion",
    "credentials", "webhookId", "disabled", "notesInFlow", "notes",
}

# 不許可だがよく混入するプロパティ
DISALLOWED_NODE_KEYS = {
    "retryOnFail", "maxTries", "waitBetweenTries", "onError",
    "polling", "alwaysOutputData", "executeOnce", "continueOnFail",
}

# 動作確認済み typeVersion マッピング
VERIFIED_TYPE_VERSIONS: dict[str, float | int] = {
    "n8n-nodes-base.code": 2,
    "n8n-nodes-base.if": 2.2,
    "n8n-nodes-base.httpRequest": 4.2,
    "n8n-nodes-base.switch": 3.2,
    "n8n-nodes-base.set": 3.4,
    "n8n-nodes-base.stickyNote": 1,
    "n8n-nodes-base.webhook": 1,
    "n8n-nodes-base.respondToWebhook": 1.1,
    "n8n-nodes-base.notion": 2.2,
    "n8n-nodes-base.googleCalendarTrigger": 1,
}

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def _is_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value))


# ─── Validation ──────────────────────────────────────────


class ValidationIssue:
    def __init__(self, level: str, node_name: str, message: str):
        self.level = level  # "error" | "warning"
        self.node_name = node_name
        self.message = message

    def __repr__(self):
        return f"[{self.level.upper()}] {self.node_name}: {self.message}"


def validate_workflow(wf: dict) -> list[ValidationIssue]:
    """Validate a workflow JSON for Cloud compatibility. Returns list of issues."""
    issues: list[ValidationIssue] = []
    nodes = wf.get("nodes", [])

    if not nodes:
        issues.append(ValidationIssue("error", "(workflow)", "No nodes defined"))
        return issues

    for node in nodes:
        name = node.get("name", "(unnamed)")
        node_type = node.get("type", "")

        # UUID check
        node_id = node.get("id", "")
        if not node_id:
            issues.append(ValidationIssue("error", name, "Missing node id"))
        elif not _is_uuid(node_id):
            issues.append(ValidationIssue("error", name, f"Node id is not UUID format: '{node_id}'"))

        # Disallowed properties
        extra_keys = set(node.keys()) - ALLOWED_NODE_KEYS
        if extra_keys:
            issues.append(ValidationIssue(
                "error", name,
                f"Disallowed top-level properties: {', '.join(sorted(extra_keys))}",
            ))

        # typeVersion check
        if node_type in VERIFIED_TYPE_VERSIONS:
            expected = VERIFIED_TYPE_VERSIONS[node_type]
            actual = node.get("typeVersion")
            if actual is not None and actual != expected:
                issues.append(ValidationIssue(
                    "warning", name,
                    f"typeVersion {actual} may not work on Cloud. Verified: {expected}",
                ))

        # Python Code Node checks
        if node_type == "n8n-nodes-base.code":
            params = node.get("parameters", {})
            lang = params.get("language", "")
            code = params.get("pythonCode", "")
            if lang == "pythonNative" and code:
                if "_input" in code:
                    issues.append(ValidationIssue(
                        "error", name,
                        "Python code uses '_input' which doesn't exist. Use '_items[0][\"json\"]' instead.",
                    ))
                if "_node" in code:
                    issues.append(ValidationIssue(
                        "warning", name,
                        "Python code uses '_node' which doesn't exist. Switch to JavaScript for cross-node references.",
                    ))

        # googleCalendarTrigger: pollTimes required
        if node_type == "n8n-nodes-base.googleCalendarTrigger":
            params = node.get("parameters", {})
            if "pollTimes" not in params:
                issues.append(ValidationIssue(
                    "error", name,
                    "googleCalendarTrigger requires 'pollTimes' parameter.",
                ))

        # Default node name warning
        if name in ("HTTP Request", "Set", "Code", "IF", "Switch", "Webhook"):
            issues.append(ValidationIssue(
                "warning", name,
                f"Node uses default name '{name}'. Rename to describe its purpose.",
            ))

    # Connections reference check
    connections = wf.get("connections", {})
    node_names = {n.get("name") for n in nodes}
    for source_name in connections:
        if source_name not in node_names:
            issues.append(ValidationIssue(
                "error", source_name,
                "Referenced in connections but not found in nodes.",
            ))

    return issues


# ─── Sanitization (auto-fix) ────────────────────────────


def sanitize_workflow(wf: dict) -> tuple[dict, list[str]]:
    """Auto-fix common Cloud compatibility issues. Returns (fixed_wf, list of changes)."""
    import copy
    wf = copy.deepcopy(wf)
    changes: list[str] = []

    for node in wf.get("nodes", []):
        name = node.get("name", "(unnamed)")

        # Fix non-UUID ids
        node_id = node.get("id", "")
        if not node_id or not _is_uuid(node_id):
            new_id = str(uuid.uuid4())
            node["id"] = new_id
            changes.append(f"'{name}': Generated UUID id: {new_id}")

        # Remove disallowed properties
        extra_keys = set(node.keys()) - ALLOWED_NODE_KEYS
        for key in extra_keys:
            del node[key]
            changes.append(f"'{name}': Removed disallowed property: {key}")

        # Fix typeVersion if known
        node_type = node.get("type", "")
        if node_type in VERIFIED_TYPE_VERSIONS:
            expected = VERIFIED_TYPE_VERSIONS[node_type]
            actual = node.get("typeVersion")
            if actual is None:
                node["typeVersion"] = expected
                changes.append(f"'{name}': Set typeVersion to {expected}")

    return wf, changes


# ─── Extraction helpers ──────────────────────────────────


def extract_required_credentials(wf: dict) -> list[dict]:
    """Extract credential types required by the workflow."""
    required: list[dict] = []
    seen = set()
    for node in wf.get("nodes", []):
        for cred_type, cred_info in node.get("credentials", {}).items():
            if cred_type not in seen:
                seen.add(cred_type)
                required.append({
                    "type": cred_type,
                    "node_name": node.get("name", ""),
                    "node_type": node.get("type", ""),
                    "existing_id": cred_info.get("id"),
                    "existing_name": cred_info.get("name"),
                })
    return required


def extract_sub_workflows(wf: dict) -> list[dict]:
    """Detect executeWorkflow nodes and their sub-workflow references."""
    sub_wfs: list[dict] = []
    for node in wf.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.executeWorkflow":
            params = node.get("parameters", {})
            sub_wf = params.get("workflowId") or params.get("subWorkflow", {})
            sub_wfs.append({
                "node_name": node.get("name", ""),
                "sub_workflow_ref": sub_wf,
            })
    return sub_wfs


def extract_webhook_paths(wf: dict) -> list[dict]:
    """Extract webhook paths from webhook trigger nodes."""
    webhooks: list[dict] = []
    for node in wf.get("nodes", []):
        if node.get("type") in ("n8n-nodes-base.webhook", "n8n-nodes-base.webhookTest"):
            params = node.get("parameters", {})
            path = params.get("path", "")
            method = params.get("httpMethod", "GET")
            webhooks.append({
                "node_name": node.get("name", ""),
                "path": path,
                "method": method,
            })
    return webhooks


def extract_trigger_type(wf: dict) -> str | None:
    """Identify the trigger type of the workflow."""
    for node in wf.get("nodes", []):
        node_type = node.get("type", "")
        if "trigger" in node_type.lower() or "webhook" in node_type.lower():
            return node_type
        if node_type == "n8n-nodes-base.manualTrigger":
            return "manual"
        if node_type == "n8n-nodes-base.scheduleTrigger":
            return "schedule"
    return None
