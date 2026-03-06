"""Credential discovery and resolution for n8n Cloud environments.

n8n Cloud では GET /api/v1/credentials が 405 のため、
既存ワークフローのノードからクレデンシャル情報を収集・マッピングする。
"""

from __future__ import annotations

from n8n_client.client import N8nClient

# よく使われるクレデンシャルタイプのセットアップガイド
CREDENTIAL_SETUP_GUIDES: dict[str, dict] = {
    "slackOAuth2Api": {
        "display_name": "Slack OAuth2",
        "setup_steps": [
            "n8n の Credentials > New Credential > Slack OAuth2 API を選択",
            "Slack API (api.slack.com) で App を作成し OAuth トークンを取得",
            "Bot Token Scopes に必要な権限を追加 (chat:write, channels:read 等)",
            "n8n に Client ID, Client Secret を入力して Connect",
        ],
    },
    "slackApi": {
        "display_name": "Slack API (Bot Token)",
        "setup_steps": [
            "n8n の Credentials > New Credential > Slack API を選択",
            "Slack API で Bot User OAuth Token を取得",
            "Access Token フィールドに xoxb-... トークンを入力",
        ],
    },
    "googleCalendarOAuth2Api": {
        "display_name": "Google Calendar OAuth2",
        "setup_steps": [
            "n8n の Credentials > New Credential > Google Calendar OAuth2 API を選択",
            "Google Cloud Console で OAuth 2.0 クライアントIDを作成",
            "n8n に Client ID, Client Secret を入力して Connect",
            "Calendar API を有効化しておくこと",
        ],
    },
    "googleSheetsOAuth2Api": {
        "display_name": "Google Sheets OAuth2",
        "setup_steps": [
            "n8n の Credentials > New Credential > Google Sheets OAuth2 API を選択",
            "Google Cloud Console で OAuth 2.0 クライアントIDを作成",
            "n8n に Client ID, Client Secret を入力して Connect",
            "Sheets API を有効化しておくこと",
        ],
    },
    "gmailOAuth2": {
        "display_name": "Gmail OAuth2",
        "setup_steps": [
            "n8n の Credentials > New Credential > Gmail OAuth2 API を選択",
            "Google Cloud Console で OAuth 2.0 クライアントIDを作成",
            "n8n に Client ID, Client Secret を入力して Connect",
            "Gmail API を有効化しておくこと",
        ],
    },
    "notionApi": {
        "display_name": "Notion API",
        "setup_steps": [
            "n8n の Credentials > New Credential > Notion API を選択",
            "Notion で Internal Integration を作成 (notion.so/my-integrations)",
            "Internal Integration Secret を n8n に入力",
            "対象のデータベース/ページで Integration を共有設定すること",
        ],
    },
    "openAiApi": {
        "display_name": "OpenAI API",
        "setup_steps": [
            "n8n の Credentials > New Credential > OpenAI API を選択",
            "OpenAI の API Keys ページで API Key を発行",
            "API Key を n8n に入力",
        ],
    },
    "anthropicApi": {
        "display_name": "Anthropic API",
        "setup_steps": [
            "n8n の Credentials > New Credential > Anthropic API を選択",
            "Anthropic Console で API Key を発行",
            "API Key を n8n に入力",
        ],
    },
    "supabaseApi": {
        "display_name": "Supabase API",
        "setup_steps": [
            "n8n の Credentials > New Credential > Supabase API を選択",
            "Supabase Dashboard > Settings > API から URL と anon/service_role key を取得",
            "Host (URL) と Service Role Key を n8n に入力",
        ],
    },
    "httpBasicAuth": {
        "display_name": "HTTP Basic Auth",
        "setup_steps": [
            "n8n の Credentials > New Credential > HTTP Basic Auth を選択",
            "Username と Password を入力",
        ],
    },
    "httpHeaderAuth": {
        "display_name": "HTTP Header Auth",
        "setup_steps": [
            "n8n の Credentials > New Credential > HTTP Header Auth を選択",
            "Header Name (例: Authorization) と Value (例: Bearer xxx) を入力",
        ],
    },
}


def collect_credentials_from_workflows(client: N8nClient) -> dict[str, list[dict]]:
    """Scan all workflows on the instance to build a credential map.

    Returns: { credential_type: [{ id, name, used_in_workflows: [...] }] }
    """
    cred_map: dict[str, dict[str, dict]] = {}

    cursor = None
    while True:
        result = client.list_workflows(limit=250, cursor=cursor)
        workflows = result.get("data", [])

        for wf in workflows:
            wf_name = wf.get("name", "")
            for node in wf.get("nodes", []):
                for cred_type, cred_info in node.get("credentials", {}).items():
                    cred_id = cred_info.get("id", "")
                    if not cred_id:
                        continue
                    by_type = cred_map.setdefault(cred_type, {})
                    if cred_id not in by_type:
                        by_type[cred_id] = {
                            "id": cred_id,
                            "name": cred_info.get("name", ""),
                            "used_in_workflows": [],
                        }
                    wf_list = by_type[cred_id]["used_in_workflows"]
                    if wf_name not in wf_list:
                        wf_list.append(wf_name)

        cursor = result.get("nextCursor")
        if not cursor:
            break

    # Flatten to list per type
    return {
        cred_type: list(entries.values())
        for cred_type, entries in cred_map.items()
    }


def resolve_credentials(
    available: dict[str, list[dict]],
    required: list[dict],
) -> list[dict]:
    """Match required credentials against available ones.

    Returns list of resolution results:
    {
        type, node_name, status: "resolved"|"multiple"|"missing",
        resolved_id, resolved_name,  # if resolved
        candidates,                   # if multiple
        setup_guide,                  # if missing
    }
    """
    results: list[dict] = []

    for req in required:
        cred_type = req["type"]
        candidates = available.get(cred_type, [])

        entry: dict = {
            "type": cred_type,
            "node_name": req["node_name"],
            "node_type": req["node_type"],
        }

        if len(candidates) == 1:
            entry["status"] = "resolved"
            entry["resolved_id"] = candidates[0]["id"]
            entry["resolved_name"] = candidates[0]["name"]
        elif len(candidates) > 1:
            entry["status"] = "multiple"
            entry["candidates"] = [
                {"id": c["id"], "name": c["name"]} for c in candidates
            ]
        else:
            entry["status"] = "missing"
            guide = CREDENTIAL_SETUP_GUIDES.get(cred_type)
            if guide:
                entry["setup_guide"] = guide
            else:
                entry["setup_guide"] = {
                    "display_name": cred_type,
                    "setup_steps": [
                        f"n8n の Credentials > New Credential で '{cred_type}' を検索して作成",
                        "必要な認証情報を入力して保存",
                    ],
                }

        results.append(entry)

    return results


def apply_resolved_credentials(wf: dict, resolutions: list[dict]) -> dict:
    """Apply resolved credentials to workflow JSON.

    Only applies entries with status='resolved'.
    """
    import copy
    wf = copy.deepcopy(wf)

    resolved_map = {
        r["type"]: (r["resolved_id"], r["resolved_name"])
        for r in resolutions
        if r.get("status") == "resolved"
    }

    for node in wf.get("nodes", []):
        for cred_type in list(node.get("credentials", {}).keys()):
            if cred_type in resolved_map:
                cred_id, cred_name = resolved_map[cred_type]
                node["credentials"][cred_type] = {
                    "id": cred_id,
                    "name": cred_name,
                }

    return wf


def get_credential_setup_guide(cred_type: str) -> dict:
    """Get setup instructions for a credential type."""
    if cred_type in CREDENTIAL_SETUP_GUIDES:
        return CREDENTIAL_SETUP_GUIDES[cred_type]
    return {
        "display_name": cred_type,
        "setup_steps": [
            f"n8n の Credentials > New Credential で '{cred_type}' を検索して作成",
            "必要な認証情報を入力して保存",
        ],
    }
