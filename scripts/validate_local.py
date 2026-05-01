"""Local validation helper for SmartCharge CI-relevant checks.

This script is a non-Docker approximation of the repository's GitHub Actions.
It validates:
- JSON syntax for Home Assistant metadata files
- translation key parity between strings.json and translations/en.json
- Black formatting
- flake8 linting
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "smartcharge"
STRINGS_FILE = COMPONENT / "strings.json"
EN_TRANSLATION_FILE = COMPONENT / "translations" / "en.json"
MANIFEST_FILE = COMPONENT / "manifest.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _collect_key_paths(data: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            current = f"{prefix}.{key}" if prefix else key
            paths.add(current)
            paths.update(_collect_key_paths(value, current))
    return paths


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    required_keys = {
        "domain",
        "name",
        "config_flow",
        "documentation",
        "issue_tracker",
        "iot_class",
        "version",
    }
    errors: list[str] = []
    missing = sorted(required_keys - set(manifest))
    if missing:
        errors.append(f"manifest.json is missing keys: {', '.join(missing)}")
    return errors


def _validate_translation_shape(
    strings_data: dict[str, Any],
    translation_data: dict[str, Any],
) -> list[str]:
    expected_paths = _collect_key_paths(strings_data)
    actual_paths = _collect_key_paths(translation_data)

    missing = sorted(expected_paths - actual_paths)
    extra = sorted(actual_paths - expected_paths)

    errors: list[str] = []
    if missing:
        errors.append(
            "translations/en.json is missing keys: " + ", ".join(missing[:20])
        )
    if extra:
        errors.append(
            "translations/en.json has extra keys: " + ", ".join(extra[:20])
        )
    return errors


def _run_command(command: list[str]) -> list[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []

    output = result.stdout.strip()
    error_output = result.stderr.strip()
    lines = [line for line in [output, error_output] if line]
    if not lines:
        lines = [f"Command failed: {' '.join(command)}"]
    return lines


def main() -> int:
    errors: list[str] = []

    try:
        manifest = _load_json(MANIFEST_FILE)
        strings_data = _load_json(STRINGS_FILE)
        translation_data = _load_json(EN_TRANSLATION_FILE)
    except json.JSONDecodeError as err:
        print(f"JSON parsing failed: {err}")
        return 1
    except FileNotFoundError as err:
        print(f"Required file not found: {err}")
        return 1

    errors.extend(_validate_manifest(manifest))
    errors.extend(_validate_translation_shape(strings_data, translation_data))

    errors.extend(_run_command([sys.executable, "-m", "black", "--check", str(COMPONENT)]))
    errors.extend(
        _run_command(
            [
                sys.executable,
                "-m",
                "flake8",
                str(COMPONENT),
                "--max-line-length=88",
            ]
        )
    )

    if errors:
        print("Local validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Local validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())