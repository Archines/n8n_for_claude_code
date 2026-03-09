# n8n ワークフロー管理

n8n APIを使ってワークフローの作成・管理・実行を行うスキル。

## 手順

1. まず `n8n config list` を実行してクライアント設定を確認する
2. クライアントが未登録の場合:
   - ユーザーにクライアント名、n8n URL、API Key、説明を質問する
   - `n8n config add <name> <url> <api_key> -d "<desc>"` で登録する（API KeyはmacOS Keychainに保存される）
3. 複数クライアントがある場合:
   - 一覧を表示して「どの環境で作業しますか？」と質問する
   - `n8n config switch <name>` で切り替える
4. `n8n config test` で接続を確認する
5. 接続確認後、ユーザーの要望に応じて作業を進める

## ワークフロー開発フロー

### 1. 設計
- ユーザーの要件をヒアリング
- `docs/` のナレッジを参照してワークフローJSONを設計
- `workflows/` にJSONファイルを作成

### 2. テンプレートから開始（任意）
```bash
n8n dev template list                         # 利用可能なテンプレート一覧
n8n dev template show <name>                  # テンプレート詳細を確認
n8n dev template use <name> -n "WF名"         # テンプレートからWF作成
```

### 3. バリデーション・修正
```bash
n8n dev validate @workflows/<file>.json       # Cloud互換性チェック
n8n dev sanitize @workflows/<file>.json -o workflows/<file>.json  # 自動修正
```

### 4. クレデンシャル解決
```bash
n8n dev resolve-credentials @workflows/<file>.json  # 必要なクレデンシャルを確認・解決
```
- resolved → 自動適用される
- multiple → ユーザーに候補を提示して選択してもらう
- missing → `n8n dev credential-guide <type>` でセットアップ手順を案内

### 5. プリフライトチェック
```bash
n8n dev preflight @workflows/<file>.json      # バリデーション+クレデンシャル+依存関係を一括チェック
```

### 6. デプロイ
```bash
n8n project list                              # デプロイ先を確認
n8n dev deploy @workflows/<file>.json -p <project_id>  # スマートデプロイ
n8n dev deploy @workflows/<file>.json --dry-run  # ドライラン（実際にはデプロイしない）
```
- ユーザーにデプロイ先を質問（プロジェクト or パーソナルフォルダ）
- 手動でクレデンシャルを指定する場合: `-c slackOAuth2Api=<id>`

### 7. テスト
```bash
n8n dev test-data @workflows/<file>.json      # テストデータ自動生成
n8n dev webhook-test @workflows/<file>.json   # Webhookテスト実行→結果確認
n8n dev test-create @workflows/<file>.json    # テストケーステンプレート生成
n8n dev test-run @workflows/tests/<file>.test.json  # テストスイート実行
n8n dev test-run-all                          # 全テスト一括実行
```

### 8. 結果確認・デバッグ
```bash
n8n dev check-execution <execution_id>        # ノード別の成否・エラー詳細
n8n dev watch <workflow_id> [-i 5]            # リアルタイム実行監視
n8n execution list -w <workflow_id>           # 実行履歴
```
- エラーがあれば原因を分析 → WF修正 → 再デプロイ → 再テストのサイクル

### 9. アクティベーション
```bash
n8n dev activate <workflow_id>                # 影響分析付きで有効化（安全確認あり）
```

## 既存ワークフロー操作

### 確認・閲覧
```bash
n8n workflow list                             # 全ワークフロー一覧
n8n dev show <workflow_id>                    # ツリー表示（ノード構成を可視化）
n8n dev info <workflow_id>                    # サマリー表示
n8n dev deps <workflow_id>                    # 依存関係マップ（上流・下流）
```

### ローカル同期（pull/push/diff）
```bash
n8n dev pull <workflow_id>                    # リモート→ローカル (workflows/ に保存)
n8n dev pull-all                              # 全WF一括取得
n8n dev diff <workflow_id> @workflows/<file>.json  # リモート vs ローカルの差分
n8n dev push @workflows/<file>.json <workflow_id>  # ローカル→リモートに反映
```

### 編集
```bash
n8n dev edit <workflow_id> --name "新名前"     # 名前変更
n8n dev edit <workflow_id> --tag <tag_id>      # タグ追加
n8n dev edit <workflow_id> --active true       # 有効化
```

### バージョン管理・ロールバック
```bash
n8n dev versions <wf_name>                    # ローカルバージョン一覧
n8n dev version-show <wf_name> <version>      # 特定バージョン表示
n8n dev rollback <workflow_id> <wf_name> [--version N]  # バージョンに復元
```

### 一括操作・環境間移行
```bash
n8n dev batch-deploy @file1.json @file2.json [-p project_id]  # 一括デプロイ
n8n dev batch-activate <id1> <id2> ...        # 一括有効化
n8n dev batch-deactivate <id1> <id2> ...      # 一括無効化
n8n dev migrate <workflow_id> --from <client> --to <client>  # 環境間移行
n8n dev migrate-all --from <client> --to <client>  # 全WF環境間移行
```

### 変数同期
```bash
n8n dev var-pull [-o output_dir]              # リモート変数→ローカル
n8n dev var-push @file                        # ローカル変数→リモート
n8n dev var-diff [@file]                      # 変数の差分表示
n8n dev var-export [--format env|json]        # 変数エクスポート
```

## 注意事項

- ワークフローJSON作成時は `docs/n8n-cloud-constraints.md` の制約に必ず従うこと
- ノードIDは必ずUUID形式
- 許可プロパティ以外は含めない
- 動作確認済みtypeVersionを使用
- Code Nodeは基本Python (`pythonNative`)。他ノード参照が必要な場合のみJS
- API連携は専用ノード優先（HTTP Requestは最終手段、StickyNoteで理由を説明）
- `n8n dev activate` は影響分析を表示するので、本番環境では必ず確認してからactivateする
- `--dry-run` でデプロイ前に最終確認を推奨
