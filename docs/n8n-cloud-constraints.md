# n8n Cloud 開発制約ガイド

n8n Cloud環境でワークフローをAPI経由で作成・デプロイする際の制約とベストプラクティス。

---

## 1. ノードIDはUUID形式が必須

カスタム文字列IDだと「Install this node to use it」エラーになる。

```
NG: "id": "node-trigger-created"
OK: "id": "e6663e6c-7ecf-4c3d-9106-2a77b3192f50"
```

Python で生成:
```python
import uuid
node_id = str(uuid.uuid4())
```

## 2. ノードの許可プロパティ（トップレベル）

以下のキーのみ使用可能。他を含めると HTTP 400 `"must NOT have additional properties"` エラー。

| 許可キー |
|---------|
| `id` |
| `name` |
| `parameters` |
| `position` |
| `type` |
| `typeVersion` |
| `credentials` |
| `webhookId` |
| `disabled` |
| `notesInFlow` |
| `notes` |

**不可**: `retryOnFail`, `maxTries`, `waitBetweenTries`, `onError`, `polling`
→ 削除するか `parameters` 内に移動する。

## 3. 動作確認済み typeVersion 一覧

| ノードタイプ | typeVersion | 備考 |
|---|---|---|
| `googleCalendarTrigger` | **1** | 1.2は未対応。`pollTimes` 必須 |
| `code` | 2 | Python: `pythonNative` / JS: デフォルト |
| `if` | 2.2 | |
| `httpRequest` | 4.2 | |
| `switch` | 3.2 | |
| `stickyNote` | 1 | |
| `webhook` | 1 | |
| `respondToWebhook` | 1.1 | |
| `set` | 3.4 | |
| `notion` | 2.2 | |

## 4. Credentials API の制限

```
GET /api/v1/credentials → 405 Method Not Allowed（Cloud環境）
```

**代替手段**: 既存ワークフローのノードデータからCredential情報を収集する。

```bash
# 全ワークフローを取得して特定のCredentialを検索
n8n workflow list | python3 -c "
import json, sys
data = json.load(sys.stdin)
for wf in data.get('data', []):
    for n in wf.get('nodes', []):
        for ctype, cdata in n.get('credentials', {}).items():
            print(f'{ctype}: {cdata[\"name\"]} (ID: {cdata[\"id\"]})')
"
```

## 5. REST APIアップロードの注意

**PUT（更新）はクラウドの全設定を上書きする。**
クラウド上でUI経由で行った変更（ノードの追加・修正・Credential設定など）はローカルJSONで上書きされる。

**推奨フロー**:
1. `n8n workflow get <id>` で最新を取得
2. ローカルJSONと差分を確認
3. ローカルJSONにクラウドの変更を反映
4. その上で `n8n workflow update <id> @file.json`

## 6. トラブルシューティング

| エラーメッセージ | 原因 | 対処 |
|---|---|---|
| `must NOT have additional properties` | 不正なトップレベルプロパティ | 許可キー以外を削除 (§2) |
| `Install this node to use it` | ノードIDが非UUID | UUID形式に変更 (§1) |
| `This node is not currently installed` | `typeVersion` がCloud未対応 | 動作確認済みバージョンに変更 (§3) |
| `name '_input' is not defined` | Python Code Nodeで `_input` 使用 | `_items[0]["json"]` に変更 |
| `name '_node' is not defined` | Python Code Nodeで `_node` 使用 | JavaScriptに切り替え |
| `GET /api/v1/credentials` → 405 | CloudではCredentials API非対応 | 既存WFから取得 (§4) |
