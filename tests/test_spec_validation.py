from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import cast

import yaml

from lattice_aka_repro.spec_validation import (
    SpecValidationResult,
    validate_specs,
    write_validation_outputs,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPECS_DIR = _REPO_ROOT / "specs"


def test_current_specs_have_expected_warnings_only() -> None:
    result = validate_specs(specs_dir=_SPECS_DIR, repo_root=_REPO_ROOT)

    assert result.passed
    assert result.unexpected_errors == []
    warning_codes = Counter(issue.code for issue in result.expected_warnings)
    assert warning_codes == Counter(
        {
            "C2LAKE_PAPER_Q_COMPOSITE": 9,
            "LCLA_PAPER_Q_COMPOSITE": 2,
            "LCLA_PAPER_PERFORMANCE_DIMENSION_CONFLICT": 1,
        }
    )


def test_c2lake_benchmark_n_relation_is_enforced(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "c2lake" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["paper_literal_m32"]["n"] = 641
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "C2LAKE_N_RELATION_INVALID", "paper_literal_m32")


def test_audited_nonprime_q_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "c2lake" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["audited_prime_m32"]["q"] = 1024
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "C2LAKE_AUDITED_Q_NOT_PRIME", "audited_prime_m32")


def test_audited_prime_flag_false_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "c2lake" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["audited_prime_m32"]["q_must_be_prime"] = False
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "AUDITED_Q_MUST_BE_PRIME_FLAG_FALSE", "audited_prime_m32")


def test_lcla_audited_flag_false_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "lcla_aka" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["audited_preserve_keylen"]["q_must_be_prime"] = False
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "AUDITED_Q_MUST_BE_PRIME_FLAG_FALSE", "audited_preserve_keylen")


def test_duplicate_shape_symbol_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    shape_path = specs_dir / "lcla_aka" / "shape_table.csv"
    original = shape_path.read_text(encoding="utf-8-sig")
    duplicate = "n,duplicate symbol,scalar,Z+,public,profile,duplicate for test,test\n"
    shape_path.write_text(f"{original.rstrip()}\n{duplicate}", encoding="utf-8")

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "SHAPE_SYMBOL_DUPLICATE", "n")


def test_shape_source_is_required(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    shape_path = specs_dir / "lcla_aka" / "shape_table.csv"
    _clear_shape_source(shape_path, "E_A")

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "CSV_REQUIRED_FIELD_EMPTY", "row 16")


def test_invalid_claim_class_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    claims_path = specs_dir / "lcla_aka" / "claims_matrix.csv"
    text = claims_path.read_text(encoding="utf-8-sig")
    claims_path.write_text(
        text.replace("executable/structural", "security-proof", 1), encoding="utf-8"
    )

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "CLAIM_CLASS_INVALID", "LCLA-R1-TRANSCRIPT")


def test_invalid_lcla_backend_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "lcla_aka" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["toy"]["backend"] = "made_up"
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "PROFILE_BACKEND_INVALID", "toy")


def test_invalid_profile_family_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "lcla_aka" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["toy"]["family"] = "invalid_family"
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "PROFILE_FAMILY_INVALID", "toy")


def test_invalid_numeric_profile_field_type_is_unexpected_error(tmp_path: Path) -> None:
    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "c2lake" / "parameter_profiles.yaml"
    document = _read_profile_yaml(profile_path)
    document["profiles"]["toy"]["m"] = "8"
    _write_profile_yaml(profile_path, document)

    result = validate_specs(specs_dir=specs_dir, repo_root=_REPO_ROOT)

    assert _has_error(result, "PROFILE_FIELD_TYPE_INVALID", "toy")


def test_validation_outputs_are_written(tmp_path: Path) -> None:
    result = validate_specs(specs_dir=_SPECS_DIR, repo_root=_REPO_ROOT)
    json_output = tmp_path / "spec_validation.json"
    report_output = tmp_path / "spec_validation.md"

    write_validation_outputs(result, json_output=json_output, report_output=report_output)

    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["result"] == "pass"
    assert payload["summary"]["unexpected_error_count"] == 0
    finding_names = {finding["name"] for finding in payload["required_findings"]}
    assert "c2lake_n_equals_ceil_4m_log2m" in finding_names
    assert "LCLA_PAPER_PERFORMANCE_DIMENSION_CONFLICT" in report_output.read_text(encoding="utf-8")


def _copy_specs(tmp_path: Path) -> Path:
    destination = tmp_path / "specs"
    shutil.copytree(_SPECS_DIR, destination)
    return destination


def _read_profile_yaml(path: Path) -> dict[str, dict[str, dict[str, object]]]:
    return cast(
        dict[str, dict[str, dict[str, object]]],
        yaml.safe_load(path.read_text(encoding="utf-8")),
    )


def _write_profile_yaml(path: Path, document: dict[str, dict[str, dict[str, object]]]) -> None:
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _clear_shape_source(path: Path, symbol: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        assert fieldnames is not None
        rows = [{field: row.get(field) or "" for field in fieldnames} for row in reader]
    matched = False
    for row in rows:
        if row["symbol"] == symbol:
            row["source"] = ""
            matched = True
    assert matched
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _has_error(result: SpecValidationResult, code: str, subject: str) -> bool:
    return any(
        error.code == code and error.subject == subject for error in result.unexpected_errors
    )
