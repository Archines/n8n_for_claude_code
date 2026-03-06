"""Batch operations — bulk deploy, activate/deactivate, and cross-environment migration."""

from __future__ import annotations

import copy

from n8n_client.client import N8nClient
from n8n_client.deploy import DeployReport, smart_deploy
from n8n_client.validator import sanitize_workflow


def batch_deploy(
    client: N8nClient,
    wf_files: list[dict],
    project_id: str | None = None,
) -> list[DeployReport]:
    """Deploy multiple workflows sequentially via smart_deploy.

    Args:
        client: N8nClient instance
        wf_files: List of workflow JSON dicts
        project_id: Target project (None = personal folder)

    Returns:
        List of DeployReport, one per workflow.
    """
    reports: list[DeployReport] = []
    for wf in wf_files:
        report = smart_deploy(client, wf, project_id=project_id)
        reports.append(report)
    return reports


def batch_activate(
    client: N8nClient,
    workflow_ids: list[str],
    active: bool = True,
) -> list[dict]:
    """Bulk activate or deactivate workflows.

    Returns:
        List of result dicts: [{"id": ..., "status": "ok"/"error", "message": ...}]
    """
    results: list[dict] = []
    for wf_id in workflow_ids:
        try:
            if active:
                client.activate_workflow(wf_id)
            else:
                client.deactivate_workflow(wf_id)
            results.append({"id": wf_id, "status": "ok", "message": "activated" if active else "deactivated"})
        except Exception as e:
            results.append({"id": wf_id, "status": "error", "message": str(e)})
    return results


def _sanitize_for_migration(wf: dict) -> dict:
    """Sanitize a workflow for cross-environment migration.

    Removes IDs, credential references (invalid in target env), and server metadata.
    """
    wf = copy.deepcopy(wf)

    # Remove server-side fields
    for key in ("id", "createdAt", "updatedAt", "versionId", "active", "hash",
                "meta", "tags", "shared", "statistics", "triggerCount",
                "updatedBy", "homeProject", "usedCredentials"):
        wf.pop(key, None)

    # Sanitize nodes (fix UUIDs, remove disallowed props)
    wf, _ = sanitize_workflow(wf)

    # Strip credential id/name from all nodes (target env has different credentials)
    for node in wf.get("nodes", []):
        creds = node.get("credentials", {})
        for cred_type in list(creds.keys()):
            cred_info = creds[cred_type]
            if isinstance(cred_info, dict):
                cred_info.pop("id", None)
                cred_info.pop("name", None)

    return wf


def migrate_workflow(
    source_client: N8nClient,
    target_client: N8nClient,
    workflow_id: str,
    project_id: str | None = None,
) -> DeployReport:
    """Migrate a single workflow between environments.

    1. Fetch from source
    2. Sanitize (remove IDs, credentials)
    3. Deploy to target via smart_deploy (handles credential re-resolution)
    """
    # 1. Fetch from source
    wf = source_client.get_workflow(workflow_id)

    # 2. Sanitize for migration
    wf_clean = _sanitize_for_migration(wf)

    # 3. Deploy to target
    report = smart_deploy(target_client, wf_clean, project_id=project_id)
    return report


def migrate_all(
    source_client: N8nClient,
    target_client: N8nClient,
    project_id: str | None = None,
) -> list[DeployReport]:
    """Migrate all workflows from source to target environment."""
    reports: list[DeployReport] = []
    cursor: str | None = None

    while True:
        result = source_client.list_workflows(cursor=cursor)
        workflows = result.get("data", [])

        for wf_summary in workflows:
            wf_id = str(wf_summary["id"])
            report = migrate_workflow(source_client, target_client, wf_id, project_id=project_id)
            reports.append(report)

        next_cursor = result.get("nextCursor")
        if not next_cursor:
            break
        cursor = next_cursor

    return reports
