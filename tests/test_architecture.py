"""Enforces the layered import contract from AGENTS.md section 6.

Walks the AST of every module under sentinel/ rather than relying on
import-order behavior at runtime, so a circular or upward import is
caught as a static defect regardless of whether anything happens to
exercise that path in another test.
"""

import ast
from pathlib import Path

SENTINEL_ROOT = Path(__file__).resolve().parent.parent / "sentinel"

# AGENTS.md section 6: each layer may import only from layers listed here
# (plus itself, checked separately).
LAYER_ALLOWED: dict[str, set[str]] = {
    "config": set(),
    "models": {"config"},
    "database": {"config", "models"},
    "events": {"config", "models"},
    "state": {"config", "models", "events"},
    "rules": {"config", "models", "events", "state"},
    "camera": {"config", "models", "events"},
    "detection": {"config", "models", "events"},
    "audio": {"config", "models", "events"},
    "services": {
        "config",
        "models",
        "database",
        "events",
        "state",
        "rules",
        "camera",
        "detection",
        "audio",
    },
    "api": {"config", "models", "services", "state"},
    "dashboard": {"config", "models"},
}

# camera and detection own the vision stack; nothing else may reach into it.
CV2_ALLOWED_LAYERS = {"camera", "detection"}

# database owns the ORM; nothing else may touch sqlalchemy directly.
SQLALCHEMY_ALLOWED_LAYERS = {"database"}


def _layer_of(module_path: Path) -> str | None:
    """Return the architectural layer a module belongs to, or None for
    root-level modules (e.g. cli.py) that sit outside the layer tree."""
    relative = module_path.relative_to(SENTINEL_ROOT)
    if len(relative.parts) < 2:
        return None
    layer = relative.parts[0]
    return layer if layer in LAYER_ALLOWED else None


def _sentinel_layers_imported(tree: ast.Module) -> set[str]:
    """Return the recognized layer names imported from `sentinel.*`.

    Root-level modules (e.g. `sentinel.errors`) are not layers and are
    deliberately excluded: they sit outside the tree the contract governs.
    """
    layers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                is_layer = len(parts) >= 2 and parts[0] == "sentinel"
                if is_layer and parts[1] in LAYER_ALLOWED:
                    layers.add(parts[1])
            continue
        else:
            continue
        parts = module.split(".")
        if len(parts) >= 2 and parts[0] == "sentinel" and parts[1] in LAYER_ALLOWED:
            layers.add(parts[1])
    return layers


def _module_names(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return [node.module] if node.module else []


def test_import_contract() -> None:
    violations: list[str] = []
    for path in SENTINEL_ROOT.rglob("*.py"):
        layer = _layer_of(path)
        if layer is None:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        allowed = LAYER_ALLOWED[layer]
        for imported in _sentinel_layers_imported(tree):
            if imported != layer and imported not in allowed:
                violations.append(
                    f"{path.relative_to(SENTINEL_ROOT.parent)} (layer '{layer}') "
                    f"imports forbidden layer 'sentinel.{imported}'"
                )
    assert not violations, "Import contract violations:\n" + "\n".join(violations)


def test_cv2_confined_to_camera_and_detection() -> None:
    violations: list[str] = []
    for path in SENTINEL_ROOT.rglob("*.py"):
        if _layer_of(path) in CV2_ALLOWED_LAYERS:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                names = _module_names(node)
                if any(name == "cv2" or name.startswith("cv2.") for name in names):
                    violations.append(str(path.relative_to(SENTINEL_ROOT.parent)))
    assert not violations, f"cv2 imported outside camera/detection: {violations}"


def test_sqlalchemy_confined_to_database() -> None:
    violations: list[str] = []
    for path in SENTINEL_ROOT.rglob("*.py"):
        if _layer_of(path) in SQLALCHEMY_ALLOWED_LAYERS:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                names = _module_names(node)
                if any(
                    name == "sqlalchemy" or name.startswith("sqlalchemy.")
                    for name in names
                ):
                    violations.append(str(path.relative_to(SENTINEL_ROOT.parent)))
    assert not violations, f"sqlalchemy imported outside database: {violations}"
