"""Click CLI for n8n API — all 59 endpoints."""

from __future__ import annotations

import json
import sys

import click

from n8n_client.client import N8nClient
from n8n_client.config import ConfigManager

_cfg = ConfigManager()


def _output(data):
    """Pretty-print JSON response."""
    if data is None:
        click.echo("(no content)")
        return
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _get_client() -> N8nClient:
    active = _cfg.get_active_client()
    if not active:
        click.echo("No active client. Run: n8n config add", err=True)
        sys.exit(1)
    name, info = active
    return N8nClient(info["base_url"], info["api_key"])


def _load_json_arg(json_str_or_file: str) -> dict | list:
    """Parse a JSON string or read from a file path."""
    if json_str_or_file.startswith("@"):
        with open(json_str_or_file[1:]) as f:
            return json.load(f)
    return json.loads(json_str_or_file)


# ════════════════════════════════════════════════════════════
# Root
# ════════════════════════════════════════════════════════════

@click.group()
def cli():
    """n8n API client for Claude Code."""
    pass


# ════════════════════════════════════════════════════════════
# Config
# ════════════════════════════════════════════════════════════

@cli.group()
def config():
    """Manage n8n client configurations."""
    pass


@config.command("list")
def config_list():
    """List all configured clients."""
    clients = _cfg.list_clients()
    if not clients:
        click.echo("No clients configured.")
        return
    active = _cfg.get_active_client_name()
    for name, info in clients.items():
        marker = " (active)" if name == active else ""
        desc = info.get("description", "")
        click.echo(f"  {name}{marker} — {info['base_url']} [{desc}]")


@config.command("add")
@click.argument("name")
@click.argument("base_url")
@click.argument("api_key")
@click.option("--description", "-d", default="", help="Description of this client")
def config_add(name, base_url, api_key, description):
    """Add a new client configuration."""
    _cfg.add_client(name, base_url, api_key, description)
    click.echo(f"Client '{name}' added.")


@config.command("remove")
@click.argument("name")
def config_remove(name):
    """Remove a client configuration."""
    _cfg.remove_client(name)
    click.echo(f"Client '{name}' removed.")


@config.command("switch")
@click.argument("name")
def config_switch(name):
    """Switch to a different client."""
    _cfg.switch_client(name)
    click.echo(f"Switched to '{name}'.")


@config.command("active")
def config_active():
    """Show the active client."""
    active = _cfg.get_active_client()
    if not active:
        click.echo("No active client.")
        return
    name, info = active
    click.echo(f"{name} — {info['base_url']} [{info.get('description', '')}]")


@config.command("test")
def config_test():
    """Test connection to the active client."""
    client = _get_client()
    try:
        client.list_workflows(limit=1)
        name, info = _cfg.get_active_client()
        click.echo(f"Connection successful: {name} ({info['base_url']})")
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        sys.exit(1)


# ════════════════════════════════════════════════════════════
# Audit
# ════════════════════════════════════════════════════════════

@cli.group()
def audit():
    """Security audit operations."""
    pass


@audit.command("generate")
@click.option("--categories", "-c", help="Comma-separated: credentials,database,nodes,filesystem,instance")
@click.option("--days-abandoned", type=int, help="Days to consider a workflow abandoned")
def audit_generate(categories, days_abandoned):
    """Generate a security audit report."""
    cats = categories.split(",") if categories else None
    _output(_get_client().generate_audit(categories=cats, days_abandoned_workflow=days_abandoned))


# ════════════════════════════════════════════════════════════
# Credentials
# ════════════════════════════════════════════════════════════

@cli.group()
def credential():
    """Credential operations."""
    pass


@credential.command("list")
@click.option("--limit", type=int)
@click.option("--cursor")
def credential_list(limit, cursor):
    """List all credentials."""
    _output(_get_client().list_credentials(limit=limit, cursor=cursor))


@credential.command("create")
@click.argument("json_data")
def credential_create(json_data):
    """Create a credential. Pass JSON string or @file.json."""
    _output(_get_client().create_credential(_load_json_arg(json_data)))


@credential.command("update")
@click.argument("credential_id")
@click.argument("json_data")
def credential_update(credential_id, json_data):
    """Update a credential."""
    _output(_get_client().update_credential(credential_id, _load_json_arg(json_data)))


@credential.command("delete")
@click.argument("credential_id")
def credential_delete(credential_id):
    """Delete a credential."""
    _output(_get_client().delete_credential(credential_id))


@credential.command("schema")
@click.argument("credential_type")
def credential_schema(credential_type):
    """Get the JSON schema for a credential type."""
    _output(_get_client().get_credential_schema(credential_type))


@credential.command("transfer")
@click.argument("credential_id")
@click.argument("destination_project_id")
def credential_transfer(credential_id, destination_project_id):
    """Transfer a credential to another project."""
    _output(_get_client().transfer_credential(credential_id, destination_project_id))


# ════════════════════════════════════════════════════════════
# Executions
# ════════════════════════════════════════════════════════════

@cli.group()
def execution():
    """Execution operations."""
    pass


@execution.command("list")
@click.option("--workflow-id", "-w")
@click.option("--project-id", "-p")
@click.option("--status", type=click.Choice(["canceled", "error", "running", "success", "waiting"]))
@click.option("--include-data", is_flag=True)
@click.option("--limit", type=int)
@click.option("--cursor")
def execution_list(workflow_id, project_id, status, include_data, limit, cursor):
    """List executions."""
    _output(_get_client().list_executions(
        workflow_id=workflow_id, project_id=project_id, status=status,
        include_data=include_data, limit=limit, cursor=cursor,
    ))


@execution.command("get")
@click.argument("execution_id")
@click.option("--include-data", is_flag=True)
def execution_get(execution_id, include_data):
    """Get a single execution."""
    _output(_get_client().get_execution(execution_id, include_data=include_data))


@execution.command("delete")
@click.argument("execution_id")
def execution_delete(execution_id):
    """Delete an execution."""
    _output(_get_client().delete_execution(execution_id))


@execution.command("retry")
@click.argument("execution_id")
@click.option("--load-workflow", is_flag=True, help="Use latest workflow version")
def execution_retry(execution_id, load_workflow):
    """Retry a failed execution."""
    _output(_get_client().retry_execution(execution_id, load_workflow=load_workflow))


@execution.command("stop")
@click.argument("execution_id")
def execution_stop(execution_id):
    """Stop a single execution."""
    _output(_get_client().stop_execution(execution_id))


@execution.command("stop-many")
@click.argument("statuses", nargs=-1, required=True)
@click.option("--workflow-id", "-w")
@click.option("--started-after")
@click.option("--started-before")
def execution_stop_many(statuses, workflow_id, started_after, started_before):
    """Stop multiple executions by status (queued, running, waiting)."""
    _output(_get_client().stop_executions(
        list(statuses), workflow_id=workflow_id,
        started_after=started_after, started_before=started_before,
    ))


@execution.command("tags")
@click.argument("execution_id")
def execution_tags_get(execution_id):
    """Get annotation tags for an execution."""
    _output(_get_client().get_execution_tags(execution_id))


@execution.command("set-tags")
@click.argument("execution_id")
@click.argument("tag_ids", nargs=-1, required=True)
def execution_tags_set(execution_id, tag_ids):
    """Set annotation tags on an execution (replaces all)."""
    _output(_get_client().update_execution_tags(execution_id, list(tag_ids)))


# ════════════════════════════════════════════════════════════
# Workflows
# ════════════════════════════════════════════════════════════

@cli.group()
def workflow():
    """Workflow operations."""
    pass


@workflow.command("list")
@click.option("--active/--inactive", default=None)
@click.option("--tags", help="Comma-separated tag names")
@click.option("--name")
@click.option("--project-id", "-p")
@click.option("--exclude-pinned-data", is_flag=True)
@click.option("--limit", type=int)
@click.option("--cursor")
def workflow_list(active, tags, name, project_id, exclude_pinned_data, limit, cursor):
    """List workflows."""
    _output(_get_client().list_workflows(
        active=active, tags=tags, name=name, project_id=project_id,
        exclude_pinned_data=exclude_pinned_data, limit=limit, cursor=cursor,
    ))


@workflow.command("get")
@click.argument("workflow_id")
@click.option("--exclude-pinned-data", is_flag=True)
def workflow_get(workflow_id, exclude_pinned_data):
    """Get a single workflow."""
    _output(_get_client().get_workflow(workflow_id, exclude_pinned_data=exclude_pinned_data))


@workflow.command("create")
@click.argument("json_data")
@click.option("--project-id", "-p", help="Deploy to this project (omit for personal folder)")
def workflow_create(json_data, project_id):
    """Create a workflow. Pass JSON string or @file.json."""
    _output(_get_client().create_workflow(_load_json_arg(json_data), project_id=project_id))


@workflow.command("update")
@click.argument("workflow_id")
@click.argument("json_data")
def workflow_update(workflow_id, json_data):
    """Update a workflow."""
    _output(_get_client().update_workflow(workflow_id, _load_json_arg(json_data)))


@workflow.command("delete")
@click.argument("workflow_id")
def workflow_delete(workflow_id):
    """Delete a workflow."""
    _output(_get_client().delete_workflow(workflow_id))


@workflow.command("version")
@click.argument("workflow_id")
@click.argument("version_id")
def workflow_version(workflow_id, version_id):
    """Get a specific workflow version from history."""
    _output(_get_client().get_workflow_version(workflow_id, version_id))


@workflow.command("activate")
@click.argument("workflow_id")
@click.option("--version-id")
@click.option("--name")
@click.option("--description")
def workflow_activate(workflow_id, version_id, name, description):
    """Activate (publish) a workflow."""
    _output(_get_client().activate_workflow(
        workflow_id, version_id=version_id, name=name, description=description,
    ))


@workflow.command("deactivate")
@click.argument("workflow_id")
def workflow_deactivate(workflow_id):
    """Deactivate a workflow."""
    _output(_get_client().deactivate_workflow(workflow_id))


@workflow.command("transfer")
@click.argument("workflow_id")
@click.argument("destination_project_id")
def workflow_transfer(workflow_id, destination_project_id):
    """Transfer a workflow to another project."""
    _output(_get_client().transfer_workflow(workflow_id, destination_project_id))


@workflow.command("tags")
@click.argument("workflow_id")
def workflow_tags_get(workflow_id):
    """Get tags for a workflow."""
    _output(_get_client().get_workflow_tags(workflow_id))


@workflow.command("set-tags")
@click.argument("workflow_id")
@click.argument("tag_ids", nargs=-1, required=True)
def workflow_tags_set(workflow_id, tag_ids):
    """Set tags on a workflow (replaces all)."""
    _output(_get_client().update_workflow_tags(workflow_id, list(tag_ids)))


# ════════════════════════════════════════════════════════════
# Tags
# ════════════════════════════════════════════════════════════

@cli.group()
def tag():
    """Tag operations."""
    pass


@tag.command("list")
@click.option("--limit", type=int)
@click.option("--cursor")
def tag_list(limit, cursor):
    """List all tags."""
    _output(_get_client().list_tags(limit=limit, cursor=cursor))


@tag.command("get")
@click.argument("tag_id")
def tag_get(tag_id):
    """Get a single tag."""
    _output(_get_client().get_tag(tag_id))


@tag.command("create")
@click.argument("name")
def tag_create(name):
    """Create a tag."""
    _output(_get_client().create_tag(name))


@tag.command("update")
@click.argument("tag_id")
@click.argument("name")
def tag_update(tag_id, name):
    """Update a tag."""
    _output(_get_client().update_tag(tag_id, name))


@tag.command("delete")
@click.argument("tag_id")
def tag_delete(tag_id):
    """Delete a tag."""
    _output(_get_client().delete_tag(tag_id))


# ════════════════════════════════════════════════════════════
# Users
# ════════════════════════════════════════════════════════════

@cli.group()
def user():
    """User operations."""
    pass


@user.command("list")
@click.option("--include-role", is_flag=True)
@click.option("--project-id", "-p")
@click.option("--limit", type=int)
@click.option("--cursor")
def user_list(include_role, project_id, limit, cursor):
    """List all users."""
    _output(_get_client().list_users(
        include_role=include_role, project_id=project_id, limit=limit, cursor=cursor,
    ))


@user.command("get")
@click.argument("user_id_or_email")
@click.option("--include-role", is_flag=True)
def user_get(user_id_or_email, include_role):
    """Get a user by ID or email."""
    _output(_get_client().get_user(user_id_or_email, include_role=include_role))


@user.command("invite")
@click.argument("json_data")
def user_invite(json_data):
    """Invite users. Pass JSON array: [{"email":"...","role":"global:member"}]."""
    _output(_get_client().invite_users(_load_json_arg(json_data)))


@user.command("delete")
@click.argument("user_id")
def user_delete(user_id):
    """Delete a user."""
    _output(_get_client().delete_user(user_id))


@user.command("set-role")
@click.argument("user_id")
@click.argument("role")
def user_set_role(user_id, role):
    """Change a user's global role (e.g. global:member)."""
    _output(_get_client().update_user_role(user_id, role))


# ════════════════════════════════════════════════════════════
# Source Control
# ════════════════════════════════════════════════════════════

@cli.group("source-control")
def source_control():
    """Source control operations."""
    pass


@source_control.command("pull")
@click.option("--options", help="JSON string of pull options")
def sc_pull(options):
    """Pull from remote repository."""
    opts = json.loads(options) if options else None
    _output(_get_client().source_control_pull(opts))


# ════════════════════════════════════════════════════════════
# Variables
# ════════════════════════════════════════════════════════════

@cli.group()
def variable():
    """Variable operations."""
    pass


@variable.command("list")
@click.option("--project-id", "-p")
@click.option("--state", type=click.Choice(["empty"]))
@click.option("--limit", type=int)
@click.option("--cursor")
def variable_list(project_id, state, limit, cursor):
    """List all variables."""
    _output(_get_client().list_variables(
        project_id=project_id, state=state, limit=limit, cursor=cursor,
    ))


@variable.command("create")
@click.argument("key")
@click.argument("value")
def variable_create(key, value):
    """Create a variable."""
    _output(_get_client().create_variable(key, value))


@variable.command("update")
@click.argument("variable_id")
@click.argument("key")
@click.argument("value")
def variable_update(variable_id, key, value):
    """Update a variable."""
    _output(_get_client().update_variable(variable_id, key, value))


@variable.command("delete")
@click.argument("variable_id")
def variable_delete(variable_id):
    """Delete a variable."""
    _output(_get_client().delete_variable(variable_id))


# ════════════════════════════════════════════════════════════
# Data Tables
# ════════════════════════════════════════════════════════════

@cli.group("data-table")
def data_table():
    """Data table operations."""
    pass


@data_table.command("list")
@click.option("--filter", "filter_", help="JSON filter string")
@click.option("--sort-by", help="e.g. name:asc")
@click.option("--limit", type=int)
@click.option("--cursor")
def dt_list(filter_, sort_by, limit, cursor):
    """List all data tables."""
    _output(_get_client().list_data_tables(
        filter_=filter_, sort_by=sort_by, limit=limit, cursor=cursor,
    ))


@data_table.command("get")
@click.argument("table_id")
def dt_get(table_id):
    """Get a data table."""
    _output(_get_client().get_data_table(table_id))


@data_table.command("create")
@click.argument("name")
@click.argument("columns_json")
def dt_create(name, columns_json):
    """Create a data table. COLUMNS_JSON: [{"name":"col","type":"string"}]."""
    _output(_get_client().create_data_table(name, json.loads(columns_json)))


@data_table.command("update")
@click.argument("table_id")
@click.argument("name")
def dt_update(table_id, name):
    """Rename a data table."""
    _output(_get_client().update_data_table(table_id, name))


@data_table.command("delete")
@click.argument("table_id")
def dt_delete(table_id):
    """Delete a data table and all its rows."""
    _output(_get_client().delete_data_table(table_id))


# ── Data Table Rows ─────────────────────────────────────────

@data_table.group("row")
def dt_row():
    """Data table row operations."""
    pass


@dt_row.command("list")
@click.argument("table_id")
@click.option("--filter", "filter_", help="JSON filter string")
@click.option("--sort-by")
@click.option("--search")
@click.option("--limit", type=int)
@click.option("--cursor")
def dt_row_list(table_id, filter_, sort_by, search, limit, cursor):
    """List rows in a data table."""
    _output(_get_client().list_data_table_rows(
        table_id, filter_=filter_, sort_by=sort_by, search=search,
        limit=limit, cursor=cursor,
    ))


@dt_row.command("insert")
@click.argument("table_id")
@click.argument("rows_json")
@click.option("--return-type", type=click.Choice(["count", "id", "all"]), default="count")
def dt_row_insert(table_id, rows_json, return_type):
    """Insert rows. ROWS_JSON: [{"col":"val"}, ...]."""
    _output(_get_client().insert_data_table_rows(
        table_id, json.loads(rows_json), return_type=return_type,
    ))


@dt_row.command("update")
@click.argument("table_id")
@click.argument("filter_json")
@click.argument("data_json")
@click.option("--return-data", is_flag=True)
@click.option("--dry-run", is_flag=True)
def dt_row_update(table_id, filter_json, data_json, return_data, dry_run):
    """Update rows by filter."""
    _output(_get_client().update_data_table_rows(
        table_id, json.loads(filter_json), json.loads(data_json),
        return_data=return_data, dry_run=dry_run,
    ))


@dt_row.command("upsert")
@click.argument("table_id")
@click.argument("filter_json")
@click.argument("data_json")
@click.option("--return-data", is_flag=True)
@click.option("--dry-run", is_flag=True)
def dt_row_upsert(table_id, filter_json, data_json, return_data, dry_run):
    """Upsert a row."""
    _output(_get_client().upsert_data_table_row(
        table_id, json.loads(filter_json), json.loads(data_json),
        return_data=return_data, dry_run=dry_run,
    ))


@dt_row.command("delete")
@click.argument("table_id")
@click.argument("filter_json")
@click.option("--return-data", is_flag=True)
@click.option("--dry-run", is_flag=True)
def dt_row_delete(table_id, filter_json, return_data, dry_run):
    """Delete rows by filter."""
    _output(_get_client().delete_data_table_rows(
        table_id, filter_json, return_data=return_data, dry_run=dry_run,
    ))


# ════════════════════════════════════════════════════════════
# Projects
# ════════════════════════════════════════════════════════════

@cli.group()
def project():
    """Project operations."""
    pass


@project.command("list")
@click.option("--limit", type=int)
@click.option("--cursor")
def project_list(limit, cursor):
    """List all projects."""
    _output(_get_client().list_projects(limit=limit, cursor=cursor))


@project.command("create")
@click.argument("name")
def project_create(name):
    """Create a project."""
    _output(_get_client().create_project(name))


@project.command("update")
@click.argument("project_id")
@click.argument("name")
def project_update(project_id, name):
    """Rename a project."""
    _output(_get_client().update_project(project_id, name))


@project.command("delete")
@click.argument("project_id")
def project_delete(project_id):
    """Delete a project."""
    _output(_get_client().delete_project(project_id))


@project.command("users")
@click.argument("project_id")
@click.option("--limit", type=int)
@click.option("--cursor")
def project_users_list(project_id, limit, cursor):
    """List members of a project."""
    _output(_get_client().list_project_users(project_id, limit=limit, cursor=cursor))


@project.command("add-user")
@click.argument("project_id")
@click.argument("relations_json")
def project_add_users(project_id, relations_json):
    """Add users to a project. JSON: [{"userId":"...","role":"project:viewer"}]."""
    _output(_get_client().add_project_users(project_id, json.loads(relations_json)))


@project.command("set-user-role")
@click.argument("project_id")
@click.argument("user_id")
@click.argument("role")
def project_set_user_role(project_id, user_id, role):
    """Change a user's role in a project."""
    _output(_get_client().update_project_user_role(project_id, user_id, role))


@project.command("remove-user")
@click.argument("project_id")
@click.argument("user_id")
def project_remove_user(project_id, user_id):
    """Remove a user from a project."""
    _output(_get_client().remove_project_user(project_id, user_id))


# ════════════════════════════════════════════════════════════
# Dev — development helpers (validate, credentials, test, deploy)
# ════════════════════════════════════════════════════════════

@cli.group()
def dev():
    """Development helpers: validate, credentials, test, deploy."""
    pass


@dev.command("validate")
@click.argument("json_data")
def dev_validate(json_data):
    """Validate a workflow JSON for Cloud compatibility."""
    from n8n_client.validator import validate_workflow, sanitize_workflow
    wf = _load_json_arg(json_data)
    issues = validate_workflow(wf)
    if not issues:
        click.echo("No issues found.")
        return
    for issue in issues:
        click.echo(str(issue))
    # Show what would be auto-fixed
    _, changes = sanitize_workflow(wf)
    if changes:
        click.echo(f"\nAuto-fixable ({len(changes)}):")
        for c in changes:
            click.echo(f"  - {c}")


@dev.command("sanitize")
@click.argument("json_data")
@click.option("--output", "-o", help="Output file path (default: stdout)")
def dev_sanitize(json_data, output):
    """Auto-fix Cloud compatibility issues and output sanitized JSON."""
    from n8n_client.validator import sanitize_workflow
    wf = _load_json_arg(json_data)
    fixed, changes = sanitize_workflow(wf)
    if changes:
        for c in changes:
            click.echo(f"Fixed: {c}", err=True)
    else:
        click.echo("No changes needed.", err=True)
    result = json.dumps(fixed, indent=2, ensure_ascii=False)
    if output:
        with open(output, "w") as f:
            f.write(result)
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(result)


@dev.command("scan-credentials")
def dev_scan_credentials():
    """Scan all workflows on the instance to discover available credentials."""
    from n8n_client.credentials import collect_credentials_from_workflows
    client = _get_client()
    click.echo("Scanning workflows for credentials...", err=True)
    cred_map = collect_credentials_from_workflows(client)
    if not cred_map:
        click.echo("No credentials found.")
        return
    for cred_type, entries in sorted(cred_map.items()):
        click.echo(f"\n{cred_type}:")
        for entry in entries:
            wf_count = len(entry["used_in_workflows"])
            click.echo(f"  [{entry['id']}] {entry['name']} (used in {wf_count} workflow(s))")


@dev.command("resolve-credentials")
@click.argument("json_data")
def dev_resolve_credentials(json_data):
    """Check what credentials a workflow needs and resolve them."""
    from n8n_client.credentials import collect_credentials_from_workflows, resolve_credentials
    from n8n_client.validator import extract_required_credentials
    wf = _load_json_arg(json_data)
    required = extract_required_credentials(wf)
    if not required:
        click.echo("This workflow does not require any credentials.")
        return
    click.echo(f"Required credentials: {len(required)}", err=True)
    client = _get_client()
    click.echo("Scanning instance for available credentials...", err=True)
    available = collect_credentials_from_workflows(client)
    resolutions = resolve_credentials(available, required)
    _output(resolutions)


@dev.command("credential-guide")
@click.argument("credential_type")
def dev_credential_guide(credential_type):
    """Show setup instructions for a credential type."""
    from n8n_client.credentials import get_credential_setup_guide
    guide = get_credential_setup_guide(credential_type)
    click.echo(f"\n{guide['display_name']}")
    click.echo("-" * 40)
    for i, step in enumerate(guide["setup_steps"], 1):
        click.echo(f"  {i}. {step}")


@dev.command("test-data")
@click.argument("json_data")
def dev_test_data(json_data):
    """Generate sample test data for a workflow."""
    from n8n_client.testing import generate_test_data
    wf = _load_json_arg(json_data)
    result = generate_test_data(wf)
    click.echo(result["instructions"], err=True)
    if result.get("webhook_info"):
        click.echo(f"Webhook: {result['webhook_info']['method']} /{result['webhook_info']['path']}", err=True)
    click.echo("\nGenerated test data:")
    _output(result["test_data"])


@dev.command("webhook-test")
@click.argument("json_data")
@click.option("--data", "-d", help="Custom test data (JSON string or @file)")
@click.option("--wait/--no-wait", default=True, help="Wait for execution result")
def dev_webhook_test(json_data, data, wait):
    """Send test data to a workflow's webhook and check the result."""
    from n8n_client.testing import (
        generate_test_data, send_webhook_test, wait_for_execution,
        analyze_execution, format_execution_summary,
    )
    from n8n_client.validator import extract_webhook_paths

    wf = _load_json_arg(json_data)
    webhooks = extract_webhook_paths(wf)
    if not webhooks:
        click.echo("No webhook trigger found in this workflow.", err=True)
        sys.exit(1)

    wh = webhooks[0]

    # Get test data
    if data:
        test_data = _load_json_arg(data)
    else:
        gen = generate_test_data(wf)
        test_data = gen["test_data"]
        click.echo("Using auto-generated test data:", err=True)
        click.echo(json.dumps(test_data, indent=2, ensure_ascii=False), err=True)

    # Get base URL
    active = _cfg.get_active_client()
    if not active:
        click.echo("No active client.", err=True)
        sys.exit(1)
    _, info = active
    base_url = info["base_url"]

    # Send
    click.echo(f"\nSending {wh['method']} to /webhook-test/{wh['path']}...", err=True)
    result = send_webhook_test(base_url, wh["path"], test_data, method=wh["method"])
    click.echo(f"Response: {result['status_code']}", err=True)
    _output(result)

    # Wait for execution
    if wait and result["success"]:
        # Need workflow ID — try to find from wf JSON
        wf_id = wf.get("id")
        if wf_id:
            click.echo(f"\nWaiting for execution result (workflow {wf_id})...", err=True)
            client = _get_client()
            execution = wait_for_execution(client, str(wf_id), timeout=60)
            if execution:
                analysis = analyze_execution(execution)
                click.echo(f"\n{format_execution_summary(analysis)}")
            else:
                click.echo("Timeout: no execution result received.", err=True)


@dev.command("check-execution")
@click.argument("execution_id")
def dev_check_execution(execution_id):
    """Analyze an execution result."""
    from n8n_client.testing import analyze_execution, format_execution_summary
    client = _get_client()
    execution = client.get_execution(execution_id, include_data=True)
    analysis = analyze_execution(execution)
    click.echo(format_execution_summary(analysis))


@dev.command("pull")
@click.argument("workflow_id")
@click.option("--output-dir", "-o", default="workflows", help="Output directory")
def dev_pull(workflow_id, output_dir):
    """Pull a remote workflow and save locally."""
    from n8n_client.sync import pull_workflow
    client = _get_client()
    path = pull_workflow(client, workflow_id, output_dir)
    click.echo(f"Saved: {path}")


@dev.command("pull-all")
@click.option("--project-id", "-p", help="Filter by project ID")
@click.option("--output-dir", "-o", default="workflows", help="Output directory")
def dev_pull_all(project_id, output_dir):
    """Pull all workflows and save locally."""
    from n8n_client.sync import pull_all_workflows
    client = _get_client()
    click.echo("Pulling all workflows...", err=True)
    paths = pull_all_workflows(client, output_dir, project_id=project_id)
    for p in paths:
        click.echo(f"Saved: {p}")
    click.echo(f"\n{len(paths)} workflow(s) saved to {output_dir}/", err=True)


@dev.command("diff")
@click.argument("workflow_id")
@click.argument("local_json")
def dev_diff(workflow_id, local_json):
    """Show diff between remote workflow and local file."""
    from n8n_client.sync import diff_workflow, format_diff
    client = _get_client()
    diff = diff_workflow(client, workflow_id, local_json)
    click.echo(format_diff(diff))


@dev.command("edit")
@click.argument("workflow_id")
@click.option("--output-dir", "-o", default="workflows", help="Output directory")
def dev_edit(workflow_id, output_dir):
    """Pull a workflow for editing, then push back with `n8n dev push`."""
    from n8n_client.sync import clean_workflow_for_local
    import os

    client = _get_client()
    wf = client.get_workflow(workflow_id)
    cleaned = clean_workflow_for_local(wf)

    os.makedirs(output_dir, exist_ok=True)
    filename = f"edit-{workflow_id}.json"
    path = os.path.join(output_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
        f.write("\n")

    click.echo(f"Saved: {path}")
    click.echo(f"\nEdit the file, then push with:")
    click.echo(f"  n8n dev push {workflow_id} @{path}")


@dev.command("push")
@click.argument("workflow_id")
@click.argument("local_json")
@click.option("--force", is_flag=True, help="Push without confirmation")
def dev_push(workflow_id, local_json, force):
    """Push local workflow to remote (with diff confirmation)."""
    from n8n_client.sync import diff_workflow, format_diff, push_workflow
    client = _get_client()

    diff = diff_workflow(client, workflow_id, local_json)
    if diff["summary"] == "no changes":
        click.echo("No changes to push.")
        return

    click.echo(format_diff(diff))
    if not force:
        if not click.confirm("\nPush these changes?"):
            click.echo("Aborted.")
            return

    push_workflow(client, workflow_id, local_json)
    click.echo(f"Pushed to workflow {workflow_id}.")


@dev.command("preflight")
@click.argument("json_data")
def dev_preflight(json_data):
    """Run all pre-deploy checks (validate, credentials, sub-workflows)."""
    from n8n_client.deploy import preflight_check
    wf = _load_json_arg(json_data)
    client = _get_client()
    click.echo("Running preflight checks...", err=True)
    report = preflight_check(client, wf)
    click.echo(report.summary())


@dev.command("activate")
@click.argument("workflow_id")
def dev_activate(workflow_id):
    """Activate a workflow with safety analysis."""
    from n8n_client.deploy import analyze_activation_impact
    client = _get_client()
    active = _cfg.get_active_client()
    client_name = active[0] if active else ""
    base_url = active[1]["base_url"] if active else ""

    wf = client.get_workflow(workflow_id)
    impact = analyze_activation_impact(wf, client_name=client_name, base_url=base_url)

    click.echo(f"Trigger: {impact['trigger_type'] or 'unknown'}")
    click.echo(f"Impact:  {impact['impact_description']}")
    for w in impact["warnings"]:
        click.echo(f"WARNING: {w}", err=True)

    client.activate_workflow(workflow_id)
    click.echo(f"\nWorkflow {workflow_id} activated.")


@dev.command("deploy")
@click.argument("json_data")
@click.option("--project-id", "-p", help="Target project ID")
@click.option("--credential", "-c", multiple=True, help="Manual credential: type=id")
@click.option("--activate", is_flag=True, help="Activate after deploy")
@click.option("--dry-run", is_flag=True, help="Validate and resolve without deploying")
def dev_deploy(json_data, project_id, credential, activate, dry_run):
    """Smart deploy: validate → resolve credentials → deploy."""
    from n8n_client.deploy import smart_deploy, analyze_activation_impact
    wf = _load_json_arg(json_data)
    client = _get_client()

    # Parse manual credential selections
    cred_selections = {}
    for c in credential:
        if "=" in c:
            ctype, cid = c.split("=", 1)
            cred_selections[ctype] = cid

    click.echo("Deploying..." if not dry_run else "Dry run...", err=True)
    report = smart_deploy(
        client, wf,
        project_id=project_id,
        credential_selections=cred_selections or None,
        dry_run=dry_run,
    )
    click.echo(report.summary())

    if dry_run and report.final_json:
        nodes = report.final_json.get("nodes", [])
        connections = report.final_json.get("connections", {})
        node_names = [n.get("name", "?") for n in nodes]
        cred_types = set()
        for n in nodes:
            for cred in n.get("credentials", {}).values():
                cred_types.add(cred.get("name", cred.get("id", "?")))
        conn_count = sum(
            len(outs)
            for dest in connections.values()
            for outs in dest.get("main", [])
        )
        click.echo(f"\nFinal workflow summary:")
        click.echo(f"  Nodes: {len(nodes)}")
        click.echo(f"  Node names: {', '.join(node_names)}")
        if cred_types:
            click.echo(f"  Credentials: {', '.join(sorted(cred_types))}")
        click.echo(f"  Connections: {conn_count}")
        return

    if report.deployed_workflow_id and activate:
        active = _cfg.get_active_client()
        client_name = active[0] if active else ""
        base_url = active[1]["base_url"] if active else ""

        deployed_wf = client.get_workflow(report.deployed_workflow_id)
        impact = analyze_activation_impact(deployed_wf, client_name=client_name, base_url=base_url)

        click.echo(f"\nTrigger: {impact['trigger_type'] or 'unknown'}")
        click.echo(f"Impact:  {impact['impact_description']}")
        for w in impact["warnings"]:
            click.echo(f"WARNING: {w}", err=True)

        click.echo(f"\nActivating workflow {report.deployed_workflow_id}...", err=True)
        client.activate_workflow(report.deployed_workflow_id)
        click.echo("Activated.")


@dev.command("watch")
@click.argument("workflow_id")
@click.option("--interval", "-i", type=int, default=5, help="Poll interval in seconds")
def dev_watch(workflow_id, interval):
    """Watch executions of a workflow in real-time."""
    from n8n_client.monitoring import watch_executions
    client = _get_client()
    click.echo(f"Watching workflow {workflow_id} (interval={interval}s) — Ctrl+C to stop", err=True)
    watch_executions(client, workflow_id, interval=interval, callback=click.echo)
    click.echo("\nStopped.", err=True)


@dev.command("versions")
@click.argument("wf_name_or_file")
@click.option("--dir", "base_dir", default="workflows", help="Workflows directory")
def dev_versions(wf_name_or_file, base_dir):
    """List local versions of a workflow."""
    from n8n_client.versioning import list_versions
    wf_name = wf_name_or_file.replace(".json", "").split("/")[-1]
    versions = list_versions(wf_name, base_dir)
    if not versions:
        click.echo(f"No versions found for '{wf_name}'.")
        return
    for v in versions:
        click.echo(f"  v{v['number']:03d}  {v['timestamp']}  [{v['operation']}]  {v.get('source_id', '')}")


@dev.command("version-show")
@click.argument("wf_name")
@click.argument("version", type=int)
@click.option("--dir", "base_dir", default="workflows", help="Workflows directory")
def dev_version_show(wf_name, version, base_dir):
    """Show a specific version of a workflow."""
    from n8n_client.versioning import get_version
    wf_name = wf_name.replace(".json", "").split("/")[-1]
    try:
        data = get_version(wf_name, version, base_dir)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    _output(data)


@dev.command("rollback")
@click.argument("workflow_id")
@click.argument("wf_name")
@click.option("--version", "-v", type=int, default=None, help="Target version (default: previous)")
@click.option("--dir", "base_dir", default="workflows", help="Workflows directory")
def dev_rollback(workflow_id, wf_name, version, base_dir):
    """Rollback a workflow to a previous local version."""
    from n8n_client.versioning import rollback_workflow
    wf_name = wf_name.replace(".json", "").split("/")[-1]
    client = _get_client()
    try:
        result = rollback_workflow(client, wf_name, workflow_id, version_number=version, base_dir=base_dir)
    except (ValueError, FileNotFoundError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    click.echo(f"Rolled back to version {result['rolled_back_to']} (new version: v{result['new_version']:03d})")
    click.echo(f"Remote workflow {workflow_id} updated.")


@dev.command("var-pull")
@click.option("--output-dir", "-o", default="workflows/variables", help="Output directory")
def dev_var_pull(output_dir):
    """Pull variables from remote and save locally."""
    from n8n_client.var_sync import pull_variables
    client = _get_client()
    active = _cfg.get_active_client()
    client_name = active[0] if active else "default"
    result = pull_variables(client, client_name, output_dir)
    click.echo(f"Saved {len(result['variables'])} variable(s) to {output_dir}/{client_name}.vars.json")


@dev.command("var-push")
@click.argument("file_path")
def dev_var_push(file_path):
    """Push variables from local file to remote. Use @file syntax."""
    from n8n_client.var_sync import push_variables
    client = _get_client()
    path = file_path[1:] if file_path.startswith("@") else file_path
    result = push_variables(client, path)
    if result["created"]:
        click.echo(f"Created: {', '.join(result['created'])}")
    if result["updated"]:
        click.echo(f"Updated: {', '.join(result['updated'])}")
    if result["delete_candidates"]:
        click.echo(f"Delete candidates (remote only): {', '.join(result['delete_candidates'])}")
    if not result["created"] and not result["updated"] and not result["delete_candidates"]:
        click.echo("No changes.")


@dev.command("var-diff")
@click.argument("file_path", required=False, default=None)
def dev_var_diff(file_path):
    """Show diff between local variables file and remote."""
    from n8n_client.var_sync import diff_variables, format_diff
    client = _get_client()
    path = None
    if file_path:
        path = file_path[1:] if file_path.startswith("@") else file_path
    active = _cfg.get_active_client()
    client_name = active[0] if active else "default"
    diff = diff_variables(client, input_path=path, client_name=client_name)
    click.echo(format_diff(diff))


@dev.command("var-export")
@click.option("--format", "fmt", type=click.Choice(["env", "json"]), default="env", help="Output format")
def dev_var_export(fmt):
    """Export variables from remote."""
    from n8n_client.var_sync import export_env, _get_all_variables
    client = _get_client()
    if fmt == "env":
        click.echo(export_env(client))
    else:
        variables = _get_all_variables(client)
        _output(variables)


@dev.command("deps")
@click.argument("workflow_id")
def dev_deps(workflow_id):
    """Show dependency tree and upstream references for a workflow."""
    from n8n_client.dependencies import (
        build_dependency_tree, find_dependents,
        format_dependency_tree, format_dependency_summary,
    )
    client = _get_client()
    click.echo("Building dependency tree...", err=True)
    tree = build_dependency_tree(client, workflow_id)
    click.echo("Scanning for upstream references...", err=True)
    upstream = find_dependents(client, workflow_id)
    click.echo("")
    click.echo(format_dependency_summary(workflow_id, tree["name"], upstream, tree))
    if tree.get("children"):
        click.echo("")
        click.echo("Full dependency tree:")
        click.echo(format_dependency_tree(tree))


@dev.command("test-run")
@click.argument("test_file")
def dev_test_run(test_file):
    """Run a test suite. Pass @workflows/tests/<file>.test.json."""
    from n8n_client.test_runner import load_test_suite, run_test_suite, format_test_results
    file_path = test_file[1:] if test_file.startswith("@") else test_file
    suite = load_test_suite(file_path)
    client = _get_client()
    active = _cfg.get_active_client()
    base_url = active[1]["base_url"] if active else ""
    click.echo("Running tests...", err=True)
    results = run_test_suite(client, base_url, suite)
    click.echo(format_test_results(results))


@dev.command("test-create")
@click.argument("json_data")
@click.option("--workflow-id", "-w", default="", help="Remote workflow ID")
def dev_test_create(json_data, workflow_id):
    """Generate a test template from a workflow JSON. Saves to workflows/tests/."""
    from n8n_client.test_runner import create_test_template
    import os
    wf_file = json_data[1:] if json_data.startswith("@") else json_data
    wf = _load_json_arg(json_data)
    template = create_test_template(wf, wf_file=wf_file, workflow_id=workflow_id)
    wf_name = wf.get("name", "unnamed").replace(" ", "-").lower()
    out_dir = "workflows/tests"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{wf_name}.test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
        f.write("\n")
    click.echo(f"Test template saved: {out_path}")


@dev.command("test-run-all")
def dev_test_run_all():
    """Run all test suites in workflows/tests/."""
    from n8n_client.test_runner import load_test_suite, run_test_suite, format_test_results
    from pathlib import Path
    test_dir = Path("workflows/tests")
    if not test_dir.exists():
        click.echo("No test directory found: workflows/tests/", err=True)
        sys.exit(1)
    test_files = sorted(test_dir.glob("*.test.json"))
    if not test_files:
        click.echo("No test files found in workflows/tests/", err=True)
        sys.exit(1)
    client = _get_client()
    active = _cfg.get_active_client()
    base_url = active[1]["base_url"] if active else ""
    all_results: list[dict] = []
    for tf in test_files:
        click.echo(f"\n--- {tf.name} ---", err=True)
        suite = load_test_suite(str(tf))
        results = run_test_suite(client, base_url, suite)
        all_results.extend(results)
        click.echo(format_test_results(results))
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    click.echo(f"\n{'='*40}")
    click.echo(f"Total: {passed}/{total} passed")


@dev.command("show")
@click.argument("json_data")
def dev_show(json_data):
    """Visualize workflow structure as text tree."""
    from n8n_client.visualize import visualize_workflow
    wf = _load_json_arg(json_data)
    click.echo(visualize_workflow(wf))


@dev.command("info")
@click.argument("json_data")
def dev_info(json_data):
    """Show workflow summary info."""
    from n8n_client.visualize import summarize_workflow
    wf = _load_json_arg(json_data)
    click.echo(summarize_workflow(wf))


# ── Batch & Migration ─────────────────────────────────────

@dev.command("batch-deploy")
@click.argument("json_files", nargs=-1, required=True)
@click.option("--project-id", "-p", help="Target project ID")
def dev_batch_deploy(json_files, project_id):
    """Batch deploy multiple workflows. Pass @file1.json @file2.json ..."""
    from n8n_client.batch import batch_deploy
    client = _get_client()
    wf_list = [_load_json_arg(f) for f in json_files]
    click.echo(f"Deploying {len(wf_list)} workflow(s)...", err=True)
    reports = batch_deploy(client, wf_list, project_id=project_id)
    for i, report in enumerate(reports):
        click.echo(f"\n--- [{i + 1}/{len(reports)}] {json_files[i]} ---")
        click.echo(report.summary())
    ok = sum(1 for r in reports if r.deployed_workflow_id)
    fail = len(reports) - ok
    click.echo(f"\nResult: {ok} deployed, {fail} failed", err=True)


@dev.command("batch-activate")
@click.argument("workflow_ids", nargs=-1, required=True)
def dev_batch_activate(workflow_ids):
    """Bulk activate workflows."""
    from n8n_client.batch import batch_activate
    client = _get_client()
    results = batch_activate(client, list(workflow_ids), active=True)
    for r in results:
        status = "OK" if r["status"] == "ok" else f"ERROR: {r['message']}"
        click.echo(f"  {r['id']}: {status}")


@dev.command("batch-deactivate")
@click.argument("workflow_ids", nargs=-1, required=True)
def dev_batch_deactivate(workflow_ids):
    """Bulk deactivate workflows."""
    from n8n_client.batch import batch_activate
    client = _get_client()
    results = batch_activate(client, list(workflow_ids), active=False)
    for r in results:
        status = "OK" if r["status"] == "ok" else f"ERROR: {r['message']}"
        click.echo(f"  {r['id']}: {status}")


@dev.command("migrate")
@click.argument("workflow_id")
@click.option("--from", "from_client", required=True, help="Source client name")
@click.option("--to", "to_client", required=True, help="Target client name")
@click.option("--project-id", "-p", help="Target project ID")
def dev_migrate(workflow_id, from_client, to_client, project_id):
    """Migrate a workflow between environments."""
    from n8n_client.batch import migrate_workflow
    _, src_info = _cfg.get_client(from_client)
    _, tgt_info = _cfg.get_client(to_client)
    source = N8nClient(src_info["base_url"], src_info["api_key"])
    target = N8nClient(tgt_info["base_url"], tgt_info["api_key"])
    click.echo(f"Migrating workflow {workflow_id}: {from_client} -> {to_client}", err=True)
    report = migrate_workflow(source, target, workflow_id, project_id=project_id)
    click.echo(report.summary())


@dev.command("migrate-all")
@click.option("--from", "from_client", required=True, help="Source client name")
@click.option("--to", "to_client", required=True, help="Target client name")
@click.option("--project-id", "-p", help="Target project ID")
def dev_migrate_all(from_client, to_client, project_id):
    """Migrate all workflows between environments."""
    from n8n_client.batch import migrate_all
    _, src_info = _cfg.get_client(from_client)
    _, tgt_info = _cfg.get_client(to_client)
    source = N8nClient(src_info["base_url"], src_info["api_key"])
    target = N8nClient(tgt_info["base_url"], tgt_info["api_key"])
    click.echo(f"Migrating all workflows: {from_client} -> {to_client}", err=True)
    reports = migrate_all(source, target, project_id=project_id)
    for i, report in enumerate(reports, 1):
        click.echo(f"\n--- [{i}/{len(reports)}] ---")
        click.echo(report.summary())
    ok = sum(1 for r in reports if r.deployed_workflow_id)
    fail = len(reports) - ok
    click.echo(f"\nResult: {ok} migrated, {fail} failed", err=True)


# ── Templates ──────────────────────────────────────────────

@dev.group()
def template():
    """Workflow template operations."""
    pass


@template.command("list")
def template_list():
    """List available workflow templates."""
    from n8n_client.templates import list_templates
    templates = list_templates()
    if not templates:
        click.echo("No templates found.")
        return
    for t in templates:
        click.echo(f"  {t['name']:30s} {t['description']}  (nodes: {t['nodes_count']}, trigger: {t['trigger_type']})")


@template.command("show")
@click.argument("name")
def template_show(name):
    """Show the contents of a template."""
    from n8n_client.templates import get_template
    try:
        tmpl = get_template(name)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    _output(tmpl)


@template.command("use")
@click.argument("name")
@click.option("--name", "wf_name", help="Workflow name to set")
@click.option("--output", "-o", help="Output file path (default: stdout)")
def template_use(name, wf_name, output):
    """Generate a workflow from a template (with fresh UUIDs)."""
    from n8n_client.templates import instantiate_template
    try:
        wf = instantiate_template(name, workflow_name=wf_name)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    result = json.dumps(wf, indent=2, ensure_ascii=False)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result)
            f.write("\n")
        click.echo(f"Written to {output}", err=True)
    else:
        click.echo(result)


if __name__ == "__main__":
    cli()
