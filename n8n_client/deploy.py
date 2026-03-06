"""Smart deploy — validates, resolves credentials, handles dependencies, deploys."""

from __future__ import annotations

import json
import re

from n8n_client.client import N8nClient
from n8n_client.credentials import (
    apply_resolved_credentials,
    collect_credentials_from_workflows,
    resolve_credentials,
)
from n8n_client.validator import (
    ValidationIssue,
    extract_required_credentials,
    extract_sub_workflows,
    extract_trigger_type,
    extract_webhook_paths,
    sanitize_workflow,
    validate_workflow,
)


class DeployReport:
    """Structured report of a deploy attempt."""

    def __init__(self):
        self.validation_issues: list[ValidationIssue] = []
        self.sanitize_changes: list[str] = []
        self.credential_resolutions: list[dict] = []
        self.sub_workflow_deps: list[dict] = []
        self.webhook_urls: list[str] = []
        self.deployed_workflow_id: str | None = None
        self.errors: list[str] = []
        self.blocked: bool = False
        self.block_reason: str = ""
        self.dry_run: bool = False
        self.final_json: dict | None = None
        self.rollback_available: bool = False
        self.rollback_wf_name: str = ""

    def has_errors(self) -> bool:
        return bool(self.errors) or self.blocked

    def summary(self) -> str:
        lines: list[str] = []

        if self.blocked:
            lines.append(f"BLOCKED: {self.block_reason}")
            return "\n".join(lines)

        # Validation
        errors = [i for i in self.validation_issues if i.level == "error"]
        warnings = [i for i in self.validation_issues if i.level == "warning"]
        if errors:
            lines.append(f"Validation: {len(errors)} errors (auto-fixed)")
        if warnings:
            lines.append(f"Validation: {len(warnings)} warnings")
            for w in warnings:
                lines.append(f"  - {w}")

        # Sanitization
        if self.sanitize_changes:
            lines.append(f"Auto-fixed: {len(self.sanitize_changes)} issues")

        # Credentials
        resolved = [r for r in self.credential_resolutions if r["status"] == "resolved"]
        missing = [r for r in self.credential_resolutions if r["status"] == "missing"]
        multiple = [r for r in self.credential_resolutions if r["status"] == "multiple"]
        if resolved:
            lines.append(f"Credentials: {len(resolved)} auto-resolved")
        if missing:
            lines.append(f"Credentials: {len(missing)} MISSING (setup required)")
            for m in missing:
                guide = m.get("setup_guide", {})
                lines.append(f"  - {m['type']} ({guide.get('display_name', '')})")
                for step in guide.get("setup_steps", []):
                    lines.append(f"    {step}")
        if multiple:
            lines.append(f"Credentials: {len(multiple)} need user selection")
            for m in multiple:
                lines.append(f"  - {m['type']}: {len(m['candidates'])} candidates")
                for c in m["candidates"]:
                    lines.append(f"    [{c['id']}] {c['name']}")

        # Sub-workflows
        if self.sub_workflow_deps:
            lines.append(f"Sub-workflows: {len(self.sub_workflow_deps)} dependencies detected")
            for dep in self.sub_workflow_deps:
                lines.append(f"  - {dep['node_name']}: {dep['sub_workflow_ref']}")

        # Webhook URLs
        if self.webhook_urls:
            lines.append("Webhook URLs:")
            for url in self.webhook_urls:
                lines.append(f"  - {url}")

        # Result
        if self.dry_run:
            lines.append("\n[DRY RUN] Deploy skipped.")
        elif self.deployed_workflow_id:
            lines.append(f"\nDeployed: workflow ID = {self.deployed_workflow_id}")
        elif self.errors:
            lines.append(f"\nDeploy FAILED:")
            for e in self.errors:
                lines.append(f"  - {e}")
            if self.rollback_available:
                lines.append(f"\nRollback available: n8n dev rollback <workflow_id> {self.rollback_wf_name}")

        return "\n".join(lines) if lines else "No issues found."


def preflight_check(
    client: N8nClient,
    wf: dict,
) -> DeployReport:
    """Run all pre-deploy checks without actually deploying.

    Validates, resolves credentials, checks sub-workflow deps.
    """
    report = DeployReport()

    # 1. Validate
    report.validation_issues = validate_workflow(wf)

    # 2. Sanitize
    wf_fixed, changes = sanitize_workflow(wf)
    report.sanitize_changes = changes

    # 3. Credential resolution
    required_creds = extract_required_credentials(wf_fixed)
    if required_creds:
        available = collect_credentials_from_workflows(client)
        report.credential_resolutions = resolve_credentials(available, required_creds)

        missing = [r for r in report.credential_resolutions if r["status"] == "missing"]
        multiple = [r for r in report.credential_resolutions if r["status"] == "multiple"]
        if missing:
            report.blocked = True
            cred_names = [m["type"] for m in missing]
            report.block_reason = (
                f"Missing credentials: {', '.join(cred_names)}. "
                "n8n 上でこれらのクレデンシャルを作成してから再度デプロイしてください。"
            )
        elif multiple:
            report.blocked = True
            report.block_reason = (
                "複数候補のクレデンシャルがあります。ユーザーに選択を確認してください。"
            )

    # 4. Sub-workflow deps
    report.sub_workflow_deps = extract_sub_workflows(wf_fixed)

    # 5. Webhook URLs (preview)
    name, info = None, None
    try:
        from n8n_client.config import ConfigManager
        cfg = ConfigManager()
        active = cfg.get_active_client()
        if active:
            name, info = active
    except Exception:
        pass

    webhooks = extract_webhook_paths(wf_fixed)
    if webhooks and info:
        base = info["base_url"].rstrip("/")
        for wh in webhooks:
            report.webhook_urls.append(f"{base}/webhook-test/{wh['path']} ({wh['method']})")

    return report


def smart_deploy(
    client: N8nClient,
    wf: dict,
    *,
    project_id: str | None = None,
    skip_validation: bool = False,
    credential_selections: dict[str, str] | None = None,
    dry_run: bool = False,
) -> DeployReport:
    """Full deploy pipeline: validate → resolve credentials → deploy.

    Args:
        client: N8nClient instance
        wf: Workflow JSON dict
        project_id: Target project (None = personal folder)
        skip_validation: Skip validation step
        credential_selections: Manual credential selections { cred_type: cred_id }
        dry_run: If True, skip actual deploy and store final JSON in report
    """
    report = DeployReport()

    # 1. Validate & sanitize
    if not skip_validation:
        report.validation_issues = validate_workflow(wf)

    wf_fixed, changes = sanitize_workflow(wf)
    report.sanitize_changes = changes

    # 2. Credential resolution
    required_creds = extract_required_credentials(wf_fixed)
    if required_creds:
        available = collect_credentials_from_workflows(client)
        resolutions = resolve_credentials(available, required_creds)

        # Apply manual selections
        if credential_selections:
            for res in resolutions:
                if res["type"] in credential_selections:
                    selected_id = credential_selections[res["type"]]
                    # Find the name from candidates
                    all_creds = available.get(res["type"], [])
                    selected_name = next(
                        (c["name"] for c in all_creds if c["id"] == selected_id),
                        res["type"],
                    )
                    res["status"] = "resolved"
                    res["resolved_id"] = selected_id
                    res["resolved_name"] = selected_name

        report.credential_resolutions = resolutions

        # Block if unresolved
        missing = [r for r in resolutions if r["status"] == "missing"]
        multiple = [r for r in resolutions if r["status"] == "multiple"]
        if missing:
            report.blocked = True
            cred_names = [m["type"] for m in missing]
            report.block_reason = (
                f"Missing credentials: {', '.join(cred_names)}. "
                "n8n 上でクレデンシャルを作成してから再度デプロイしてください。"
            )
            return report
        if multiple:
            report.blocked = True
            report.block_reason = (
                "複数候補のクレデンシャルがあります。credential_selections で指定してください。"
            )
            return report

        # Apply resolved credentials
        wf_fixed = apply_resolved_credentials(wf_fixed, resolutions)

    # 3. Sub-workflow dependencies
    sub_wfs = extract_sub_workflows(wf_fixed)
    report.sub_workflow_deps = sub_wfs
    if sub_wfs:
        # Check if sub-workflows exist on the instance
        for dep in sub_wfs:
            ref = dep.get("sub_workflow_ref")
            if isinstance(ref, dict):
                sub_id = ref.get("value") or ref.get("id")
            else:
                sub_id = ref
            if sub_id:
                try:
                    client.get_workflow(str(sub_id))
                except Exception:
                    report.errors.append(
                        f"Sub-workflow '{dep['node_name']}' references ID '{sub_id}' "
                        f"which does not exist on the target instance."
                    )

    if report.errors:
        return report

    # 4. Deploy (or dry-run)
    if dry_run:
        report.dry_run = True
        report.final_json = wf_fixed
    else:
        try:
            result = client.create_workflow(wf_fixed, project_id=project_id)
            report.deployed_workflow_id = str(result.get("id", ""))
        except Exception as e:
            report.errors.append(f"Deploy failed: {e}")
            # Check if rollback is available from local versions
            from n8n_client.versioning import list_versions
            from n8n_client.sync import workflow_filename
            wf_name = workflow_filename(wf_fixed).replace(".json", "")
            if list_versions(wf_name):
                report.rollback_available = True
                report.rollback_wf_name = wf_name
            return report

    # 5. Webhook URLs
    webhooks = extract_webhook_paths(wf_fixed)
    if webhooks:
        try:
            from n8n_client.config import ConfigManager
            cfg = ConfigManager()
            active = cfg.get_active_client()
            if active:
                _, info = active
                base = info["base_url"].rstrip("/")
                for wh in webhooks:
                    report.webhook_urls.append(f"{base}/webhook/{wh['path']} ({wh['method']})")
                    report.webhook_urls.append(f"{base}/webhook-test/{wh['path']} ({wh['method']})")
        except Exception:
            pass

    return report


def analyze_activation_impact(wf: dict, client_name: str = "", base_url: str = "") -> dict:
    """ワークフローをactivateした場合の影響を分析する。

    Returns:
        {
            "trigger_type": str,
            "impact_description": str,
            "webhook_urls": list[str],
            "is_production": bool,
            "warnings": list[str],
        }
    """
    trigger_type = extract_trigger_type(wf) or ""
    impact_description = ""
    webhook_urls: list[str] = []
    warnings: list[str] = []

    if trigger_type == "n8n-nodes-base.webhook":
        webhooks = extract_webhook_paths(wf)
        base = base_url.rstrip("/") if base_url else ""
        for wh in webhooks:
            url = f"{base}/webhook/{wh['path']}" if base else f"/webhook/{wh['path']}"
            webhook_urls.append(url)
        if webhook_urls:
            impact_description = f"Webhook URL が外部に公開されます: {', '.join(webhook_urls)}"
        else:
            impact_description = "Webhook URL が外部に公開されます"

    elif trigger_type == "n8n-nodes-base.scheduleTrigger":
        interval_desc = _parse_schedule_interval(wf)
        impact_description = f"{interval_desc}ごとに自動実行されます"

    elif trigger_type in ("manual", "n8n-nodes-base.manualTrigger"):
        impact_description = "手動実行のみです（自動実行されません）"

    elif "Trigger" in trigger_type or "trigger" in trigger_type.lower():
        impact_description = "ポーリングによる自動実行が開始されます"

    else:
        impact_description = "自動トリガーが開始されます"

    is_production = bool(
        re.search(r"prod|production|本番|prd", client_name, re.IGNORECASE)
    )
    if is_production:
        warnings.append("本番環境です。慎重に確認してください。")

    return {
        "trigger_type": trigger_type,
        "impact_description": impact_description,
        "webhook_urls": webhook_urls,
        "is_production": is_production,
        "warnings": warnings,
    }


def _parse_schedule_interval(wf: dict) -> str:
    """scheduleTrigger ノードからスケジュール間隔を読み取る。"""
    for node in wf.get("nodes", []):
        if node.get("type") != "n8n-nodes-base.scheduleTrigger":
            continue
        params = node.get("parameters", {})
        rule = params.get("rule", {})
        interval = rule.get("interval", [{}])
        if isinstance(interval, list) and interval:
            entry = interval[0]
            field = entry.get("field", "")
            if field == "seconds":
                return f"{entry.get('secondsInterval', 30)}秒"
            elif field == "minutes":
                return f"{entry.get('minutesInterval', 5)}分"
            elif field == "hours":
                return f"{entry.get('hoursInterval', 1)}時間"
            elif field == "days":
                return f"{entry.get('daysInterval', 1)}日"
            elif field == "weeks":
                return f"{entry.get('weeksInterval', 1)}週間"
            elif field == "cronExpression":
                return f"cron({entry.get('expression', '')})"
    return "指定間隔"
