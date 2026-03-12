from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _load_env_file(env_path: Path) -> None:
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env_file(_BACKEND_ROOT / ".env")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile and run the NEMSIS local Schematron kit against a local XML payload.",
    )
    parser.add_argument("--xml-file", required=True, help="Path to the XML file to validate.")
    parser.add_argument(
        "--dataset-type",
        choices=("DEM", "EMS", "dem", "ems"),
        default="",
        help="Optional dataset type override. Defaults to auto-detect from the XML root element.",
    )
    parser.add_argument(
        "--rule-file",
        default="",
        help="Optional Schematron rule file name or absolute path. Defaults to the sample rule for the dataset type.",
    )
    parser.add_argument(
        "--schematron-dir",
        default=os.getenv("NEMSIS_LOCAL_SCHEMATRON_DIR", ""),
        help="Path to the extracted NEMSIS Schematron kit directory.",
    )
    parser.add_argument(
        "--saxon-jar-path",
        default=os.getenv("NEMSIS_SAXON_JAR_PATH", ""),
        help="Optional Saxon HE jar path when saxonche is not installed.",
    )
    parser.add_argument(
        "--include-svrl",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Include raw SVRL output in the JSON response.",
    )
    parser.add_argument(
        "--output-svrl",
        default="",
        help="Optional file path to write the raw SVRL report.",
    )
    return parser


def main() -> int:
    from core_app.nemsis.local_schematron import (
        LocalSchematronRunnerError,
        NEMSISLocalSchematronRunner,
    )

    parser = _build_parser()
    args = parser.parse_args()

    xml_path = Path(args.xml_file).expanduser()
    if not xml_path.is_file():
        parser.error(f"XML file not found: {xml_path}")

    runner = NEMSISLocalSchematronRunner(
        schematron_dir=args.schematron_dir or None,
        saxon_jar_path=args.saxon_jar_path or None,
    )

    try:
        result = runner.validate_xml_bytes(
            xml_path.read_bytes(),
            dataset_type=args.dataset_type or None,
            rule_file=args.rule_file or None,
        )
    except LocalSchematronRunnerError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        return 1

    if args.output_svrl:
        output_path = Path(args.output_svrl).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.svrl_xml, encoding="utf-8")

    print(json.dumps(result.to_dict(include_svrl=args.include_svrl), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())