"""n8n Public API client — covers all 59 endpoints (API v1)."""

from __future__ import annotations

import requests


class N8nClient:
    """Stateless HTTP client for the n8n Public REST API v1."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/") + "/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    # ── helpers ──────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs) -> dict | list | None:
        resp = self.session.request(method, self._url(path), **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _get(self, path, **kw):    return self._request("GET", path, **kw)
    def _post(self, path, **kw):   return self._request("POST", path, **kw)
    def _put(self, path, **kw):    return self._request("PUT", path, **kw)
    def _patch(self, path, **kw):  return self._request("PATCH", path, **kw)
    def _delete(self, path, **kw): return self._request("DELETE", path, **kw)

    @staticmethod
    def _pagination_params(limit: int | None, cursor: str | None) -> dict:
        params: dict = {}
        if limit is not None:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor
        return params

    # ── 1. Audit (1) ────────────────────────────────────────

    def generate_audit(
        self,
        categories: list[str] | None = None,
        days_abandoned_workflow: int | None = None,
    ) -> dict:
        body: dict = {}
        opts: dict = {}
        if categories:
            opts["categories"] = categories
        if days_abandoned_workflow is not None:
            opts["daysAbandonedWorkflow"] = days_abandoned_workflow
        if opts:
            body["additionalOptions"] = opts
        return self._post("/audit", json=body)

    # ── 2. Credentials (6) ──────────────────────────────────

    def list_credentials(
        self, *, limit: int | None = None, cursor: str | None = None,
    ) -> dict:
        return self._get("/credentials", params=self._pagination_params(limit, cursor))

    def create_credential(self, data: dict) -> dict:
        return self._post("/credentials", json=data)

    def update_credential(self, credential_id: str, data: dict) -> dict:
        return self._patch(f"/credentials/{credential_id}", json=data)

    def delete_credential(self, credential_id: str) -> dict:
        return self._delete(f"/credentials/{credential_id}")

    def get_credential_schema(self, credential_type_name: str) -> dict:
        return self._get(f"/credentials/schema/{credential_type_name}")

    def transfer_credential(self, credential_id: str, destination_project_id: str):
        return self._put(
            f"/credentials/{credential_id}/transfer",
            json={"destinationProjectId": destination_project_id},
        )

    # ── 3. Executions (8) ───────────────────────────────────

    def list_executions(
        self,
        *,
        workflow_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        include_data: bool = False,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params = self._pagination_params(limit, cursor)
        if workflow_id:
            params["workflowId"] = workflow_id
        if project_id:
            params["projectId"] = project_id
        if status:
            params["status"] = status
        if include_data:
            params["includeData"] = "true"
        return self._get("/executions", params=params)

    def get_execution(self, execution_id: str, *, include_data: bool = False) -> dict:
        params = {}
        if include_data:
            params["includeData"] = "true"
        return self._get(f"/executions/{execution_id}", params=params)

    def delete_execution(self, execution_id: str) -> dict:
        return self._delete(f"/executions/{execution_id}")

    def retry_execution(self, execution_id: str, *, load_workflow: bool = False) -> dict:
        body = {}
        if load_workflow:
            body["loadWorkflow"] = True
        return self._post(f"/executions/{execution_id}/retry", json=body)

    def stop_execution(self, execution_id: str) -> dict:
        return self._post(f"/executions/{execution_id}/stop")

    def stop_executions(
        self,
        status: list[str],
        *,
        workflow_id: str | None = None,
        started_after: str | None = None,
        started_before: str | None = None,
    ) -> dict:
        body: dict = {"status": status}
        if workflow_id:
            body["workflowId"] = workflow_id
        if started_after:
            body["startedAfter"] = started_after
        if started_before:
            body["startedBefore"] = started_before
        return self._post("/executions/stop", json=body)

    def get_execution_tags(self, execution_id: str) -> list:
        return self._get(f"/executions/{execution_id}/tags")

    def update_execution_tags(self, execution_id: str, tag_ids: list[str]) -> list:
        return self._put(
            f"/executions/{execution_id}/tags",
            json=[{"id": tid} for tid in tag_ids],
        )

    # ── 4. Workflows (11) ───────────────────────────────────

    def list_workflows(
        self,
        *,
        active: bool | None = None,
        tags: str | None = None,
        name: str | None = None,
        project_id: str | None = None,
        exclude_pinned_data: bool = False,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params = self._pagination_params(limit, cursor)
        if active is not None:
            params["active"] = str(active).lower()
        if tags:
            params["tags"] = tags
        if name:
            params["name"] = name
        if project_id:
            params["projectId"] = project_id
        if exclude_pinned_data:
            params["excludePinnedData"] = "true"
        return self._get("/workflows", params=params)

    def create_workflow(self, data: dict, *, project_id: str | None = None) -> dict:
        if project_id:
            data = {**data, "projectId": project_id}
        return self._post("/workflows", json=data)

    def get_workflow(self, workflow_id: str, *, exclude_pinned_data: bool = False) -> dict:
        params = {}
        if exclude_pinned_data:
            params["excludePinnedData"] = "true"
        return self._get(f"/workflows/{workflow_id}", params=params)

    def update_workflow(self, workflow_id: str, data: dict) -> dict:
        return self._put(f"/workflows/{workflow_id}", json=data)

    def delete_workflow(self, workflow_id: str) -> dict:
        return self._delete(f"/workflows/{workflow_id}")

    def get_workflow_version(self, workflow_id: str, version_id: str) -> dict:
        return self._get(f"/workflows/{workflow_id}/{version_id}")

    def activate_workflow(
        self,
        workflow_id: str,
        *,
        version_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        body: dict = {}
        if version_id:
            body["versionId"] = version_id
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        return self._post(f"/workflows/{workflow_id}/activate", json=body)

    def deactivate_workflow(self, workflow_id: str) -> dict:
        return self._post(f"/workflows/{workflow_id}/deactivate")

    def transfer_workflow(self, workflow_id: str, destination_project_id: str):
        return self._put(
            f"/workflows/{workflow_id}/transfer",
            json={"destinationProjectId": destination_project_id},
        )

    def get_workflow_tags(self, workflow_id: str) -> list:
        return self._get(f"/workflows/{workflow_id}/tags")

    def update_workflow_tags(self, workflow_id: str, tag_ids: list[str]) -> list:
        return self._put(
            f"/workflows/{workflow_id}/tags",
            json=[{"id": tid} for tid in tag_ids],
        )

    # ── 5. Tags (5) ─────────────────────────────────────────

    def list_tags(
        self, *, limit: int | None = None, cursor: str | None = None,
    ) -> dict:
        return self._get("/tags", params=self._pagination_params(limit, cursor))

    def create_tag(self, name: str) -> dict:
        return self._post("/tags", json={"name": name})

    def get_tag(self, tag_id: str) -> dict:
        return self._get(f"/tags/{tag_id}")

    def update_tag(self, tag_id: str, name: str) -> dict:
        return self._put(f"/tags/{tag_id}", json={"name": name})

    def delete_tag(self, tag_id: str) -> dict:
        return self._delete(f"/tags/{tag_id}")

    # ── 6. Users (5) ────────────────────────────────────────

    def list_users(
        self,
        *,
        include_role: bool = False,
        project_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params = self._pagination_params(limit, cursor)
        if include_role:
            params["includeRole"] = "true"
        if project_id:
            params["projectId"] = project_id
        return self._get("/users", params=params)

    def invite_users(self, users: list[dict]) -> dict:
        return self._post("/users", json=users)

    def get_user(self, user_id_or_email: str, *, include_role: bool = False) -> dict:
        params = {}
        if include_role:
            params["includeRole"] = "true"
        return self._get(f"/users/{user_id_or_email}", params=params)

    def delete_user(self, user_id: str):
        return self._delete(f"/users/{user_id}")

    def update_user_role(self, user_id: str, new_role_name: str):
        return self._patch(f"/users/{user_id}/role", json={"newRoleName": new_role_name})

    # ── 7. Source Control (1) ───────────────────────────────

    def source_control_pull(self, options: dict | None = None) -> dict:
        return self._post("/source-control/pull", json=options or {})

    # ── 8. Variables (4) ────────────────────────────────────

    def list_variables(
        self,
        *,
        project_id: str | None = None,
        state: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params = self._pagination_params(limit, cursor)
        if project_id:
            params["projectId"] = project_id
        if state:
            params["state"] = state
        return self._get("/variables", params=params)

    def create_variable(self, key: str, value: str):
        return self._post("/variables", json={"key": key, "value": value})

    def update_variable(self, variable_id: str, key: str, value: str):
        return self._put(f"/variables/{variable_id}", json={"key": key, "value": value})

    def delete_variable(self, variable_id: str):
        return self._delete(f"/variables/{variable_id}")

    # ── 9. Data Tables (10) ─────────────────────────────────

    def list_data_tables(
        self,
        *,
        filter_: str | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params = self._pagination_params(limit, cursor)
        if filter_:
            params["filter"] = filter_
        if sort_by:
            params["sortBy"] = sort_by
        return self._get("/data-tables", params=params)

    def create_data_table(self, name: str, columns: list[dict]) -> dict:
        return self._post("/data-tables", json={"name": name, "columns": columns})

    def get_data_table(self, table_id: str) -> dict:
        return self._get(f"/data-tables/{table_id}")

    def update_data_table(self, table_id: str, name: str) -> dict:
        return self._patch(f"/data-tables/{table_id}", json={"name": name})

    def delete_data_table(self, table_id: str):
        return self._delete(f"/data-tables/{table_id}")

    def list_data_table_rows(
        self,
        table_id: str,
        *,
        filter_: str | None = None,
        sort_by: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        params = self._pagination_params(limit, cursor)
        if filter_:
            params["filter"] = filter_
        if sort_by:
            params["sortBy"] = sort_by
        if search:
            params["search"] = search
        return self._get(f"/data-tables/{table_id}/rows", params=params)

    def insert_data_table_rows(
        self,
        table_id: str,
        rows: list[dict],
        *,
        return_type: str = "count",
    ) -> dict:
        return self._post(
            f"/data-tables/{table_id}/rows",
            json={"data": rows, "returnType": return_type},
        )

    def update_data_table_rows(
        self,
        table_id: str,
        filter_: dict,
        data: dict,
        *,
        return_data: bool = False,
        dry_run: bool = False,
    ) -> dict:
        body = {"filter": filter_, "data": data}
        if return_data:
            body["returnData"] = True
        if dry_run:
            body["dryRun"] = True
        return self._patch(f"/data-tables/{table_id}/rows/update", json=body)

    def upsert_data_table_row(
        self,
        table_id: str,
        filter_: dict,
        data: dict,
        *,
        return_data: bool = False,
        dry_run: bool = False,
    ) -> dict:
        body = {"filter": filter_, "data": data}
        if return_data:
            body["returnData"] = True
        if dry_run:
            body["dryRun"] = True
        return self._post(f"/data-tables/{table_id}/rows/upsert", json=body)

    def delete_data_table_rows(
        self,
        table_id: str,
        filter_: str,
        *,
        return_data: bool = False,
        dry_run: bool = False,
    ):
        params = {"filter": filter_}
        if return_data:
            params["returnData"] = "true"
        if dry_run:
            params["dryRun"] = "true"
        return self._delete(f"/data-tables/{table_id}/rows/delete", params=params)

    # ── 10. Projects (8) ────────────────────────────────────

    def list_projects(
        self, *, limit: int | None = None, cursor: str | None = None,
    ) -> dict:
        return self._get("/projects", params=self._pagination_params(limit, cursor))

    def create_project(self, name: str):
        return self._post("/projects", json={"name": name})

    def update_project(self, project_id: str, name: str):
        return self._put(f"/projects/{project_id}", json={"name": name})

    def delete_project(self, project_id: str):
        return self._delete(f"/projects/{project_id}")

    def list_project_users(
        self,
        project_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> dict:
        return self._get(
            f"/projects/{project_id}/users",
            params=self._pagination_params(limit, cursor),
        )

    def add_project_users(self, project_id: str, relations: list[dict]):
        return self._post(
            f"/projects/{project_id}/users",
            json={"relations": relations},
        )

    def update_project_user_role(self, project_id: str, user_id: str, role: str):
        return self._patch(
            f"/projects/{project_id}/users/{user_id}",
            json={"role": role},
        )

    def remove_project_user(self, project_id: str, user_id: str):
        return self._delete(f"/projects/{project_id}/users/{user_id}")
