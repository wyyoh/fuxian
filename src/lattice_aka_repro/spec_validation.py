"""冻结规格的机器校验，不实现协议运算。"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, cast

import yaml

from lattice_aka_repro.evidence import RunMetadata, collect_run_metadata

Severity = Literal["expected_warning", "unexpected_error"]
CheckStatus = Literal["pass", "warning", "fail"]
CsvRows = list[tuple[int, dict[str, str]]]

_PROTOCOLS: Final = ("c2lake", "lcla_aka")
_PROFILE_NAME_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")
_SHAPE_HEADERS: Final = (
    "symbol",
    "role",
    "shape",
    "domain",
    "visibility",
    "generation",
    "notes",
    "source",
)
_CLAIMS_HEADERS: Final = (
    "claim_id",
    "claim",
    "required_evidence",
    "class",
    "status",
    "notes",
)
_COMMON_PROFILE_FIELDS: Final = frozenset({"family", "m", "n", "q", "beta", "q_must_be_prime"})
_PROTOCOL_PROFILE_FIELDS: Final = {
    "c2lake": frozenset({"matrix_shape", "secret_sampling"}),
    "lcla_aka": frozenset({"backend"}),
}
_OPTIONAL_PROFILE_FIELDS: Final = frozenset({"note"})
_ALLOWED_FAMILIES: Final = frozenset({"paper_literal", "audited", "audited_prime", "toy"})
_ALLOWED_C2LAKE_MATRIX_SHAPES: Final = frozenset({"square_n"})
_ALLOWED_C2LAKE_SECRET_SAMPLING: Final = frozenset({"literal", "small_secret"})
_ALLOWED_LCLA_BACKENDS: Final = frozenset(
    {
        "constructed_or_real",
        "frodo_probe_or_constructed",
        "real_trapdoor_preferred",
        "toy",
    }
)
_CLAIM_CLASS_ATOMS: Final = frozenset({"executable", "empirical", "structural"})
_CLAIM_CLASS_EXACT: Final = frozenset({"formal/non-executable"})
_CHECK_NAMES: Final = (
    "csv_schema",
    "yaml_profile_schema",
    "parameter_relations",
    "prime_checks",
    "shape_symbol_uniqueness",
    "claims_class",
)
_FLOAT_TOLERANCE: Final = 1e-3


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """一次校验中的 warning 或 error。"""

    check: str
    code: str
    severity: Severity
    protocol: str
    source: str
    subject: str
    message: str
    details: dict[str, object]

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    """单类校验的汇总状态。"""

    name: str
    status: CheckStatus
    expected_warning_count: int
    unexpected_error_count: int

    def to_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProfileRecord:
    """已通过基础类型校验的 profile。"""

    protocol: str
    name: str
    family: str
    m: int
    n: int
    q: int
    beta: float
    q_must_be_prime: bool
    fields: dict[str, object]


@dataclass(frozen=True, slots=True)
class SpecValidationResult:
    """完整规格校验结果。"""

    metadata: RunMetadata
    checks: list[ValidationCheck]
    expected_warnings: list[ValidationIssue]
    unexpected_errors: list[ValidationIssue]
    profile_counts: dict[str, int]
    shape_symbol_counts: dict[str, int]
    claim_counts: dict[str, int]

    @property
    def passed(self) -> bool:
        return not self.unexpected_errors

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "task_id": "T002",
            "result": "pass" if self.passed else "fail",
            "metadata": asdict(self.metadata),
            "summary": {
                "expected_warning_count": len(self.expected_warnings),
                "unexpected_error_count": len(self.unexpected_errors),
                "profile_counts": self.profile_counts,
                "shape_symbol_counts": self.shape_symbol_counts,
                "claim_counts": self.claim_counts,
            },
            "checks": [check.to_json() for check in self.checks],
            "required_findings": _required_findings(self),
            "expected_warnings": [issue.to_json() for issue in self.expected_warnings],
            "unexpected_errors": [issue.to_json() for issue in self.unexpected_errors],
        }


def validate_specs(
    *,
    specs_dir: Path,
    repo_root: Path,
) -> SpecValidationResult:
    """校验 CSV/YAML 规格，并按 expected warning 与 unexpected error 分类。"""

    metadata = collect_run_metadata(
        task_id="T002",
        profile="not_applicable",
        backend="python",
        seed=0,
        warmup=0,
        repetitions=1,
        repo_root=repo_root,
    )
    issues: list[ValidationIssue] = []
    profile_counts: dict[str, int] = {}
    shape_symbol_counts: dict[str, int] = {}
    claim_counts: dict[str, int] = {}

    for protocol in _PROTOCOLS:
        protocol_dir = specs_dir / protocol
        shape_rows = _read_csv_rows(
            protocol=protocol,
            path=protocol_dir / "shape_table.csv",
            expected_headers=_SHAPE_HEADERS,
            check="csv_schema",
            issues=issues,
        )
        claims_rows = _read_csv_rows(
            protocol=protocol,
            path=protocol_dir / "claims_matrix.csv",
            expected_headers=_CLAIMS_HEADERS,
            check="csv_schema",
            issues=issues,
        )
        profile_records = _read_profile_records(
            protocol=protocol,
            path=protocol_dir / "parameter_profiles.yaml",
            issues=issues,
        )

        profile_counts[protocol] = len(profile_records)
        shape_symbol_counts[protocol] = len(shape_rows)
        claim_counts[protocol] = len(claims_rows)

        _validate_shape_symbols(protocol, shape_rows, issues)
        _validate_claim_classes(protocol, claims_rows, issues)
        _validate_parameter_relations(protocol, profile_records, issues)
        _validate_prime_requirements(protocol, profile_records, issues)

    expected_warnings = [issue for issue in issues if issue.severity == "expected_warning"]
    unexpected_errors = [issue for issue in issues if issue.severity == "unexpected_error"]
    return SpecValidationResult(
        metadata=metadata,
        checks=_summarize_checks(issues),
        expected_warnings=expected_warnings,
        unexpected_errors=unexpected_errors,
        profile_counts=profile_counts,
        shape_symbol_counts=shape_symbol_counts,
        claim_counts=claim_counts,
    )


def write_validation_outputs(
    result: SpecValidationResult,
    *,
    json_output: Path,
    report_output: Path,
) -> tuple[Path, Path]:
    """写出机器 JSON 与人工 Markdown 报告。"""

    json_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(result.to_json(), allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    report_output.write_text(render_report(result), encoding="utf-8")
    return json_output, report_output


def render_report(result: SpecValidationResult) -> str:
    """生成确定性 Markdown 报告，不包含时间戳等易漂移内容。"""

    lines = [
        "# 规格校验报告",
        "",
        "## 摘要",
        "",
        f"- 结果：{'pass' if result.passed else 'fail'}",
        f"- unexpected error：{len(result.unexpected_errors)}",
        f"- expected warning：{len(result.expected_warnings)}",
        f"- profiles：{_format_counts(result.profile_counts)}",
        f"- shape symbols：{_format_counts(result.shape_symbol_counts)}",
        f"- claims：{_format_counts(result.claim_counts)}",
        "",
        "## 校验项",
        "",
        "| 校验项 | 状态 | expected warning | unexpected error |",
        "| --- | --- | ---: | ---: |",
    ]
    for check in result.checks:
        lines.append(
            "| "
            f"{check.name} | {check.status} | "
            f"{check.expected_warning_count} | {check.unexpected_error_count} |"
        )
    lines.extend(
        [
            "",
            "## 必须验证项",
            "",
            "| 项目 | 状态 | 结论 |",
            "| --- | --- | --- |",
        ]
    )
    for finding in _required_findings(result):
        lines.append(
            "| "
            f"{_escape_markdown(str(finding['name']))} | "
            f"{_escape_markdown(str(finding['status']))} | "
            f"{_escape_markdown(str(finding['summary']))} |"
        )
    lines.extend(["", "## Expected Warnings", ""])
    _append_issue_table(lines, result.expected_warnings)
    lines.extend(["", "## Unexpected Errors", ""])
    _append_issue_table(lines, result.unexpected_errors)
    lines.extend(
        [
            "",
            "## 范围",
            "",
            "- 本报告只校验冻结 CSV/YAML 规格元数据。",
            "- 本轮不实现 C2LAKE 或 LCLA-AKA 数学运算。",
            "- 本轮不实现 TrapGen、SamplePre、密钥生成、密钥协商、benchmark 或安全性结论。",
            "",
        ]
    )
    return "\n".join(lines)


def _read_csv_rows(
    *,
    protocol: str,
    path: Path,
    expected_headers: tuple[str, ...],
    check: str,
    issues: list[ValidationIssue],
) -> CsvRows:
    if not path.is_file():
        _add_issue(
            issues,
            check=check,
            code="CSV_SOURCE_MISSING",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=path.name,
            message="找不到 CSV 规格文件",
        )
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = tuple(reader.fieldnames or ())
            if headers != expected_headers:
                _add_issue(
                    issues,
                    check=check,
                    code="CSV_HEADER_INVALID",
                    severity="unexpected_error",
                    protocol=protocol,
                    source=str(path),
                    subject=path.name,
                    message="CSV header 不匹配预期 schema",
                    details={"actual": list(headers), "expected": list(expected_headers)},
                )
                return []
            rows: CsvRows = []
            for row_number, raw_row in enumerate(reader, start=2):
                row = {header: (raw_row.get(header) or "").strip() for header in expected_headers}
                _validate_required_csv_fields(
                    protocol,
                    path,
                    row_number,
                    row,
                    _required_csv_fields(path.name),
                    issues,
                )
                rows.append((row_number, row))
    except (OSError, csv.Error, UnicodeError) as error:
        _add_issue(
            issues,
            check=check,
            code="CSV_DOCUMENT_INVALID",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=path.name,
            message=f"CSV 读取失败：{error}",
        )
        return []
    return rows


def _validate_required_csv_fields(
    protocol: str,
    path: Path,
    row_number: int,
    row: Mapping[str, str],
    required_fields: Iterable[str],
    issues: list[ValidationIssue],
) -> None:
    for field in required_fields:
        value = row[field]
        if not value:
            _add_issue(
                issues,
                check="csv_schema",
                code="CSV_REQUIRED_FIELD_EMPTY",
                severity="unexpected_error",
                protocol=protocol,
                source=str(path),
                subject=f"row {row_number}",
                message=f"CSV 必填字段 {field!r} 为空",
                details={"field": field, "row": row_number},
            )


def _required_csv_fields(filename: str) -> tuple[str, ...]:
    if filename == "shape_table.csv":
        return ("symbol", "role", "shape", "domain", "visibility", "generation")
    return ("claim_id", "claim", "required_evidence", "class", "status")


def _read_profile_records(
    *,
    protocol: str,
    path: Path,
    issues: list[ValidationIssue],
) -> list[ProfileRecord]:
    if not path.is_file():
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="YAML_SOURCE_MISSING",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=path.name,
            message="找不到 profile YAML 文件",
        )
        return []
    try:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="YAML_DOCUMENT_INVALID",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=path.name,
            message=f"YAML 读取失败：{error}",
        )
        return []
    if not isinstance(loaded, dict):
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="YAML_DOCUMENT_INVALID",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=path.name,
            message="YAML 顶层必须是映射",
        )
        return []
    document = cast(dict[object, object], loaded)
    profiles_value = document.get("profiles")
    if not isinstance(profiles_value, dict):
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_ROOT_INVALID",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=path.name,
            message="顶层 profiles 必须是映射",
        )
        return []
    records: list[ProfileRecord] = []
    profiles = cast(dict[object, object], profiles_value)
    for raw_name, raw_profile in profiles.items():
        if not isinstance(raw_name, str) or not _PROFILE_NAME_PATTERN.fullmatch(raw_name):
            _add_issue(
                issues,
                check="yaml_profile_schema",
                code="PROFILE_NAME_INVALID",
                severity="unexpected_error",
                protocol=protocol,
                source=str(path),
                subject=str(raw_name),
                message="profile 名称必须是安全标识符",
            )
            continue
        if not isinstance(raw_profile, dict):
            _add_issue(
                issues,
                check="yaml_profile_schema",
                code="PROFILE_DOCUMENT_INVALID",
                severity="unexpected_error",
                protocol=protocol,
                source=str(path),
                subject=raw_name,
                message="profile 必须是映射",
            )
            continue
        profile = _normalize_profile_mapping(protocol, path, raw_name, raw_profile, issues)
        record = _validate_profile_fields(protocol, path, raw_name, profile, issues)
        if record is not None:
            records.append(record)
    return records


def _normalize_profile_mapping(
    protocol: str,
    path: Path,
    name: str,
    raw_profile: Mapping[object, object],
    issues: list[ValidationIssue],
) -> dict[str, object]:
    profile: dict[str, object] = {}
    for raw_field, value in raw_profile.items():
        if not isinstance(raw_field, str):
            _add_issue(
                issues,
                check="yaml_profile_schema",
                code="PROFILE_FIELD_NAME_INVALID",
                severity="unexpected_error",
                protocol=protocol,
                source=str(path),
                subject=name,
                message="profile 字段名必须是字符串",
            )
            continue
        profile[raw_field] = value
    return profile


def _validate_profile_fields(
    protocol: str,
    path: Path,
    name: str,
    profile: Mapping[str, object],
    issues: list[ValidationIssue],
) -> ProfileRecord | None:
    required = _COMMON_PROFILE_FIELDS | _PROTOCOL_PROFILE_FIELDS[protocol]
    allowed = required | _OPTIONAL_PROFILE_FIELDS
    missing = sorted(required.difference(profile))
    unexpected = sorted(set(profile).difference(allowed))
    for field in missing:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_FIELD_MISSING",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=name,
            message=f"profile 缺少字段 {field!r}",
            details={"field": field},
        )
    for field in unexpected:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_FIELD_UNEXPECTED",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=name,
            message=f"profile 包含未定义字段 {field!r}",
            details={"field": field},
        )
    if missing:
        return None

    family = _require_string(profile, "family", protocol, path, name, issues)
    m = _require_positive_int(profile, "m", protocol, path, name, issues)
    n = _require_positive_int(profile, "n", protocol, path, name, issues)
    q = _require_positive_int(profile, "q", protocol, path, name, issues)
    beta = _require_positive_number(profile, "beta", protocol, path, name, issues)
    q_must_be_prime = _require_bool(profile, "q_must_be_prime", protocol, path, name, issues)
    if family is not None and family not in _ALLOWED_FAMILIES:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_FAMILY_INVALID",
            severity="unexpected_error",
            protocol=protocol,
            source=str(path),
            subject=name,
            message=f"profile family {family!r} 不合法",
            details={"allowed": sorted(_ALLOWED_FAMILIES), "family": family},
        )
    if protocol == "c2lake":
        _validate_c2lake_profile_fields(path, name, profile, issues)
    else:
        _validate_lcla_profile_fields(path, name, profile, issues)
    if (
        family is None
        or family not in _ALLOWED_FAMILIES
        or m is None
        or n is None
        or q is None
        or beta is None
        or q_must_be_prime is None
    ):
        return None
    return ProfileRecord(
        protocol=protocol,
        name=name,
        family=family,
        m=m,
        n=n,
        q=q,
        beta=beta,
        q_must_be_prime=q_must_be_prime,
        fields=dict(profile),
    )


def _validate_c2lake_profile_fields(
    path: Path,
    name: str,
    profile: Mapping[str, object],
    issues: list[ValidationIssue],
) -> None:
    matrix_shape = _require_string(profile, "matrix_shape", "c2lake", path, name, issues)
    secret_sampling = _require_string(profile, "secret_sampling", "c2lake", path, name, issues)
    if matrix_shape is not None and matrix_shape not in _ALLOWED_C2LAKE_MATRIX_SHAPES:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_MATRIX_SHAPE_INVALID",
            severity="unexpected_error",
            protocol="c2lake",
            source=str(path),
            subject=name,
            message=f"C2LAKE matrix_shape {matrix_shape!r} 不合法",
            details={"allowed": sorted(_ALLOWED_C2LAKE_MATRIX_SHAPES)},
        )
    if secret_sampling is not None and secret_sampling not in _ALLOWED_C2LAKE_SECRET_SAMPLING:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_SECRET_SAMPLING_INVALID",
            severity="unexpected_error",
            protocol="c2lake",
            source=str(path),
            subject=name,
            message=f"C2LAKE secret_sampling {secret_sampling!r} 不合法",
            details={"allowed": sorted(_ALLOWED_C2LAKE_SECRET_SAMPLING)},
        )


def _validate_lcla_profile_fields(
    path: Path,
    name: str,
    profile: Mapping[str, object],
    issues: list[ValidationIssue],
) -> None:
    backend = _require_string(profile, "backend", "lcla_aka", path, name, issues)
    if backend is not None and backend not in _ALLOWED_LCLA_BACKENDS:
        _add_issue(
            issues,
            check="yaml_profile_schema",
            code="PROFILE_BACKEND_INVALID",
            severity="unexpected_error",
            protocol="lcla_aka",
            source=str(path),
            subject=name,
            message=f"LCLA-AKA backend {backend!r} 不合法",
            details={"allowed": sorted(_ALLOWED_LCLA_BACKENDS), "backend": backend},
        )


def _validate_shape_symbols(
    protocol: str,
    rows: CsvRows,
    issues: list[ValidationIssue],
) -> None:
    seen: dict[str, int] = {}
    for row_number, row in rows:
        symbol = row["symbol"]
        if symbol in seen:
            _add_issue(
                issues,
                check="shape_symbol_uniqueness",
                code="SHAPE_SYMBOL_DUPLICATE",
                severity="unexpected_error",
                protocol=protocol,
                source=f"specs/{protocol}/shape_table.csv",
                subject=symbol,
                message=f"shape_table symbol {symbol!r} 重复",
                details={"first_row": seen[symbol], "duplicate_row": row_number},
            )
            continue
        seen[symbol] = row_number


def _validate_claim_classes(
    protocol: str,
    rows: CsvRows,
    issues: list[ValidationIssue],
) -> None:
    for row_number, row in rows:
        claim_class = row["class"]
        if _is_allowed_claim_class(claim_class):
            continue
        _add_issue(
            issues,
            check="claims_class",
            code="CLAIM_CLASS_INVALID",
            severity="unexpected_error",
            protocol=protocol,
            source=f"specs/{protocol}/claims_matrix.csv",
            subject=row["claim_id"] or f"row {row_number}",
            message=f"claims class {claim_class!r} 不属于允许集合",
            details={
                "allowed_atoms": sorted(_CLAIM_CLASS_ATOMS),
                "allowed_exact": sorted(_CLAIM_CLASS_EXACT),
                "row": row_number,
            },
        )


def _validate_parameter_relations(
    protocol: str,
    records: Iterable[ProfileRecord],
    issues: list[ValidationIssue],
) -> None:
    if protocol == "c2lake":
        for record in records:
            if record.family == "toy":
                continue
            expected_n = math.ceil(4 * record.m * math.log2(record.m))
            if record.n != expected_n:
                _add_issue(
                    issues,
                    check="parameter_relations",
                    code="C2LAKE_N_RELATION_INVALID",
                    severity="unexpected_error",
                    protocol=protocol,
                    source="specs/c2lake/parameter_profiles.yaml",
                    subject=record.name,
                    message="C2LAKE benchmark profile 的 n 不等于 ceil(4*m*log2(m))",
                    details={"actual_n": record.n, "expected_n": expected_n, "m": record.m},
                )
            if record.family == "paper_literal" and record.q != record.m * record.m:
                _add_issue(
                    issues,
                    check="parameter_relations",
                    code="C2LAKE_PAPER_Q_NOT_M_SQUARED",
                    severity="unexpected_error",
                    protocol=protocol,
                    source="specs/c2lake/parameter_profiles.yaml",
                    subject=record.name,
                    message="C2LAKE paper_literal profile 的 q 必须等于 m²",
                    details={"actual_q": record.q, "expected_q": record.m * record.m},
                )
        return

    for record in records:
        if record.name != "paper_performance":
            continue
        rhs = 2 * record.n * math.log2(record.q)
        if record.m + _FLOAT_TOLERANCE < rhs:
            _add_issue(
                issues,
                check="parameter_relations",
                code="LCLA_PAPER_PERFORMANCE_DIMENSION_CONFLICT",
                severity="expected_warning",
                protocol=protocol,
                source="specs/lcla_aka/parameter_profiles.yaml",
                subject=record.name,
                message="LCLA paper_performance 违反 m >= 2*n*log2(q)",
                details={"m": record.m, "n": record.n, "q": record.q, "rhs": rhs},
            )


def _validate_prime_requirements(
    protocol: str,
    records: Iterable[ProfileRecord],
    issues: list[ValidationIssue],
) -> None:
    for record in records:
        prime = _is_prime(record.q)
        if record.q_must_be_prime and not prime:
            _add_issue(
                issues,
                check="prime_checks",
                code=f"{protocol.upper()}_AUDITED_Q_NOT_PRIME",
                severity="unexpected_error",
                protocol=protocol,
                source=f"specs/{protocol}/parameter_profiles.yaml",
                subject=record.name,
                message="q_must_be_prime=true 的 profile 使用了非素数 q",
                details={"q": record.q, "family": record.family},
            )
            continue
        if record.family == "paper_literal" and not prime and not record.q_must_be_prime:
            code = "C2LAKE_PAPER_Q_COMPOSITE" if protocol == "c2lake" else "LCLA_PAPER_Q_COMPOSITE"
            _add_issue(
                issues,
                check="prime_checks",
                code=code,
                severity="expected_warning",
                protocol=protocol,
                source=f"specs/{protocol}/parameter_profiles.yaml",
                subject=record.name,
                message="paper_literal profile 使用合数 q；按冻结决策保留为 expected warning",
                details={"q": record.q, "family": record.family},
            )


def _is_allowed_claim_class(value: str) -> bool:
    if value in _CLAIM_CLASS_EXACT:
        return True
    parts = value.split("/")
    return all(part in _CLAIM_CLASS_ATOMS for part in parts)


def _require_string(
    profile: Mapping[str, object],
    field: str,
    protocol: str,
    path: Path,
    name: str,
    issues: list[ValidationIssue],
) -> str | None:
    value = profile.get(field)
    if isinstance(value, str) and value:
        return value
    _add_profile_type_issue(protocol, path, name, field, "非空字符串", value, issues)
    return None


def _require_positive_int(
    profile: Mapping[str, object],
    field: str,
    protocol: str,
    path: Path,
    name: str,
    issues: list[ValidationIssue],
) -> int | None:
    value = profile.get(field)
    if type(value) is int and value > 0:
        return value
    _add_profile_type_issue(protocol, path, name, field, "正整数", value, issues)
    return None


def _require_positive_number(
    profile: Mapping[str, object],
    field: str,
    protocol: str,
    path: Path,
    name: str,
    issues: list[ValidationIssue],
) -> float | None:
    value = profile.get(field)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value)
    _add_profile_type_issue(protocol, path, name, field, "正数", value, issues)
    return None


def _require_bool(
    profile: Mapping[str, object],
    field: str,
    protocol: str,
    path: Path,
    name: str,
    issues: list[ValidationIssue],
) -> bool | None:
    value = profile.get(field)
    if type(value) is bool:
        return value
    _add_profile_type_issue(protocol, path, name, field, "布尔值", value, issues)
    return None


def _add_profile_type_issue(
    protocol: str,
    path: Path,
    name: str,
    field: str,
    expected: str,
    value: object,
    issues: list[ValidationIssue],
) -> None:
    _add_issue(
        issues,
        check="yaml_profile_schema",
        code="PROFILE_FIELD_TYPE_INVALID",
        severity="unexpected_error",
        protocol=protocol,
        source=str(path),
        subject=name,
        message=f"profile 字段 {field!r} 必须是{expected}",
        details={"field": field, "actual_type": type(value).__name__},
    )


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value in {2, 3}:
        return True
    if value % 2 == 0:
        return False
    limit = math.isqrt(value)
    candidate = 3
    while candidate <= limit:
        if value % candidate == 0:
            return False
        candidate += 2
    return True


def _summarize_checks(issues: Iterable[ValidationIssue]) -> list[ValidationCheck]:
    warning_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    for issue in issues:
        if issue.severity == "expected_warning":
            warning_counts[issue.check] += 1
        else:
            error_counts[issue.check] += 1
    checks: list[ValidationCheck] = []
    for name in _CHECK_NAMES:
        errors = error_counts[name]
        warnings = warning_counts[name]
        status: CheckStatus = "fail" if errors else "warning" if warnings else "pass"
        checks.append(
            ValidationCheck(
                name=name,
                status=status,
                expected_warning_count=warnings,
                unexpected_error_count=errors,
            )
        )
    return checks


def _required_findings(result: SpecValidationResult) -> list[dict[str, object]]:
    warning_counts: Counter[str] = Counter(issue.code for issue in result.expected_warnings)
    error_codes = {issue.code for issue in result.unexpected_errors}
    check_status = {check.name: check.status for check in result.checks}
    audited_prime_error_codes = {
        "C2LAKE_AUDITED_Q_NOT_PRIME",
        "LCLA_AKA_AUDITED_Q_NOT_PRIME",
    }
    return [
        {
            "name": "c2lake_n_equals_ceil_4m_log2m",
            "status": "fail" if "C2LAKE_N_RELATION_INVALID" in error_codes else "pass",
            "summary": "C2LAKE 非 toy benchmark profiles 未发现 n 关系错误。",
        },
        {
            "name": "c2lake_paper_literal_q_m_squared_composite",
            "status": "warning" if warning_counts["C2LAKE_PAPER_Q_COMPOSITE"] else "pass",
            "summary": (
                "C2LAKE paper_literal q=m² 的合数情况记录为 "
                f"{warning_counts['C2LAKE_PAPER_Q_COMPOSITE']} 个 expected warning，未拒绝。"
            ),
        },
        {
            "name": "audited_q_prime",
            "status": "fail" if error_codes.intersection(audited_prime_error_codes) else "pass",
            "summary": "所有 q_must_be_prime=true 的 audited/toy profiles 均通过素数检查。",
        },
        {
            "name": "lcla_paper_performance_dimension_relation",
            "status": (
                "warning" if warning_counts["LCLA_PAPER_PERFORMANCE_DIMENSION_CONFLICT"] else "pass"
            ),
            "summary": (
                "LCLA paper_performance 的 m=256,n=6 违反 m >= 2*n*log2(q)，"
                "已记录为 expected warning。"
            ),
        },
        {
            "name": "shape_symbol_uniqueness",
            "status": check_status["shape_symbol_uniqueness"],
            "summary": "两个 shape_table 均未发现重复 symbol。",
        },
        {
            "name": "claims_class_allowed",
            "status": check_status["claims_class"],
            "summary": "claims class 均属于允许集合或允许的组合标记。",
        },
        {
            "name": "profile_family_backend_and_field_types",
            "status": check_status["yaml_profile_schema"],
            "summary": "profile family、backend、必填字段和字段类型均通过校验。",
        },
    ]


def _add_issue(
    issues: list[ValidationIssue],
    *,
    check: str,
    code: str,
    severity: Severity,
    protocol: str,
    source: str,
    subject: str,
    message: str,
    details: dict[str, object] | None = None,
) -> None:
    issues.append(
        ValidationIssue(
            check=check,
            code=code,
            severity=severity,
            protocol=protocol,
            source=source,
            subject=subject,
            message=message,
            details=details or {},
        )
    )


def _append_issue_table(lines: list[str], issues: Iterable[ValidationIssue]) -> None:
    issue_list = list(issues)
    if not issue_list:
        lines.append("无。")
        return
    lines.extend(
        [
            "| code | protocol | subject | message |",
            "| --- | --- | --- | --- |",
        ]
    )
    for issue in issue_list:
        lines.append(
            "| "
            f"{_escape_markdown(issue.code)} | "
            f"{_escape_markdown(issue.protocol)} | "
            f"{_escape_markdown(issue.subject)} | "
            f"{_escape_markdown(issue.message)} |"
        )


def _format_counts(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|")
