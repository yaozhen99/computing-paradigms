import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "_policy"
WINDOW_DIR = ROOT / "_windows"
PACKET_DIR = WINDOW_DIR / "packets"


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(text)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_project_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return ROOT / path


def validate_member(kind, value, known):
    if value not in known:
        options = ", ".join(sorted(known))
        raise SystemExit(f"Unknown {kind}: {value}\nKnown {kind}s: {options}")


def load_policy_bundle():
    return {
        "rooms": load_json(POLICY_DIR / "rooms.json"),
        "roles": load_json(POLICY_DIR / "roles.json"),
        "matrix": load_json(POLICY_DIR / "permission_matrix.json"),
        "versions": load_json(POLICY_DIR / "policy_versions.json"),
    }


def load_window_registry():
    return load_json(WINDOW_DIR / "window_registry.json")


def write_window_registry(registry):
    write_json(WINDOW_DIR / "window_registry.json", registry)


def find_window(registry, window_id):
    for window in registry.get("windows", []):
        if window["window_id"] == window_id:
            return window
    return None

