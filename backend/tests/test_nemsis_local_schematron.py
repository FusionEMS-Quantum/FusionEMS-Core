from __future__ import annotations

from pathlib import Path

import pytest

from core_app.nemsis.local_schematron import NEMSISLocalSchematronRunner


def test_local_schematron_runner_uses_dataset_default_rule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schematron_dir = tmp_path / "Schematron"
    rules_dir = schematron_dir / "rules"
    utilities_dir = schematron_dir / "utilities" / "iso-schematron-xslt2"
    rules_dir.mkdir(parents=True)
    utilities_dir.mkdir(parents=True)
    (rules_dir / "SampleDEMDataSet.sch").write_text("<schema/>", encoding="utf-8")

    runner = NEMSISLocalSchematronRunner(schematron_dir=str(schematron_dir))

    def _fake_compile_rule(rule_path: Path, output_dir: Path) -> tuple[Path, Path]:
        compiled_schema = output_dir / f"{rule_path.stem}.compiled.sch"
        compiled_stylesheet = output_dir / f"{rule_path.stem}.compiled.xsl"
        compiled_schema.write_text("compiled", encoding="utf-8")
        compiled_stylesheet.write_text("compiled", encoding="utf-8")
        return compiled_schema, compiled_stylesheet

    monkeypatch.setattr(runner, "_compile_rule", _fake_compile_rule)
    monkeypatch.setattr(
        runner,
        "_run_validation",
        lambda xml_path, compiled_stylesheet_path: (
            '<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">'
            '<svrl:failed-assert id="sample_d001" role="[ERROR]" location="/*:DEMDataSet/*:DemographicReport/*:dAgency/*:dAgency.04[1]">'
            '<svrl:text>Agency state is required.</svrl:text>'
            '</svrl:failed-assert>'
            '</svrl:schematron-output>'
        ),
    )

    result = runner.validate_xml_bytes(
        b'<DEMDataSet xmlns="http://www.nemsis.org"><DemographicReport/></DEMDataSet>'
    )

    assert result.dataset_type == "DEM"
    assert result.rule_file == "SampleDEMDataSet.sch"
    assert result.valid is False
    assert result.issues[0].rule_id == "sample_d001"
    assert result.issues[0].stage == "local_schematron"


def test_local_schematron_runner_requires_configured_directory() -> None:
    runner = NEMSISLocalSchematronRunner(schematron_dir="")

    with pytest.raises(RuntimeError):
        runner.validate_xml_bytes(b'<DEMDataSet xmlns="http://www.nemsis.org"/>', dataset_type="DEM")