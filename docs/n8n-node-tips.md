# n8n ノード別Tips

特定ノードの注意点・ハマりポイント集。

---

## 1. Google Calendar

### トリガー vs アクション

| | トリガーノード | アクションノード |
|---|---|---|
| type | `n8n-nodes-base.googleCalendarTrigger` | `n8n-nodes-base.googleCalendar` |
| 用途 | イベントの変更を**検知** | イベントを**操作** |
| パラメータ | `triggerOn`: `eventCreated`, `eventUpdated`, `eventCancelled` | `operation`: `create`, `update`, `delete` |
| フロー上の位置 | 起点（トリガー） | 中間・末端（アクション） |

**注意**: `googleCalendar` の `update`/`delete` はアクション。変更を検知するトリガーではない。

### googleCalendarTrigger の設定

- **typeVersion は 1 を使用**（1.2はCloud未対応）
- **`pollTimes` パラメータが必須**

```json
{
  "parameters": {
    "pollTimes": {
      "item": [{ "mode": "everyMinute" }]
    },
    "triggerOn": "eventCreated",
    "calendarId": {
      "__rl": true,
      "mode": "id",
      "value": "user@example.com"
    },
    "options": {}
  },
  "type": "n8n-nodes-base.googleCalendarTrigger",
  "typeVersion": 1
}
```

### responseStatus の変更（制限と回避策）

n8n標準 Google Calendar ノードでは `attendees[].responseStatus` の変更が**未サポート**。

**回避策**: HTTP Request ノードで Calendar API v3 を直接呼び出す。

```
PATCH https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events/{eventId}
```

StickyNote でHTTP Requestを使う理由を説明すること（開発ルール §3.2）。

### attendees フィールドの書き込み可否

| フィールド | 書き込み | 説明 |
|---|---|---|
| `email` | 可 | |
| `responseStatus` | 可 | `needsAction`, `accepted`, `declined`, `tentative` |
| `displayName` | 可 | |
| `optional` | 可 | |
| `resource` | 可 | 会議室リソースか |
| `comment` | 可 | |
| `additionalGuests` | 可 | |
| `self` | **不可** | 読み取り専用 |
| `organizer` | **不可** | 読み取り専用 |
| `id` | **不可** | 読み取り専用 |

読み取り専用フィールドはPATCHボディに含めない。`self` は判定ロジックでのみ使用する。

## 2. Notion Node

- typeVersion: **2.2**
- Notion Integrationの作成・設定が必要
- 接続するデータベース/ページへのIntegration共有設定を忘れずに
- Credential名には接続先ワークスペース名を含める（例: `Notion - プロジェクト管理WS`）

## 3. Webhook Node

- typeVersion: **1**
- デプロイ後のURL: `{base_url}/webhook/{path}`
- テスト用URL: `{base_url}/webhook-test/{path}`

## 4. HTTP Request Node

- typeVersion: **4.2**
- タイムアウト設定推奨: 30秒
- 専用ノードがある場合はそちらを優先（開発ルール §3.2）
- HTTP Requestを使う場合はStickyNoteで理由を説明

## 5. Code Node

- typeVersion: **2**
- 詳細は `n8n-code-node-reference.md` を参照

## 6. Set Node

- typeVersion: **3.4**
- 不要なフィールドの除外に活用（パフォーマンス向上）

## 7. If / Switch Node

- If: typeVersion **2.2**
- Switch: typeVersion **3.2**
- 分岐は上下に展開して配置
