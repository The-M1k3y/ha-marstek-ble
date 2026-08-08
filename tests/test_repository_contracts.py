"""Repository, packaging and translation contracts for the integration."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "marstek_ble"
ORIGINAL_MODULES = {
    "__init__.py",
    "binary_sensor.py",
    "button.py",
    "config_flow.py",
    "const.py",
    "coordinator.py",
    "diagnostics.py",
    "marstek_device.py",
    "select.py",
    "sensor.py",
    "switch.py",
}
PLATFORM_MODULES = {"sensor", "binary_sensor", "button", "switch", "select"}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not a literal assignment in {path}")


def test_manifest_hacs_and_package_directory_agree() -> None:
    manifest = _read_json(INTEGRATION / "manifest.json")
    hacs = _read_json(ROOT / "hacs.json")

    assert manifest["domain"] == INTEGRATION.name
    assert manifest["name"] == hacs["name"]
    assert hacs["filename"] == INTEGRATION.name
    assert hacs["content_in_root"] is False
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "local_polling"
    assert manifest["requirements"] == []
    assert re.fullmatch(
        r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",
        manifest["version"],
    )


def test_manifest_bluetooth_patterns_cover_original_discovery_prefixes() -> None:
    manifest = _read_json(INTEGRATION / "manifest.json")
    prefixes = _literal_assignment(INTEGRATION / "const.py", "DEVICE_PREFIXES")
    patterns = {item["local_name"] for item in manifest["bluetooth"]}

    assert patterns == {f"{prefix}*" for prefix in prefixes}


def test_declared_platforms_have_modules_and_setup_entrypoints() -> None:
    source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    platforms: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "Platform"
        ):
            platforms.add(node.attr.lower())

    assert platforms == PLATFORM_MODULES
    for platform in platforms:
        path = INTEGRATION / f"{platform}.py"
        assert path.is_file()
        module_tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        functions = {
            node.name
            for node in module_tree.body
            if isinstance(node, ast.AsyncFunctionDef)
        }
        assert "async_setup_entry" in functions


def test_config_flow_abort_reasons_and_steps_have_strings() -> None:
    source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
    strings = _read_json(INTEGRATION / "strings.json")
    abort_reasons = set(
        re.findall(r'async_abort\(reason="([^"]+)"\)', source)
    )
    step_ids = set(re.findall(r'step_id="([^"]+)"', source))

    assert abort_reasons <= set(strings["config"]["abort"])
    assert {"user", "bluetooth_confirm"} <= set(strings["config"]["step"])
    assert "init" in strings["options"]["step"]
    assert step_ids <= {"user", "bluetooth_confirm", "init"}


def test_legacy_modules_only_cross_product_boundary_for_selection() -> None:
    """Only setup and discovery may select runtime products during migration."""

    selection_modules = {"__init__.py", "config_flow.py"}
    forbidden = {"schema", "entity", "products", "product_runtime"}
    for filename in ORIGINAL_MODULES - selection_modules:
        path = INTEGRATION / filename
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                module_root = (node.module or "").split(".", 1)[0]
                assert module_root not in forbidden, (
                    f"{path} imports .{node.module}"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if "custom_components" in parts and "marstek_ble" in parts:
                        assert forbidden.isdisjoint(parts), (
                            f"{path} imports {alias.name}"
                        )

    for filename in selection_modules:
        tree = ast.parse(
            (INTEGRATION / filename).read_text(encoding="utf-8")
        )
        imported_roots = {
            (node.module or "").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level
        }
        assert "products" in imported_roots

    setup_tree = ast.parse(
        (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    )
    setup_imports = {
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(setup_tree)
        if isinstance(node, ast.ImportFrom) and node.level
    }
    assert "product_coordinator" in setup_imports


def test_original_python_sources_compile_without_importing_dependencies() -> None:
    paths = [INTEGRATION / name for name in ORIGINAL_MODULES]
    paths.extend(
        [
            INTEGRATION / "product_runtime.py",
            INTEGRATION / "product_coordinator.py",
            INTEGRATION / "products" / "venus_runtime.py",
            ROOT / "standalone_test" / "marstek_basic_info.py",
            ROOT / "conftest.py",
        ]
    )

    for path in paths:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_coverage_configuration_has_no_source_omissions() -> None:
    coverage = (ROOT / ".coveragerc").read_text(encoding="utf-8")

    assert not re.search(r"(?m)^\s*omit\s*=", coverage)
    assert "custom_components/marstek_ble/" not in coverage.partition("[report]")[0].replace(
        "custom_components/marstek_ble\n", ""
    )
