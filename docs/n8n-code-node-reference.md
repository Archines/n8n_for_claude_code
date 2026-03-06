# n8n Code Node v2 リファレンス

Code Node（typeVersion: 2）でのPython / JavaScript実装の注意点。

---

## 1. Python vs JavaScript 対照表

| 操作 | Python (`pythonNative`) | JavaScript |
|------|------------------------|------------|
| 入力データ（1件目） | `_items[0]["json"]` | `$input.first().json` |
| 入力データ（全件ループ） | `for item in _items` | `for (const item of $input.all())` |
| 他ノードの出力参照 | **不可** | `$node['ノード名'].first().json` |
| JSONの `language` 値 | `"pythonNative"` | 省略可（デフォルト） |

## 2. Python 注意点

### `_input` は存在しない

```python
# NG - name '_input' is not defined
event = _input.first().json

# OK
event = _items[0]["json"]
```

### `_node` は存在しない（他ノード参照不可）

```python
# NG - name '_node' is not defined
data = _node['変更イベント整形'].first().json
```

他ノードの出力を参照する必要がある場合は **JavaScript に切り替える**:
```javascript
// OK
const data = $node['変更イベント整形'].first().json;
```

### language 値は `"pythonNative"` が正しい

`"python"` や `"Python"` では動作しない。

```json
{
  "parameters": {
    "language": "pythonNative",
    "pythonCode": "..."
  }
}
```

## 3. Python 実践パターン

```python
# 入力データ取得（1件目）
data = _items[0]["json"]

# 全件ループ
for item in _items:
    json_data = item.get("json", {})
    # 処理...

# 結果を返す
return [{"json": {"key": "value"}}]
```

## 4. Code Nodeの選択基準

- **基本はPythonを使用**（開発ルール §3.1）
- **JavaScriptに切り替えるケース**:
  - 他ノードの出力を参照する必要がある場合（`$node['名前']`）
  - Python では `_node` が使えないため
