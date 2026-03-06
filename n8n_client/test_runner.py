"""Test automation framework for n8n workflows."""

from __future__ import annotations

import json
from pathlib import Path

from n8n_client.client import N8nClient
from n8n_client.testing import (
    generate_test_data,
    send_webhook_test,
    wait_for_execution,
    analyze_execution,
)


def load_test_suite(test_file: str) -> dict:
    """Load a test suite from a JSON file."""
    path = Path(test_file)
    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {test_file}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_test_suite(
    client: N8nClient,
    base_url: str,
    suite: dict,
) -> list[dict]:
    """Run all tests in a test suite.

    Each test:
    1. Send webhook input (send_webhook_test)
    2. Wait for execution (wait_for_execution)
    3. Verify results against expectations

    Returns: [{"name": "...", "passed": True/False, "details": "..."}]
    """
    workflow_id = suite.get("workflow_id", "")
    results: list[dict] = []

    for test in suite.get("tests", []):
        test_name = test.get("name", "(unnamed)")
        trigger = test.get("trigger", "webhook")
        input_data = test.get("input", {})
        expect = test.get("expect", {})

        result: dict = {"name": test_name, "passed": False, "details": ""}

        if trigger != "webhook":
            result["details"] = f"Unsupported trigger type: {trigger}"
            results.append(result)
            continue

        # 1. Send webhook
        webhook_path = test.get("webhook_path", "")
        if not webhook_path:
            # Try to detect from workflow file
            wf_file = suite.get("workflow_file", "")
            if wf_file and Path(wf_file).exists():
                from n8n_client.validator import extract_webhook_paths
                with open(wf_file, encoding="utf-8") as f:
                    wf = json.load(f)
                webhooks = extract_webhook_paths(wf)
                if webhooks:
                    webhook_path = webhooks[0]["path"]

        if not webhook_path:
            result["details"] = "No webhook path found"
            results.append(result)
            continue

        method = test.get("method", "POST")
        response = send_webhook_test(base_url, webhook_path, input_data, method=method)

        if not response["success"]:
            result["details"] = f"Webhook failed: {response.get('status_code')} {response.get('response_body', '')}"
            results.append(result)
            continue

        # 2. Wait for execution
        if not workflow_id:
            result["details"] = "No workflow_id; cannot wait for execution"
            result["passed"] = expect.get("status") is None
            results.append(result)
            continue

        execution = wait_for_execution(client, workflow_id, timeout=60)
        if not execution:
            result["details"] = "Timeout waiting for execution"
            results.append(result)
            continue

        # 3. Verify results
        analysis = analyze_execution(execution)
        passed, details = _verify_expectations(analysis, expect)
        result["passed"] = passed
        result["details"] = details
        results.append(result)

    return results


def _verify_expectations(analysis: dict, expect: dict) -> tuple[bool, str]:
    """Compare execution analysis against expected results."""
    errors: list[str] = []

    # Check overall status
    expected_status = expect.get("status")
    if expected_status:
        actual_status = analysis.get("status", "unknown")
        if actual_status != expected_status:
            errors.append(f"Expected status: {expected_status}, Got: {actual_status}")

    # Check per-node results
    node_expects = expect.get("node_results", {})
    if node_expects:
        node_map = {n["name"]: n for n in analysis.get("nodes", [])}
        for node_name, expected in node_expects.items():
            actual_node = node_map.get(node_name)
            if not actual_node:
                errors.append(f"Node '{node_name}' not found in execution results")
                continue
            expected_node_status = expected.get("status")
            if expected_node_status and actual_node["status"] != expected_node_status:
                errors.append(
                    f"Node '{node_name}': expected {expected_node_status}, got {actual_node['status']}"
                )

    if errors:
        return False, "\n".join(errors)
    return True, "All expectations met"


def create_test_template(
    wf: dict,
    wf_file: str = "",
    workflow_id: str = "",
) -> dict:
    """Generate a test suite template from a workflow.

    - Detects trigger type
    - Includes downstream node names in expect.node_results
    - Uses generate_test_data for input
    """
    from n8n_client.validator import extract_trigger_type, extract_webhook_paths

    wf_name = wf.get("name", "unnamed")
    trigger_type = extract_trigger_type(wf)
    webhooks = extract_webhook_paths(wf)
    nodes = wf.get("nodes", [])

    # Determine trigger label
    trigger = "webhook" if webhooks else "manual"
    if trigger_type and "schedule" in str(trigger_type).lower():
        trigger = "schedule"

    # Generate test data
    gen = generate_test_data(wf)
    test_input = gen.get("test_data", {})

    # Build node_results expectations from non-trigger nodes
    node_results = {}
    trigger_types = {
        "n8n-nodes-base.webhook", "n8n-nodes-base.webhookTest",
        "n8n-nodes-base.manualTrigger", "n8n-nodes-base.scheduleTrigger",
        "n8n-nodes-base.stickyNote",
    }
    for node in nodes:
        node_type = node.get("type", "")
        if node_type not in trigger_types and "trigger" not in node_type.lower():
            node_results[node.get("name", "")] = {"status": "success"}

    test_case = {
        "name": f"{wf_name} - basic test",
        "description": "Auto-generated test template",
        "trigger": trigger,
        "input": test_input,
        "expect": {
            "status": "success",
            "node_results": node_results,
        },
    }

    if webhooks:
        test_case["webhook_path"] = webhooks[0]["path"]
        test_case["method"] = webhooks[0].get("method", "POST")

    suite = {
        "workflow_file": wf_file,
        "workflow_id": workflow_id or str(wf.get("id", "")),
        "tests": [test_case],
    }

    return suite


def format_test_results(results: list[dict]) -> str:
    """Format test results as readable text.

    Test Results: 2/3 passed

    ✓ test name
    ✗ test name
      Expected: success, Got: error
    """
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    lines: list[str] = [f"Test Results: {passed}/{total} passed", ""]

    for r in results:
        if r["passed"]:
            lines.append(f"✓ {r['name']}")
        else:
            lines.append(f"✗ {r['name']}")
            if r.get("details"):
                for detail_line in r["details"].split("\n"):
                    lines.append(f"  {detail_line}")

    return "\n".join(lines)
