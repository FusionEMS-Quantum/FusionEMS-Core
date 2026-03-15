from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import defusedxml.ElementTree as _defused_et

from core_app.core.config import get_settings
from core_app.nemsis.validator import ValidationIssue, _ui_info

try:
    from saxonche import PySaxonProcessor

    _SAXONCHE_AVAILABLE = True
except ImportError:
    _SAXONCHE_AVAILABLE = False

_ELEMENT_ID_RE = re.compile(r"([de][A-Za-z]+\.\d{2})")


class LocalSchematronRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalSchematronValidationResult:
    valid: bool
    dataset_type: str
    rule_file: str
    issues: list[ValidationIssue]
    compiled_schema_path: str
    compiled_stylesheet_path: str
    svrl_xml: str

    def to_dict(self, *, include_svrl: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "valid": self.valid,
            "dataset_type": self.dataset_type,
            "rule_file": self.rule_file,
            "issues": [issue.to_dict() for issue in self.issues],
            "stage_results": {
                "local_schematron": {
                    "passed": self.valid,
                    "issue_count": len(self.issues),
                    "rule_file": self.rule_file,
                    "compiled_schema_path": self.compiled_schema_path,
                    "compiled_stylesheet_path": self.compiled_stylesheet_path,
                }
            },
        }
        if include_svrl:
            payload["svrl_xml"] = self.svrl_xml
        return payload


class NEMSISLocalSchematronRunner:
    def __init__(
        self,
        *,
        schematron_dir: str | None = None,
        saxon_jar_path: str | None = None,
    ) -> None:
        settings = get_settings()
        configured_dir = schematron_dir or settings.nemsis_local_schematron_dir
        self._schematron_dir = Path(configured_dir).expanduser() if configured_dir else None
        configured_jar = saxon_jar_path or settings.nemsis_saxon_jar_path
        self._saxon_jar_path = Path(configured_jar).expanduser() if configured_jar else None

    def validate_xml_bytes(
        self,
        xml_bytes: bytes,
        *,
        dataset_type: str | None = None,
        rule_file: str | None = None,
    ) -> LocalSchematronValidationResult:
        resolved_dataset_type = (dataset_type or self._detect_dataset_type(xml_bytes)).upper()
        with tempfile.TemporaryDirectory(prefix="fusionems_schematron_") as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "input.xml"
            xml_path.write_bytes(xml_bytes)
            rule_path = self._resolve_rule_path(resolved_dataset_type, rule_file)
            compiled_schema_path, compiled_stylesheet_path = self._compile_rule(rule_path, temp_path)
            svrl_xml = self._run_validation(xml_path, compiled_stylesheet_path)
        issues = self._parse_svrl(svrl_xml)
        return LocalSchematronValidationResult(
            valid=not any(issue.severity == "error" for issue in issues),
            dataset_type=resolved_dataset_type,
            rule_file=rule_path.name,
            issues=issues,
            compiled_schema_path=str(compiled_schema_path),
            compiled_stylesheet_path=str(compiled_stylesheet_path),
            svrl_xml=svrl_xml,
        )

    def _detect_dataset_type(self, xml_bytes: bytes) -> str:
        try:
            root = _defused_et.fromstring(xml_bytes)
        except ET.ParseError as exc:
            raise LocalSchematronRunnerError(f"XML parsing failed before Schematron validation: {exc}") from exc
        local_name = self._local_name(root.tag)
        if local_name == "DEMDataSet":
            return "DEM"
        if local_name == "EMSDataSet":
            return "EMS"
        raise LocalSchematronRunnerError(
            f"Unable to infer dataset type from root element '{local_name}'. Use --dataset-type explicitly."
        )

    def _resolve_rule_path(self, dataset_type: str, rule_file: str | None) -> Path:
        schematron_dir = self._require_schematron_dir()
        rules_dir = schematron_dir / "rules"
        if rule_file:
            candidate = Path(rule_file).expanduser()
            if candidate.is_file():
                return candidate
            candidate = rules_dir / rule_file
            if candidate.is_file():
                return candidate
            raise LocalSchematronRunnerError(f"Schematron rule file not found: {rule_file}")
        defaults = {
            "DEM": "SampleDEMDataSet.sch",
            "EMS": "SampleEMSDataSet.sch",
        }
        default_name = defaults.get(dataset_type.upper())
        if default_name is None:
            raise LocalSchematronRunnerError(
                f"Unsupported dataset type '{dataset_type}'. Expected DEM or EMS."
            )
        candidate = rules_dir / default_name
        if not candidate.is_file():
            raise LocalSchematronRunnerError(f"Default Schematron rule not found: {candidate}")
        return candidate

    def _compile_rule(self, rule_path: Path, output_dir: Path) -> tuple[Path, Path]:
        schematron_dir = self._require_schematron_dir()
        xslt_dir = schematron_dir / "utilities" / "iso-schematron-xslt2"
        include_xsl = xslt_dir / "iso_dsdl_include.xsl"
        expand_xsl = xslt_dir / "iso_abstract_expand.xsl"
        compile_xsl = xslt_dir / "iso_svrl_for_xslt2.xsl"
        for required_path in (include_xsl, expand_xsl, compile_xsl):
            if not required_path.is_file():
                raise LocalSchematronRunnerError(f"Required Schematron compiler asset not found: {required_path}")

        stage_one_path = output_dir / f"{rule_path.stem}.stage1.sch"
        compiled_schema_path = output_dir / f"{rule_path.stem}.compiled.sch"
        compiled_stylesheet_path = output_dir / f"{rule_path.stem}.compiled.xsl"

        self._transform_to_file(include_xsl, rule_path, stage_one_path)
        self._transform_to_file(expand_xsl, stage_one_path, compiled_schema_path)
        self._transform_to_file(
            compile_xsl,
            compiled_schema_path,
            compiled_stylesheet_path,
            parameters={"allow-foreign": "true"},
        )
        return compiled_schema_path, compiled_stylesheet_path

    def _run_validation(self, xml_path: Path, compiled_stylesheet_path: Path) -> str:
        output_path = compiled_stylesheet_path.with_suffix(".svrl")
        self._transform_to_file(compiled_stylesheet_path, xml_path, output_path)
        return output_path.read_text(encoding="utf-8")

    def _transform_to_file(
        self,
        stylesheet_path: Path,
        source_path: Path,
        output_path: Path,
        *,
        parameters: dict[str, str] | None = None,
    ) -> None:
        if _SAXONCHE_AVAILABLE:
            self._transform_with_saxonche(
                stylesheet_path,
                source_path,
                output_path,
                parameters=parameters or {},
            )
            return
        self._transform_with_java(
            stylesheet_path,
            source_path,
            output_path,
            parameters=parameters or {},
        )

    def _transform_with_saxonche(
        self,
        stylesheet_path: Path,
        source_path: Path,
        output_path: Path,
        *,
        parameters: dict[str, str],
    ) -> None:
        with PySaxonProcessor(license=False) as processor:
            xslt_processor = processor.new_xslt30_processor()
            for name, value in parameters.items():
                xslt_processor.set_parameter(name, processor.make_string_value(value))
            xslt_processor.transform_to_file(
                source_file=str(source_path),
                stylesheet_file=str(stylesheet_path),
                output_file=str(output_path),
            )

    def _transform_with_java(
        self,
        stylesheet_path: Path,
        source_path: Path,
        output_path: Path,
        *,
        parameters: dict[str, str],
    ) -> None:
        java_path = shutil.which("java")
        if java_path is None:
            raise LocalSchematronRunnerError(
                "Java is not available. Install saxonche or configure Java plus NEMSIS_SAXON_JAR_PATH."
            )
        if self._saxon_jar_path is None or not self._saxon_jar_path.is_file():
            raise LocalSchematronRunnerError(
                "No XSLT2 engine is configured. Install saxonche or set NEMSIS_SAXON_JAR_PATH to a Saxon HE jar."
            )
        command = [
            java_path,
            "-jar",
            str(self._saxon_jar_path),
            "-versionmsg:off",
            f"-xsl:{stylesheet_path}",
            f"-s:{source_path}",
            f"-o:{output_path}",
        ]
        for name, value in parameters.items():
            command.append(f"{name}={value}")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "Unknown Saxon failure"
            raise LocalSchematronRunnerError(stderr)

    def _parse_svrl(self, svrl_xml: str) -> list[ValidationIssue]:
        try:
            root = _defused_et.fromstring(svrl_xml.encode("utf-8"))
        except ET.ParseError as exc:
            raise LocalSchematronRunnerError(f"SVRL parsing failed: {exc}") from exc
        issues: list[ValidationIssue] = []
        for node in root.iter():
            local_name = self._local_name(node.tag)
            if local_name not in {"failed-assert", "successful-report"}:
                continue
            location = node.attrib.get("location", "")
            role = node.attrib.get("role", "")
            message = self._extract_message(node)
            element_id = self._extract_element_id(location)
            ui_section, _ui_label = _ui_info(element_id) if element_id else ("Schematron", "Schematron")
            issues.append(
                ValidationIssue(
                    severity=self._severity_from_role(role, local_name),
                    stage="local_schematron",
                    rule_id=node.attrib.get("id", "SCHEMATRON"),
                    element_id=element_id,
                    xpath=location or "/",
                    ui_section=ui_section,
                    plain_message=message,
                    technical_message=f"{message} (location: {location or 'n/a'})",
                    rule_source="NEMSIS Local Schematron",
                    fix_hint="Review the Schematron assertion text and the reported XPath location.",
                )
            )
        return issues

    def _extract_message(self, node: ET.Element) -> str:
        text_fragments: list[str] = []
        for child in list(node):
            if self._local_name(child.tag) == "text":
                text = " ".join("".join(child.itertext()).split())
                if text:
                    text_fragments.append(text)
        if text_fragments:
            return " ".join(text_fragments)
        return " ".join("".join(node.itertext()).split())

    def _extract_element_id(self, location: str) -> str:
        matches = _ELEMENT_ID_RE.findall(location)
        return matches[-1] if matches else "schematron"

    def _severity_from_role(self, role: str, local_name: str) -> str:
        normalized = role.upper()
        if "FATAL" in normalized or "ERROR" in normalized:
            return "error"
        if "WARNING" in normalized or local_name == "successful-report":
            return "warning"
        return "error" if local_name == "failed-assert" else "warning"

    def _require_schematron_dir(self) -> Path:
        if self._schematron_dir is None:
            raise LocalSchematronRunnerError(
                "NEMSIS local Schematron directory is not configured. Set NEMSIS_LOCAL_SCHEMATRON_DIR or pass --schematron-dir."
            )
        if not self._schematron_dir.is_dir():
            raise LocalSchematronRunnerError(
                f"Configured Schematron directory does not exist: {self._schematron_dir}"
            )
        return self._schematron_dir

    def _local_name(self, tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag
