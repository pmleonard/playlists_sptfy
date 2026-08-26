import json
import os
import tempfile
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data")).resolve()


def _safe_path(rel_path: str) -> Path:
    resolved = (DATA_ROOT / rel_path).resolve()
    if not str(resolved).startswith(str(DATA_ROOT)):
        raise ValueError(f"Path traversal detected: {rel_path}")
    return resolved


def read_json(rel_path: str):
    return json.loads(_safe_path(rel_path).read_text(encoding="utf-8"))


def write_json(rel_path: str, data) -> None:
    target = _safe_path(rel_path)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, target)
    except Exception:
        os.unlink(tmp_path)
        raise


def read_txt(rel_path: str) -> str:
    return _safe_path(rel_path).read_text(encoding="utf-8")


def write_txt(rel_path: str, content: str) -> None:
    target = _safe_path(rel_path)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        os.unlink(tmp_path)
        raise


def list_txt_files(rel_dir: str) -> list:
    d = _safe_path(rel_dir)
    return sorted(p.stem for p in d.glob("*.txt") if p.is_file())


def delete_file(rel_path: str) -> None:
    _safe_path(rel_path).unlink()
