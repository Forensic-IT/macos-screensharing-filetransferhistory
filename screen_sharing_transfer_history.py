#!/usr/bin/env python3
"""Extract macOS Screen Sharing FileTransferHistory from a plist.

Uses Python's standard library only. The JSON output contains artifact values
such as paths, names, and counters; treat it as sensitive case data and do not
share it without review. The script does not contact a network or modify input.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, plistlib, posixpath, re, sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, bytes): return {"__type__": "data", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict): return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_value(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)): return value
    return {"__type__": type(value).__name__, "repr": repr(value)}

def normalize_root(root: str | None) -> str | None:
    if root is None: return None
    if not root.startswith("/") or root.startswith("//") or "\x00" in root: raise ValueError("Path roots must be absolute POSIX paths")
    if any(part == ".." for part in root.split("/")): raise ValueError("Path roots must not contain parent-directory segments")
    normalized = posixpath.normpath(root)
    if normalized == "/": raise ValueError("A filesystem root is too broad for classification")
    return normalized

def is_same_or_child(path: str, root: str) -> bool: return path == root or path.startswith(root.rstrip("/") + "/")

def validate_roots(local_root, remote_root):
    local, remote = normalize_root(local_root), normalize_root(remote_root)
    if bool(local) != bool(remote): raise ValueError("Provide both --local-root and --remote-root, or neither")
    if local and remote and (is_same_or_child(local, remote) or is_same_or_child(remote, local)): raise ValueError("Local and remote path roots must be distinct and non-overlapping")
    return local, remote

def path_role(value, local_root, remote_root):
    if not isinstance(value, str) or not value: return "missing"
    if not value.startswith("/") or value.startswith("//") or "\x00" in value or any(p == ".." for p in value.split("/")): return "unmapped"
    normalized = posixpath.normpath(value)
    if local_root and is_same_or_child(normalized, local_root): return "local"
    if remote_root and is_same_or_child(normalized, remote_root): return "remote"
    return "unmapped"

def path_direction(source, destination):
    if source == "local" and destination == "remote": return "local_to_remote_path"
    if source == "remote" and destination == "local": return "remote_to_local_path"
    if source == destination and source in {"local", "remote"}: return "same_root_path"
    return "unresolved_path_roots"

def parse_plist(path, local_root, remote_root):
    raw = path.read_bytes(); outer = plistlib.loads(raw)
    if not isinstance(outer, dict): raise ValueError("Outer plist is not a dictionary")
    embedded = outer.get("connectionsStore")
    if isinstance(embedded, (bytes, bytearray)): store, embedded_type = plistlib.loads(embedded), "embedded plist data"
    elif isinstance(embedded, dict): store, embedded_type = embedded, "dictionary"
    else: store, embedded_type = None, "missing or unsupported"
    if store is not None and not isinstance(store, dict): raise ValueError("connectionsStore did not decode to a dictionary")
    rows = outer.get("FileTransferHistory")
    if rows is not None and not isinstance(rows, list): raise ValueError("FileTransferHistory is present but is not an array")
    rows = rows or []; records = []
    for number, item in enumerate(rows, 1):
        if not isinstance(item, dict): records.append({"record_index": number, "record_value": json_value(item)}); continue
        record = {str(k): json_value(v) for k, v in item.items()}
        source, destination = path_role(item.get("sourcePath"), local_root, remote_root), path_role(item.get("destinationPath"), local_root, remote_root)
        if local_root and remote_root:
            record.update(path_based_source_role=source, path_based_destination_role=destination, path_based_direction=path_direction(source, destination))
        record["record_index"] = number; records.append(record)
    timestamp_like_fields = sorted({str(k) for item in rows if isinstance(item, dict) for k in item if re.search(r"date|time|timestamp", str(k), re.I)})
    store_keys = sorted(str(k) for k in store) if isinstance(store, dict) else []
    details = store.get("connectionDetails") if isinstance(store, dict) else None
    return {"source_file_name": path.name, "source_sha256": hashlib.sha256(raw).hexdigest(), "connectionsStore_type": embedded_type, "connectionsStore_key_names": store_keys, "saved_connection_record_count": len(details) if isinstance(details, dict) else None, "FileTransferHistory_present": "FileTransferHistory" in outer, "FileTransferHistory_record_count": len(rows), "FileTransferHistory_timestamp_like_fields": timestamp_like_fields, "records": records, "direction_and_state_codes_interpreted": False, "interpretation_limits": ["Path-root direction is a classification of recorded source/destination paths only.", "Paths and byte counters alone do not prove completion, receipt, byte identity, owner, user identity, authorization, or exact timing.", "Undocumented direction/state codes are preserved raw and not interpreted.", "A missing timestamp-like field does not establish when an operation occurred."]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plist", type=Path, help="Path to a Screen Sharing preference plist")
    parser.add_argument("-o", "--output", type=Path, help="Write JSON to a new file; default is stdout")
    parser.add_argument("--local-root", help="Optional local user-home path prefix for path-only direction labels")
    parser.add_argument("--remote-root", help="Optional remote user-home path prefix for path-only direction labels")
    args = parser.parse_args()
    try:
        local_root, remote_root = validate_roots(args.local_root, args.remote_root)
        rendered = json.dumps(parse_plist(args.plist, local_root, remote_root), indent=2, ensure_ascii=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as destination: destination.write(rendered)
            print("Wrote JSON report. Review it for sensitive values before sharing.")
        else: sys.stdout.write(rendered)
    except (OSError, plistlib.InvalidFileException, ValueError) as error: parser.error(str(error))
    return 0

if __name__ == "__main__": raise SystemExit(main())
