"""Execution monitoring — poll for new executions and report status."""

from __future__ import annotations

import time
from datetime import datetime

from n8n_client.client import N8nClient
from n8n_client.testing import analyze_execution, format_execution_summary


def format_execution_event(execution: dict) -> str:
    """Format an execution event as a timestamped log line.

    - Started:   [HH:MM:SS] Execution #ID started
    - Completed: [HH:MM:SS] Execution #ID completed (success/error) - duration
    - Error:     [HH:MM:SS] ERROR: message
    """
    now = datetime.now().strftime("%H:%M:%S")
    ex_id = execution.get("id", "?")
    status = execution.get("status", "unknown")

    if status == "running":
        return f"[{now}] Execution #{ex_id} started"

    started_at = execution.get("startedAt", "")
    stopped_at = execution.get("stoppedAt", "")
    duration = ""
    if started_at and stopped_at:
        try:
            fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
            s = datetime.strptime(started_at, fmt)
            e = datetime.strptime(stopped_at, fmt)
            secs = (e - s).total_seconds()
            duration = f" - {secs:.1f}s"
        except (ValueError, TypeError):
            pass

    if status == "error":
        data = execution.get("data", {})
        result_data = data.get("resultData", {})
        error = result_data.get("error", {})
        msg = error.get("message", "") if isinstance(error, dict) else str(error)
        line = f"[{now}] Execution #{ex_id} completed (error){duration}"
        if msg:
            line += f"\n[{now}] ERROR: {msg}"
        return line

    return f"[{now}] Execution #{ex_id} completed ({status}){duration}"


def watch_executions(
    client: N8nClient,
    workflow_id: str,
    interval: int = 5,
    callback=None,
) -> None:
    """Poll for new executions and report them.

    1. Record the latest execution ID at start
    2. Poll every `interval` seconds
    3. Report new executions via callback (or print)
    4. Stop on KeyboardInterrupt
    """
    # Record existing execution IDs
    seen_ids: set[str] = set()
    try:
        existing = client.list_executions(workflow_id=workflow_id, limit=10)
        for ex in existing.get("data", []):
            seen_ids.add(str(ex.get("id", "")))
    except Exception:
        pass

    def _report(msg: str):
        if callback:
            callback(msg)
        else:
            print(msg)

    try:
        while True:
            time.sleep(interval)
            try:
                recent = client.list_executions(workflow_id=workflow_id, limit=10)
            except Exception as e:
                _report(f"[{datetime.now().strftime('%H:%M:%S')}] Poll error: {e}")
                continue

            for ex in reversed(recent.get("data", [])):
                ex_id = str(ex.get("id", ""))
                if not ex_id or ex_id in seen_ids:
                    continue

                seen_ids.add(ex_id)
                status = ex.get("status", "")

                if status == "running":
                    _report(format_execution_event(ex))
                    # Wait for completion
                    while True:
                        time.sleep(interval)
                        try:
                            detail = client.get_execution(ex_id, include_data=True)
                        except Exception:
                            break
                        detail_status = detail.get("status", "")
                        if detail_status in ("success", "error", "canceled"):
                            _report(format_execution_event(detail))
                            if detail_status in ("success", "error"):
                                analysis = analyze_execution(detail)
                                _report(format_execution_summary(analysis))
                            break
                else:
                    _report(format_execution_event(ex))
                    if status in ("success", "error"):
                        try:
                            detail = client.get_execution(ex_id, include_data=True)
                            analysis = analyze_execution(detail)
                            _report(format_execution_summary(analysis))
                        except Exception:
                            pass

    except KeyboardInterrupt:
        pass
