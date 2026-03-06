"""Webhook testing and execution result analysis for n8n workflows."""

from __future__ import annotations

import json
import time

import requests

from n8n_client.client import N8nClient
from n8n_client.validator import extract_webhook_paths, extract_trigger_type


def generate_test_data(wf: dict) -> dict:
    """Generate sample test data based on the workflow's trigger type and structure.

    Analyzes the first node after trigger to infer expected input shape.
    """
    trigger_type = extract_trigger_type(wf)
    webhooks = extract_webhook_paths(wf)
    nodes = wf.get("nodes", [])

    result: dict = {
        "trigger_type": trigger_type,
        "test_data": {},
        "webhook_info": None,
        "instructions": "",
    }

    # Webhook trigger
    if webhooks:
        wh = webhooks[0]
        result["webhook_info"] = wh
        sample = _infer_sample_from_downstream(wf, wh["node_name"])
        result["test_data"] = sample
        result["instructions"] = (
            f"Webhook ({wh['method']}) にテストデータを送信します。\n"
            f"Path: /webhook-test/{wh['path']}"
        )
        return result

    # Manual or schedule trigger
    if trigger_type in ("manual", "n8n-nodes-base.manualTrigger", "schedule", "n8n-nodes-base.scheduleTrigger"):
        result["test_data"] = {}
        result["instructions"] = "手動トリガーのため、n8n API 経由で実行します。"
        return result

    # Polling trigger (Google Calendar, etc.)
    if trigger_type:
        sample = _infer_sample_from_trigger(wf, trigger_type)
        result["test_data"] = sample
        result["instructions"] = (
            f"ポーリングトリガー ({trigger_type}) のテストは、\n"
            f"n8n UI のテスト実行機能を使うか、後続ノードの入力に合わせたテストデータで実行してください。"
        )
        return result

    result["instructions"] = "トリガーが検出できませんでした。手動でテストデータを作成してください。"
    return result


def _infer_sample_from_downstream(wf: dict, trigger_name: str) -> dict:
    """Try to infer expected input from nodes connected to the trigger."""
    connections = wf.get("connections", {})
    nodes_by_name = {n["name"]: n for n in wf.get("nodes", [])}

    # Find first downstream node
    conns = connections.get(trigger_name, {})
    main_conns = conns.get("main", [[]])[0] if conns else []
    if not main_conns:
        return {"message": "test", "timestamp": "2024-01-01T00:00:00Z"}

    next_node_name = main_conns[0].get("node", "")
    next_node = nodes_by_name.get(next_node_name, {})

    # If next node is Code, try to extract expected fields from code
    if next_node.get("type") == "n8n-nodes-base.code":
        return _extract_fields_from_code(next_node)

    # If next node is Set, extract field names
    if next_node.get("type") == "n8n-nodes-base.set":
        return _extract_fields_from_set(next_node)

    # If next node is If/Switch, extract condition fields
    if next_node.get("type") in ("n8n-nodes-base.if", "n8n-nodes-base.switch"):
        return _extract_fields_from_conditions(next_node)

    return {"message": "test", "data": {"key": "value"}}


def _extract_fields_from_code(node: dict) -> dict:
    """Extract referenced field names from Code node to generate sample data."""
    import re
    params = node.get("parameters", {})
    code = params.get("pythonCode", "") or params.get("jsCode", "")

    # Pattern: item["json"]["fieldName"] or item.json.fieldName or .json.fieldName
    fields: set[str] = set()
    patterns = [
        r'\["json"\]\["(\w+)"\]',
        r'\[\"json\"\]\[\"(\w+)\"\]',
        r'\.json\.(\w+)',
        r'\.json\[[\"\'](\w+)[\"\']\]',
    ]
    for pattern in patterns:
        fields.update(re.findall(pattern, code))

    if not fields:
        return {"message": "test", "data": {"key": "value"}}

    sample = {}
    for field in fields:
        if "date" in field.lower() or "time" in field.lower():
            sample[field] = "2024-01-01T00:00:00Z"
        elif "id" in field.lower():
            sample[field] = "test-id-001"
        elif "email" in field.lower():
            sample[field] = "test@example.com"
        elif "name" in field.lower():
            sample[field] = "Test Name"
        elif "url" in field.lower():
            sample[field] = "https://example.com"
        elif "count" in field.lower() or "num" in field.lower() or "amount" in field.lower():
            sample[field] = 1
        elif "flag" in field.lower() or field.startswith("is") or field.startswith("has"):
            sample[field] = True
        else:
            sample[field] = f"test_{field}"
    return sample


def _extract_fields_from_set(node: dict) -> dict:
    """Extract field references from Set node assignments."""
    params = node.get("parameters", {})
    assignments = params.get("assignments", {}).get("assignments", [])
    sample = {}
    for a in assignments:
        value = a.get("value", "")
        if isinstance(value, str) and "{{" in value:
            # Extract expression references like {{ $json.fieldName }}
            import re
            refs = re.findall(r'\$json\.(\w+)', value)
            for ref in refs:
                sample[ref] = f"test_{ref}"
    return sample or {"message": "test"}


def _extract_fields_from_conditions(node: dict) -> dict:
    """Extract field references from If/Switch conditions."""
    import re
    params = node.get("parameters", {})
    params_str = json.dumps(params)
    refs = re.findall(r'\$json\.(\w+)', params_str)
    sample = {}
    for ref in set(refs):
        sample[ref] = f"test_{ref}"
    return sample or {"status": "test"}


def _infer_sample_from_trigger(wf: dict, trigger_type: str) -> dict:
    """Generate sample data matching common trigger output shapes."""
    if "calendar" in trigger_type.lower():
        return {
            "summary": "Test Event",
            "start": {"dateTime": "2024-01-01T10:00:00+09:00"},
            "end": {"dateTime": "2024-01-01T11:00:00+09:00"},
            "attendees": [{"email": "test@example.com"}],
        }
    if "slack" in trigger_type.lower():
        return {
            "type": "message",
            "text": "Test message",
            "user": "U0000000000",
            "channel": "C0000000000",
            "ts": "1700000000.000000",
        }
    if "gmail" in trigger_type.lower():
        return {
            "id": "msg-001",
            "subject": "Test Email",
            "from": "sender@example.com",
            "to": "receiver@example.com",
            "body": "This is a test email.",
        }
    return {"event": "test", "data": {}}


# ─── Webhook Testing ────────────────────────────────────


def send_webhook_test(
    base_url: str,
    path: str,
    data: dict,
    method: str = "POST",
) -> dict:
    """Send test data to a webhook URL and return the response."""
    url = f"{base_url.rstrip('/')}/webhook-test/{path.lstrip('/')}"
    try:
        resp = requests.request(
            method, url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        return {
            "status_code": resp.status_code,
            "url": url,
            "response_body": _safe_json(resp),
            "success": 200 <= resp.status_code < 300,
        }
    except requests.RequestException as e:
        return {
            "status_code": None,
            "url": url,
            "response_body": str(e),
            "success": False,
        }


def _safe_json(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        return resp.text[:2000]


# ─── Execution Result Analysis ──────────────────────────


def wait_for_execution(
    client: N8nClient,
    workflow_id: str,
    *,
    timeout: int = 60,
    poll_interval: int = 2,
) -> dict | None:
    """Poll for the latest execution of a workflow and wait until it completes."""
    start = time.time()
    seen_ids: set[str] = set()

    # Record existing execution IDs first
    existing = client.list_executions(workflow_id=workflow_id, limit=5)
    for ex in existing.get("data", []):
        seen_ids.add(str(ex.get("id", "")))

    while time.time() - start < timeout:
        time.sleep(poll_interval)
        recent = client.list_executions(workflow_id=workflow_id, limit=5)
        for ex in recent.get("data", []):
            ex_id = str(ex.get("id", ""))
            if ex_id not in seen_ids:
                status = ex.get("status", "")
                if status in ("success", "error", "canceled"):
                    return client.get_execution(ex_id, include_data=True)
                if status == "running":
                    # Wait for it to finish
                    while time.time() - start < timeout:
                        time.sleep(poll_interval)
                        detail = client.get_execution(ex_id, include_data=True)
                        if detail.get("status") in ("success", "error", "canceled"):
                            return detail

    return None


def analyze_execution(execution: dict) -> dict:
    """Analyze an execution result and produce a human-readable summary."""
    status = execution.get("status", "unknown")
    finished_at = execution.get("stoppedAt", "")
    started_at = execution.get("startedAt", "")

    summary: dict = {
        "execution_id": execution.get("id"),
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "nodes": [],
        "error_detail": None,
    }

    data = execution.get("data", {})
    result_data = data.get("resultData", {})
    run_data = result_data.get("runData", {})

    for node_name, runs in run_data.items():
        for run in runs:
            node_info: dict = {
                "name": node_name,
                "status": "success",
                "items_count": 0,
                "error": None,
            }

            if run.get("error"):
                node_info["status"] = "error"
                err = run["error"]
                node_info["error"] = {
                    "message": err.get("message", str(err)),
                    "description": err.get("description", ""),
                }
                summary["error_detail"] = node_info["error"]

            # Count output items
            output_data = run.get("data", {}).get("main", [])
            for branch in output_data:
                if branch:
                    node_info["items_count"] += len(branch)

            summary["nodes"].append(node_info)

    return summary


def format_execution_summary(analysis: dict) -> str:
    """Format execution analysis as readable text."""
    lines: list[str] = []
    status_icon = {"success": "OK", "error": "NG", "canceled": "--"}.get(analysis["status"], "??")
    lines.append(f"Execution {analysis['execution_id']}: [{status_icon}] {analysis['status']}")
    lines.append(f"  Started: {analysis['started_at']}")
    lines.append(f"  Finished: {analysis['finished_at']}")
    lines.append("")
    lines.append("Node Results:")

    for node in analysis["nodes"]:
        icon = "OK" if node["status"] == "success" else "NG"
        line = f"  [{icon}] {node['name']} ({node['items_count']} items)"
        lines.append(line)
        if node.get("error"):
            lines.append(f"       Error: {node['error']['message']}")
            if node["error"].get("description"):
                lines.append(f"       Detail: {node['error']['description']}")

    if analysis.get("error_detail"):
        lines.append("")
        lines.append(f"Error Summary: {analysis['error_detail']['message']}")

    return "\n".join(lines)
