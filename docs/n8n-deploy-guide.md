# n8n デプロイ・テストガイド

ワークフローのデプロイ、クレデンシャル解決、テスト実行の手順。

---

## 1. デプロイフロー

### 基本手順
1. ワークフローJSONを `workflows/` に作成
2. `n8n project list` でデプロイ先プロジェクトを確認
3. `n8n workflow create @workflows/xxx.json -p <project_id>` でデプロイ
4. デプロイ後、必要に応じて `n8n workflow activate <id>` でアクティベーション

### Activation安全確認
アクティベーション前に以下を確認:
- トリガー種別と影響（例: 「WebhookがXXXで公開されます」「5分ごとに実行されます」）
- 対象インスタンスが本番かどうか
- ユーザーの明示的な承認

### Webhook URL通知
Webhookトリガーを含むWFをデプロイした場合:
- `{base_url}/webhook/{path}` （本番用）
- `{base_url}/webhook-test/{path}` （テスト実行用）

## 2. クレデンシャルマッピング

n8n Cloudでは `GET /api/v1/credentials` が405エラーのため、代替手段でクレデンシャルを解決する。

### 収集フロー
1. `n8n workflow list` で全ワークフローを取得
2. 各ノードの `credentials` フィールドを抽出
3. type別に `{credential_id, credential_name}` のマッピングを構築

### 解決フロー
1. 生成したWFが必要とするクレデンシャルtype一覧を抽出
2. マッピングから自動マッチング:
   - **一致するtypeが1つ** → 自動適用
   - **複数候補** → ユーザーに選択を求める
   - **該当なし** → 「n8n上でこのクレデンシャルを先に作成してください」と案内

### 収集スクリプト例
```bash
n8n workflow list | python3 -c "
import json, sys
data = json.load(sys.stdin)
cred_map = {}
for wf in data.get('data', []):
    for n in wf.get('nodes', []):
        for ctype, cdata in n.get('credentials', {}).items():
            cred_map.setdefault(ctype, []).append({
                'id': cdata['id'], 'name': cdata['name']
            })
for ctype, creds in cred_map.items():
    unique = {c['id']: c['name'] for c in creds}
    for cid, cname in unique.items():
        print(f'{ctype}: {cname} (ID: {cid})')
"
```

## 3. サブワークフロー依存関係

メインWFが `executeWorkflow` ノードでサブWFを呼ぶ場合:

1. WF JSON内の `n8n-nodes-base.executeWorkflow` ノードを検出
2. 参照先のサブWFが対象インスタンスに存在するか確認
3. **存在しない場合**: サブWFを先にデプロイ → メインWFの `subWorkflow.id` を差し替え
4. **存在する場合**: サブWFのIDを取得して差し替え

## 4. テスト実行

### Webhook トリガーの場合
```bash
# テストデータをWebhook URLにPOST
curl -X POST "{base_url}/webhook-test/{path}" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### 手動トリガー / スケジュールトリガーの場合
```bash
# n8n API経由でワークフローを実行
# 注: executeはCloud版のAPIバージョンによっては動作が異なる
```

### 実行結果の確認
```bash
# 実行一覧（対象ワークフロー）
n8n execution list -w <workflow_id>

# 実行詳細（ノード別入出力含む）
n8n execution get <execution_id> --include-data
```

### テストサイクル
1. テストデータを作成（正常系・異常系）
2. テスト実行
3. 実行結果を確認（成功/失敗・各ノードの入出力）
4. 失敗した場合 → エラー分析 → WF修正 → 再デプロイ → 再テスト

## 5. 更新時の注意

PUT（更新）はクラウドの設定を**全上書き**する。

```bash
# 更新前に必ず最新を取得
n8n workflow get <id> > /tmp/current.json
# 差分を確認してからアップデート
n8n workflow update <id> @workflows/updated.json
```
