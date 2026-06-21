#!/usr/bin/env python3
"""Async request queue for serializing admin API actions."""
import json
import os
import threading
import time
import secrets

from server_config import QUEUE_FILE, log, _error_id

_queue_lock = threading.Lock()

def _load_queue() -> list:
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE) as f:
            items = json.load(f)
        now = time.time()
        items = [i for i in items if now - i.get('created_at', 0) < 300 or i.get('status') in ('processing', 'queued')]
        return items
    except Exception:
        return []

def _save_queue(items: list) -> None:
    with _queue_lock:
        now = time.time()
        items = [i for i in items if now - i.get('created_at', 0) < 300 or i.get('status') in ('processing', 'queued')]
        try:
            with open(QUEUE_FILE, 'w') as f:
                json.dump(items, f, indent=2)
        except Exception:
            pass

_QUEUE_HANDLERS = {}

def _register_handler(typ: str, handler) -> None:
    _QUEUE_HANDLERS[typ] = handler

_queue_event = threading.Event()

def _queue_dispatch(item: dict) -> tuple:
    typ = item.get('type', '')
    body = item.get('payload', {})
    handler = _QUEUE_HANDLERS.get(typ)
    if not handler:
        eid = _error_id()
        return False, {'ok': False, 'message': f'Unknown queue type: {typ}', 'error_id': eid}
    try:
        ok, result = handler(body)
        if not ok and 'error_id' not in result:
            result['error_id'] = _error_id()
        return ok, result
    except Exception as e:
        eid = _error_id()
        log(f"Queue dispatch crash: {typ}: {e} [{eid}]")
        return False, {'ok': False, 'message': str(e)[:200], 'error_id': eid}

def signal_queue() -> None:
    """Wake up the queue processor immediately."""
    _queue_event.set()

def _queue_processor() -> None:
    while True:
        try:
            items = _load_queue()
            # Reset items stuck in processing for >5 min so they can be retried
            now = time.time()
            changed = False
            for i in items:
                if i.get('status') == 'processing' and now - i.get('created_at', 0) > 300:
                    i['status'] = 'queued'
                    i['error'] = 'Reset from stale processing'
                    changed = True
            if changed:
                _save_queue(items)
            found = None
            for i in items:
                if i.get('status') == 'queued':
                    retry_at = i.get('retry_at')
                    if retry_at and retry_at > time.time():
                        continue
                    found = i
                    break
            if found:
                found['status'] = 'processing'
                _save_queue(items)
                try:
                    ok, result = _queue_dispatch(found)
                except Exception as e:
                    eid = _error_id()
                    ok, result = False, {'ok': False, 'message': str(e)[:200], 'error_id': eid}
                found['status'] = 'done' if ok else 'failed'
                found['result'] = result
                if not ok:
                    msg = str(result.get('message', 'Unknown error'))[:170]
                    eid = result.get('error_id', '')
                    if eid:
                        msg += f' [{eid}]'
                    found['error'] = msg
                _save_queue(items)
                log(f"Queue {found['id']}: {found['type']} → {'done' if ok else 'failed'}")
            else:
                _queue_event.wait(1)
                _queue_event.clear()
        except Exception:
            _queue_event.wait(1)
            _queue_event.clear()
