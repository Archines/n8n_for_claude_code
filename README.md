# n8n for Claude Code

Claude Code から n8n ワークフローの作成・管理・実行を自動化する CLI ツール。

n8n の全 59 API エンドポイントに対応し、複数クライアント環境の切り替え、Cloud 互換性の自動バリデーション、クレデンシャル自動解決、テスト自動化など、開発に必要な機能を網羅しています。

## 特徴

- **全 59 API エンドポイント対応** - Workflow, Execution, Credential, Project, Tag, User, Variable, DataTable, Audit, SourceControl
- **マルチクライアント** - 複数の n8n 環境（開発・本番・クライアント別）を切り替えて管理
- **スマートデプロイ** - バリデーション → クレデンシャル解決 → デプロイを一括実行
- **Cloud 互換性** - UUID、許可プロパティ、typeVersion を自動チェック・修正
- **テスト自動化** - テストデータ生成、Webhook テスト、テストスイート実行
- **バージョン管理** - ローカルでの世代管理とロールバック
- **環境間移行** - dev → prod へのワークフロー移行（クレデンシャル自動再解決）
- **実行モニタリング** - リアルタイムでの実行監視
- **依存関係可視化** - サブワークフローの上流・下流をツリー表示
- **変数同期** - 環境変数のファイル管理とリモート同期
- **Claude Code スキル** - `/n8n` コマンドで対話的にワークフロー開発

## セットアップ

### 前提条件

- Python 3.10+
- macOS（API Key の保存に Keychain を使用）
- n8n インスタンス（Cloud or Self-hosted）と API Key

### インストール

```bash
git clone https://github.com/Archines/n8n_for_claude_code.git
cd n8n_for_claude_code
pip install -e .
```

### クライアント登録

```bash
# クライアント追加（API Key は macOS Keychain に安全に保存されます）
n8n config add my_client https://my-instance.n8n.cloud YOUR_API_KEY -d "本番環境"

# 接続テスト
n8n config test

# 複数環境の場合
n8n config add dev http://localhost:5678 DEV_API_KEY -d "開発環境"
n8n config switch dev

# 既存のプレーンテキストKeyをKeychainに移行
n8n config migrate-keys
```

API Key は n8n の **Settings > API** から発行できます。
設定ファイル（`.n8n_config.json`）には URL と説明のみ保存され、API Key は macOS Keychain に保存されます。

## 使い方

### Claude Code から使う

Claude Code で `/n8n` スキルを呼び出すと、接続設定から開発フローまで対話的に進められます。

### CLI として使う

#### ワークフロー開発フロー

```bash
# 1. テンプレートから開始
n8n dev template list
n8n dev template use webhook-slack --name "[Slack] 通知WF" -o workflows/slack-notify.json

# 2. バリデーション・修正
n8n dev validate @workflows/slack-notify.json
n8n dev sanitize @workflows/slack-notify.json -o workflows/slack-notify.json

# 3. クレデンシャル解決
n8n dev resolve-credentials @workflows/slack-notify.json

# 4. プリフライトチェック（一括）
n8n dev preflight @workflows/slack-notify.json

# 5. ドライランで確認
n8n dev deploy @workflows/slack-notify.json --dry-run

# 6. デプロイ
n8n dev deploy @workflows/slack-notify.json -p <project_id>

# 7. テスト
n8n dev webhook-test @workflows/slack-notify.json

# 8. 結果確認
n8n dev check-execution <execution_id>

# 9. 有効化（影響分析付き）
n8n dev activate <workflow_id>
```

#### 既存ワークフローの操作

```bash
# 一覧・確認
n8n workflow list
n8n dev show <workflow_id>       # ツリー表示
n8n dev info <workflow_id>       # サマリー
n8n dev deps <workflow_id>       # 依存関係

# ローカル同期
n8n dev pull <workflow_id>       # リモート → ローカル
n8n dev pull-all                 # 全WF一括取得
n8n dev diff <id> @file.json     # 差分確認
n8n dev push <id> @file.json     # ローカル → リモート

# バージョン管理
n8n dev versions <wf_name>       # バージョン一覧
n8n dev rollback <id> <wf_name>  # ロールバック
```

#### 一括操作・環境間移行

```bash
# 一括デプロイ
n8n dev batch-deploy @wf1.json @wf2.json @wf3.json -p <project_id>

# 一括 activate/deactivate
n8n dev batch-activate <id1> <id2> <id3>

# 環境間移行（dev → prod）
n8n dev migrate <workflow_id> --from dev --to prod
n8n dev migrate-all --from dev --to prod
```

#### テスト自動化

```bash
# テストケーステンプレート生成
n8n dev test-create @workflows/my-wf.json

# テスト実行
n8n dev test-run @workflows/tests/my-wf.test.json

# 全テスト一括実行
n8n dev test-run-all
```

#### 実行モニタリング

```bash
# リアルタイム監視（Ctrl+C で停止）
n8n dev watch <workflow_id> -i 5
```

#### 変数同期

```bash
n8n dev var-pull                      # リモート → ローカル
n8n dev var-push @vars.json           # ローカル → リモート
n8n dev var-diff                      # 差分確認
n8n dev var-export --format env       # .env 形式で出力
```

## プロジェクト構成

```
n8n_for_claude_code/
├── CLAUDE.md                    # Claude Code 用指示書
├── README.md                    # このファイル
├── pyproject.toml               # パッケージ定義
├── .claude/commands/n8n.md      # /n8n スキル定義
├── n8n_client/                  # Python パッケージ
│   ├── client.py                #   API クライアント (59 endpoints)
│   ├── config.py                #   マルチクライアント設定管理
│   ├── cli.py                   #   Click CLI
│   ├── validator.py             #   Cloud 互換性バリデーション
│   ├── credentials.py           #   クレデンシャル解決
│   ├── testing.py               #   テストデータ生成・Webhook テスト
│   ├── deploy.py                #   スマートデプロイ・ドライラン
│   ├── sync.py                  #   ローカル同期 (pull/push/diff)
│   ├── templates.py             #   テンプレート管理
│   ├── visualize.py             #   ワークフロー可視化
│   ├── versioning.py            #   バージョン管理・ロールバック
│   ├── batch.py                 #   一括操作・環境間移行
│   ├── monitoring.py            #   実行モニタリング
│   ├── dependencies.py          #   依存関係マップ
│   ├── test_runner.py           #   テスト自動化
│   └── var_sync.py              #   変数同期
├── docs/                        # n8n 開発ナレッジ
│   ├── n8n-cloud-constraints.md #   Cloud 制約ガイド
│   ├── n8n-development-rules.md #   開発ルール
│   ├── n8n-code-node-reference.md #  Code Node リファレンス
│   ├── n8n-deploy-guide.md      #   デプロイガイド
│   └── n8n-node-tips.md         #   ノード別 Tips
└── workflows/                   # ワークフロー JSON
    ├── templates/               #   テンプレート (5 種)
    ├── tests/                   #   テストケース
    └── variables/               #   環境変数ファイル
```

## n8n Cloud の注意点

- ノード ID は **UUID 形式** 必須（カスタム文字列 ID は不可）
- ノードには **許可プロパティのみ** 使用可能（`retryOnFail` 等は HTTP 400 エラー）
- `GET /credentials` API は Cloud 環境で **405 エラー** を返すため、既存ワークフローからクレデンシャル情報をスキャンして代替
- 詳細は `docs/n8n-cloud-constraints.md` を参照

## ライセンス

Private
