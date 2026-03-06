# n8n for Claude Code

このプロジェクトは、Claude Codeからn8nのAPI経由でワークフローの作成・管理・実行を自動化するためのものです。
複数クライアント環境に対応しています。

## CLI ツール

`n8n` コマンドで全操作が可能。Bash ツールから直接呼び出す。

## セッション開始時のフロー

1. `n8n config list` を実行して登録済みクライアントを確認
2. **クライアントが未登録の場合** → 新規クライアント登録フローへ
3. **クライアントが登録済みの場合** → 一覧を表示し、どの環境で作業するか質問
4. ユーザーが選んだクライアントに `n8n config switch <name>` で切り替え
5. `n8n config test` で接続確認

## 新規クライアント登録

ユーザーに以下を質問する:
1. **クライアント名**（識別用の短い名前。例: `acme_prod`, `local_dev`）
2. **n8n URL**（例: `https://acme.n8n.cloud` または `http://localhost:5678`）
3. **API Key**（n8nの Settings > API で発行）
4. **説明**（任意。例: `ACME社 本番環境`）

```bash
n8n config add <name> <url> <api_key> -d "<description>"
```

## CLI コマンド一覧

### クライアント管理

```bash
n8n config list              # 一覧表示
n8n config active            # アクティブクライアント確認
n8n config switch <name>     # 切り替え
n8n config add <name> <url> <api_key> [-d desc]  # 追加
n8n config remove <name>     # 削除
n8n config test              # 接続テスト
```

### ワークフロー (11 endpoints)

```bash
n8n workflow list [--active|--inactive] [--tags t1,t2] [--name x] [-p project_id]
n8n workflow get <id> [--exclude-pinned-data]
n8n workflow create <json|@file.json> [-p project_id]
n8n workflow update <id> <json|@file.json>
n8n workflow delete <id>
n8n workflow version <id> <version_id>
n8n workflow activate <id> [--version-id x] [--name x] [--description x]
n8n workflow deactivate <id>
n8n workflow transfer <id> <dest_project_id>
n8n workflow tags <id>
n8n workflow set-tags <id> <tag_id1> <tag_id2> ...
```

### 実行 (8 endpoints)

```bash
n8n execution list [-w workflow_id] [-p project_id] [--status error|success|...]
n8n execution get <id> [--include-data]
n8n execution delete <id>
n8n execution retry <id> [--load-workflow]
n8n execution stop <id>
n8n execution stop-many <status1> <status2> [-w workflow_id]
n8n execution tags <id>
n8n execution set-tags <id> <tag_id1> ...
```

### クレデンシャル (6 endpoints)

```bash
n8n credential list
n8n credential create <json|@file.json>
n8n credential update <id> <json|@file.json>
n8n credential delete <id>
n8n credential schema <credential_type_name>
n8n credential transfer <id> <dest_project_id>
```

### プロジェクト (8 endpoints)

```bash
n8n project list
n8n project create <name>
n8n project update <id> <name>
n8n project delete <id>
n8n project users <id>
n8n project add-user <id> '<json_relations>'
n8n project set-user-role <project_id> <user_id> <role>
n8n project remove-user <project_id> <user_id>
```

### タグ (5 endpoints)

```bash
n8n tag list
n8n tag get <id>
n8n tag create <name>
n8n tag update <id> <name>
n8n tag delete <id>
```

### ユーザー (5 endpoints)

```bash
n8n user list [--include-role] [-p project_id]
n8n user get <id_or_email> [--include-role]
n8n user invite '<json_array>'
n8n user delete <id>
n8n user set-role <id> <role>
```

### 変数 (4 endpoints)

```bash
n8n variable list [-p project_id] [--state empty]
n8n variable create <key> <value>
n8n variable update <id> <key> <value>
n8n variable delete <id>
```

### データテーブル (10 endpoints)

```bash
n8n data-table list [--filter json] [--sort-by name:asc]
n8n data-table get <id>
n8n data-table create <name> '<columns_json>'
n8n data-table update <id> <new_name>
n8n data-table delete <id>
n8n data-table row list <table_id> [--filter json] [--search x]
n8n data-table row insert <table_id> '<rows_json>' [--return-type count|id|all]
n8n data-table row update <table_id> '<filter_json>' '<data_json>' [--dry-run]
n8n data-table row upsert <table_id> '<filter_json>' '<data_json>' [--dry-run]
n8n data-table row delete <table_id> '<filter_json>' [--dry-run]
```

### ソースコントロール (1 endpoint)

```bash
n8n source-control pull [--options '<json>']
```

### 監査 (1 endpoint)

```bash
n8n audit generate [-c credentials,database,nodes] [--days-abandoned 90]
```

## 開発ヘルパー (`n8n dev`)

ワークフロー開発の障害を自動的に解決するコマンド群。

### 開発フロー（推奨手順）

#### 新規ワークフロー作成
1. **テンプレートから開始**: `n8n dev template use webhook-slack --name "[Slack] 通知" -o workflows/xxx.json`
2. **構造確認**: `n8n dev show @workflows/xxx.json`
3. **バリデーション**: `n8n dev validate @workflows/xxx.json`
4. **自動修正**: `n8n dev sanitize @workflows/xxx.json -o workflows/xxx.json`
5. **クレデンシャル確認**: `n8n dev resolve-credentials @workflows/xxx.json`
6. **プリフライト**: `n8n dev preflight @workflows/xxx.json`
7. **デプロイ**: `n8n dev deploy @workflows/xxx.json [-p project_id]`
8. **テスト**: `n8n dev webhook-test @workflows/xxx.json`
9. **結果確認**: `n8n dev check-execution <execution_id>`
10. **有効化**: `n8n dev activate <workflow_id>`（安全確認付き）

#### 既存ワークフロー修正
1. **取得**: `n8n dev edit <workflow_id>` → ローカルに保存
2. **構造確認**: `n8n dev show @workflows/edit-{id}.json`
3. **編集**: JSONファイルを修正
4. **差分確認**: `n8n dev diff <workflow_id> @workflows/edit-{id}.json`
5. **プッシュ**: `n8n dev push <workflow_id> @workflows/edit-{id}.json`

#### ローカル同期（バージョン管理）
- `n8n dev pull <workflow_id>` — 単一WFをローカルに保存
- `n8n dev pull-all [-p project_id]` — 全WFを一括取得

### 開発ヘルパーコマンド一覧

```bash
# テンプレート
n8n dev template list                    # テンプレート一覧
n8n dev template show <name>             # テンプレート内容表示
n8n dev template use <name> [--name "WF名"] [-o file]  # テンプレートからWF生成

# 可視化・情報
n8n dev show <json|@file>               # ワークフロー構造をテキストツリーで表示
n8n dev info <json|@file>               # ワークフローサマリー（ノード数、トリガー、クレデンシャル）

# バリデーション・修正
n8n dev validate <json|@file>            # Cloud互換性チェック
n8n dev sanitize <json|@file> [-o file]  # 自動修正して出力

# クレデンシャル
n8n dev scan-credentials                 # インスタンスの全クレデンシャルを収集
n8n dev resolve-credentials <json|@file> # WFに必要なクレデンシャルを解決
n8n dev credential-guide <type>          # クレデンシャルのセットアップ手順を表示

# テスト
n8n dev test-data <json|@file>           # テストデータを自動生成
n8n dev webhook-test <json|@file> [-d data] [--no-wait]  # Webhookテスト実行
n8n dev check-execution <execution_id>   # 実行結果を分析

# デプロイ・有効化
n8n dev preflight <json|@file>           # 全事前チェック（バリデーション+クレデンシャル+依存関係）
n8n dev deploy <json|@file> [-p project_id] [-c type=id] [--activate] [--dry-run]
n8n dev activate <workflow_id>           # 安全確認付きActivation（トリガー影響分析+本番警告）

# ローカル同期
n8n dev pull <workflow_id> [-o dir]      # リモートWFをローカルに保存
n8n dev pull-all [-p project_id] [-o dir] # 全WFを一括取得
n8n dev diff <workflow_id> <local_json>  # リモートとローカルの差分表示
n8n dev push <workflow_id> <local_json> [--force]  # 差分確認付き更新
n8n dev edit <workflow_id>               # 取得→編集→push の便利コマンド

# バージョン管理・ロールバック
n8n dev versions <wf_name>              # ローカルバージョン一覧
n8n dev version-show <wf_name> <ver>    # 特定バージョン表示
n8n dev rollback <workflow_id> <wf_name> [--version N]  # バージョンに復元（ローカル+リモート）

# 一括操作・環境間移行
n8n dev batch-deploy @file1.json @file2.json ... [-p project_id]  # 複数WF一括デプロイ
n8n dev batch-activate <id1> <id2> ...   # 一括有効化
n8n dev batch-deactivate <id1> <id2> ... # 一括無効化
n8n dev migrate <workflow_id> --from <client> --to <client> [-p project_id]  # 環境間移行
n8n dev migrate-all --from <client> --to <client> [-p project_id]  # 全WF環境間移行

# 実行モニタリング
n8n dev watch <workflow_id> [-i interval]  # リアルタイム実行監視（Ctrl+Cで停止）

# 依存関係
n8n dev deps <workflow_id>               # サブWF依存ツリー（上流・下流）

# テスト自動化
n8n dev test-create @workflows/<file>.json [-w workflow_id]  # テストケーステンプレート生成
n8n dev test-run @workflows/tests/<file>.test.json  # テスト実行
n8n dev test-run-all                     # 全テスト一括実行

# 変数同期
n8n dev var-pull [-o output_dir]         # リモート変数をローカルに保存
n8n dev var-push @file                   # ローカル変数をリモートに同期
n8n dev var-diff [@file]                 # 変数の差分表示
n8n dev var-export [--format env|json]   # 変数エクスポート
```

### ドライラン

`n8n dev deploy --dry-run` でデプロイ前に最終確認:
- バリデーション・sanitize・クレデンシャル解決まで実行
- 実際のAPI呼び出しはスキップ
- 最終JSONの概要（ノード数、クレデンシャル、接続）を表示

### バージョン管理・ロールバック

- pull/push/deploy 時に自動でスナップショット保存（`workflows/.versions/`）
- `n8n dev versions` でバージョン履歴確認
- `n8n dev rollback` で任意のバージョンに復元（ローカル+リモート）
- デプロイ失敗時にも rollback_available フラグで復元可能

### 環境間移行

```bash
n8n dev migrate <workflow_id> --from dev --to prod -p <project_id>
```
- ソースからWF取得 → sanitize → ターゲットでクレデンシャル再解決 → デプロイ
- 環境が異なるためクレデンシャルは自動的に再マッチングされる

### 実行モニタリング

`n8n dev watch <workflow_id>` で実行をリアルタイム監視:
- 新しい実行を検出 → 完了時にノード別結果を自動表示
- エラー発生時にハイライト表示
- Ctrl+C で停止

### 依存関係マップ

`n8n dev deps <workflow_id>` でサブWFの依存関係を可視化:
- 下流: このWFが呼ぶサブWF（再帰的）
- 上流: このWFを呼んでいる親WF
- 循環参照を自動検出

### テスト自動化

1. `n8n dev test-create @wf.json` でテストケーステンプレート生成
2. `workflows/tests/` にテストケースを定義
3. `n8n dev test-run` / `test-run-all` で実行（Webhook送信→結果検証）

### 変数同期

環境変数を `workflows/variables/<client>.vars.json` でファイル管理:
- `var-pull` / `var-push` でリモートと同期
- `var-diff` で差分確認
- `var-export --format env` で `.env` 形式出力

### クレデンシャル解決の仕組み

Cloud環境では `GET /credentials` が使えないため:
1. `scan-credentials` でインスタンスの全WFをスキャン → ノードからクレデンシャル情報を収集
2. `resolve-credentials` で新WFが必要とするtypeを自動マッチング
   - **1候補** → 自動適用
   - **複数候補** → ユーザーに選択を求める（`-c type=id` で指定）
   - **0候補** → セットアップ手順を案内（`credential-guide`）
3. `deploy` 時に自動で解決・適用

### テストの仕組み

- `test-data`: ワークフロー構造を解析してテストデータを自動生成
  - Webhookの後続ノード（Code, Set, If等）のコードから参照フィールドを推定
  - フィールド名から型を推定（date→日時, email→メール, id→ID等）
- `webhook-test`: テストデータをwebhook-test URLに送信し、実行結果を自動取得
- `check-execution`: 実行結果をノード別に成否・エラー詳細を表示

## 低レベルAPI操作（`n8n workflow/execution/...`）

直接APIを叩く必要がある場合に使用。通常は `n8n dev` コマンドで十分。

既存ワークフローを別プロジェクトに移動: `n8n workflow transfer <id> <dest_project_id>`

## ワークフロー作成ガイドライン

ワークフローJSONを構築する際は、以下のルールと `docs/` のナレッジを必ず参照すること。

### 必須ルール（Cloud互換性）

- **ノードIDはUUID形式**（`uuid.uuid4()` で生成）。カスタム文字列IDは不可
- **ノードの許可プロパティのみ使用**: `id`, `name`, `parameters`, `position`, `type`, `typeVersion`, `credentials`, `webhookId`, `disabled`, `notesInFlow`, `notes`
  - `retryOnFail`, `maxTries`, `onError` 等は含めない（HTTP 400エラー）
- **動作確認済みtypeVersionを使用**:
  - `code`: 2, `if`: 2.2, `httpRequest`: 4.2, `switch`: 3.2, `set`: 3.4
  - `webhook`: 1, `respondToWebhook`: 1.1, `stickyNote`: 1, `notion`: 2.2
  - `googleCalendarTrigger`: 1（1.2は不可、`pollTimes`必須）

### 命名規則

- **Workflow名**: 日本語、形式 `[カテゴリ] 機能名 - 説明`
- **ノード名**: 処理内容を明確に（デフォルト名は使用しない）
- **変数名**: camelCase
- **ファイル名**: `workflow-[カテゴリ]-[機能名].json`

### 構造設計

- `nodes` 配列にノードを定義
- `connections` でノード間の接続を定義
- `position` は `[x, y]` 座標（左→右の流れ、分岐は上下に展開）
- 1つのWorkflowは1つの責務に集中。複雑な処理はSub-workflowに分割
- JSON引数は直接文字列で渡すか `@ファイルパス` で渡せる

### ノード選択

- **API連携は専用ノード優先**（HTTP Requestは最終手段。使う場合はStickyNoteで理由を説明）
- **Code Nodeは基本Python**（`language: "pythonNative"`）。他ノード参照が必要な場合のみJS

### クレデンシャル

- Cloud環境では `GET /credentials` が使えない → 既存WFのノードから収集する
- デプロイ時にtype別マッチング（詳細は `docs/n8n-deploy-guide.md`）

### エラーハンドリング・セキュリティ

- 全ての外部API呼び出しにError Workflow設定
- Credentialsはn8nの認証情報機能を使用（ハードコード禁止）
- 機密情報はログに出力しない

## ナレッジドキュメント

ワークフロー設計時に参照すべきドキュメント:

| ドキュメント | 内容 |
|---|---|
| `docs/n8n-cloud-constraints.md` | Cloud環境の制約（UUID, 許可プロパティ, typeVersion, Credentials API制限, トラブルシューティング） |
| `docs/n8n-development-rules.md` | 開発ルール（命名規則, 構造設計, ノード選択, セキュリティ, パフォーマンス） |
| `docs/n8n-code-node-reference.md` | Code Node v2 リファレンス（Python/JS対照表, `_items`の使い方, 言語切替の判断基準） |
| `docs/n8n-deploy-guide.md` | デプロイ手順（クレデンシャルマッピング, サブWF依存関係, テスト実行, 更新時の注意） |
| `docs/n8n-node-tips.md` | ノード別Tips（Google Calendar, Notion, Webhook, HTTP Request等の注意点） |

## ファイル構成

- `CLAUDE.md` - このファイル（Claude Code用の指示書）
- `.gitignore` - git管理除外設定
- `.n8n_config.json` - ローカル認証情報（git管理外、複数クライアント対応）
- `n8n_client/` - Python パッケージ
  - `client.py` - n8n API クライアント（全59エンドポイント対応）
  - `config.py` - マルチクライアント設定管理
  - `cli.py` - Click CLI（`n8n` コマンド）
  - `validator.py` - Cloud互換性バリデーション・自動修正
  - `credentials.py` - クレデンシャル収集・解決・セットアップガイド
  - `testing.py` - テストデータ生成・Webhookテスト・実行結果分析
  - `deploy.py` - スマートデプロイ + Activation安全確認 + ドライラン
  - `sync.py` - ローカル同期（pull/push/diff）
  - `templates.py` - ワークフローテンプレート管理
  - `visualize.py` - ワークフロー構造テキスト可視化
  - `versioning.py` - ローカルバージョン管理 + ロールバック
  - `batch.py` - 一括操作（batch deploy/activate）+ 環境間移行
  - `monitoring.py` - 実行モニタリング（watch）
  - `dependencies.py` - サブWF依存関係マップ
  - `test_runner.py` - テスト自動化フレームワーク
  - `var_sync.py` - 環境変数（Variables）同期
- `pyproject.toml` - パッケージ定義
- `docs/` - n8n開発ナレッジ
  - `n8n-cloud-constraints.md` - Cloud制約ガイド
  - `n8n-development-rules.md` - 開発ルール
  - `n8n-code-node-reference.md` - Code Node リファレンス
  - `n8n-deploy-guide.md` - デプロイ・テストガイド
  - `n8n-node-tips.md` - ノード別Tips
- `workflows/` - ワークフロー定義JSONを格納
  - `templates/` - ワークフローテンプレート
    - `webhook-respond.json`, `webhook-slack.json`, `schedule-fetch-notify.json`
    - `trigger-code-action.json`, `sub-workflow.json`
  - `tests/` - テストケース定義（`.test.json`）
  - `variables/` - 環境変数ファイル（`<client_name>.vars.json`）
  - `.versions/` - ローカルバージョン履歴（git管理外）
