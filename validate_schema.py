# validate_schema.py
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, List

from jsonschema import Draft202012Validator

Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def fail(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[name-defined]
    # Using a tiny shim so Pylance knows we always sys.exit here
    print(f"ERROR: {msg}")
    sys.exit(code)  # no return


def require(cond: bool, msg: str) -> None:
    if not cond:
        fail(msg)


def repo_root_from(start: Path) -> Path:
    """
    Find the repo root containing 'schemas' and 'examples' folders,
    starting at 'start' and walking upward at most 5 levels.
    Guaranteed non-None (exits on failure).
    """
    p = start
    for _ in range(6):
        if (p / "schemas").exists() and (p / "examples").exists():
            return p
        p = p.parent
    fail("Could not find repo root with 'schemas' and 'examples' folders.")


def load_json(path: Path, label: str) -> Json:
    if not path.exists():
        fail(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        fail(f"Failed to read {label} at {path}: {e}")
    try:
        return json.loads(text)
    except Exception as e:
        fail(f"Failed to parse {label} at {path}: {e}")
    # unreachable
    return None  # type: ignore[return-value]


def json_pointer(e_path: List[Union[str, int]]) -> str:
    """
    Format a jsonschema error path like $.a[0].b
    """
    out = "$"
    for seg in e_path:
        if isinstance(seg, int):
            out += f"[{seg}]"
        else:
            # escape dots minimally (schema keys don’t contain quotes here)
            out += f".{seg}"
    return out


def main() -> None:
    # Allow running from repo root or a subfolder (like /src)
    cwd = Path.cwd()
    root = repo_root_from(cwd)

    schema_path = root / "schemas" / "aave-hf-snapshot.schema.json"

    # Data file may be provided as argv[1]; otherwise default to examples/sample-response.json
    if len(sys.argv) > 1:
        data_path = Path(sys.argv[1])
        if not data_path.is_absolute():
            data_path = (cwd / data_path).resolve()
    else:
        data_path = (root / "examples" / "sample-response.json").resolve()

    schema = load_json(schema_path, "schema")
    data = load_json(data_path, "data")

    # Type enforcement for Pylance: jsonschema expects Mapping[str, Any] (dict) schema
    if not isinstance(schema, dict):
        fail("Schema root must be a JSON object (dict).")
    # Data can be any JSON value; for our use it should be an object
    if not isinstance(data, dict):
        fail("Snapshot root must be a JSON object (dict).")

    # Validate schema first, then the instance
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        fail(f"Schema is invalid for Draft 2020-12: {e}")

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if errors:
        print("❌ Snapshot does NOT match schema.")
        for e in errors[:15]:
            path = json_pointer(list(e.path))
            # Some errors carry a 'context' with more details (e.g., anyOf/oneOf)
            ctx = ""
            if getattr(e, "context", None):
                ctx_msgs = "; ".join(c.message for c in e.context if getattr(c, "message", None))
                if ctx_msgs:
                    ctx = f" | context: {ctx_msgs}"
            print(f" - {path}: {e.message}{ctx}")
        if len(errors) > 15:
            print(f" ... and {len(errors) - 15} more errors")
        sys.exit(2)

    print("✅ OK: snapshot matches schema.")
    print(f"network={data.get('network')}, chain_id={data.get('chain_id')}, address={data.get('address')}")
    # Optional: quick section sanity
    for section in ("user", "totals", "collateral", "debt", "oracles", "config", "meta"):
        print(f" • has {section}: {section in data}")


# ---- Python <3.11 compatibility for NoReturn shim ----
try:
    from typing import NoReturn  # noqa: F401
except Exception:  # pragma: no cover
    pass


if __name__ == "__main__":
    main()
