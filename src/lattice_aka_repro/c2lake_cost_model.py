"""C2LAKE 理论通信、存储和运算成本模型。

模型从冻结 profile 和协议字段定义推导 C2LAKE 自身成本；其他方案的论文数值只能作为
只读 reference，不在本模块中声称独立复现。
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import yaml

from lattice_aka_repro.c2lake_core import C2LakeProfile, load_c2lake_profile


@dataclass(frozen=True, slots=True)
class CommunicationCost:
    profile: str
    family: str
    m: int
    q: int
    n: int
    bits_per_zq: int
    one_message_paper_compact_bits: int
    one_message_paper_compact_bytes: int
    full_exchange_paper_compact_bits: int
    full_exchange_paper_compact_bytes: int
    one_message_canonical_hash_encoding_bits: int
    one_message_canonical_hash_encoding_bytes: int
    full_exchange_canonical_hash_encoding_bits: int
    full_exchange_canonical_hash_encoding_bytes: int
    identity_bytes: int
    timestamp_bytes: int
    network_wire_encoding_defined: bool


@dataclass(frozen=True, slots=True)
class StorageCost:
    profile: str
    family: str
    m: int
    q: int
    n: int
    bits_per_zq: int
    item: str
    element_count: int
    math_ideal_bits: int
    math_ideal_bytes: int
    numpy_int64_bytes: int
    optimized_storage_bytes: int


@dataclass(frozen=True, slots=True)
class OperationCount:
    profile: str
    family: str
    m: int
    q: int
    n: int
    phase: str
    vector_times_matrix: int = 0
    matrix_times_vector: int = 0
    vector_dot: int = 0
    vector_add: int = 0
    scalar_times_vector: int = 0
    h1: int = 0
    h2: int = 0
    h3: int = 0


def load_profile_names(*, specs_dir: Path) -> list[str]:
    source = specs_dir / "c2lake" / "parameter_profiles.yaml"
    raw: object = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), dict):
        raise ValueError("C2LAKE profile YAML 结构错误")
    profiles = cast(dict[str, object], raw["profiles"])
    return sorted(profiles)


def build_cost_tables(*, specs_dir: Path) -> dict[str, object]:
    profiles = [
        load_c2lake_profile(name, specs_dir=specs_dir)
        for name in load_profile_names(specs_dir=specs_dir)
    ]
    communications = [communication_cost(profile) for profile in profiles]
    storage = [row for profile in profiles for row in storage_costs(profile)]
    operations = [row for profile in profiles for row in operation_counts(profile)]
    return {
        "schema_version": 1,
        "result": "pass",
        "source": "derived_from_c2lake_field_definitions",
        "notes": [
            "C2LAKE 成本由字段定义和冻结 profile 推导。",
            "paper_compact_message_bytes 按 Zq 元素最小位长估算，沿用论文忽略 ID/T 的紧凑口径。",
            (
                "canonical_hash_encoding_bytes 是当前 SHAKE 输入的长度前缀编码长度，"
                "不是网络 wire serializer。"
            ),
            "当前项目未实现专用网络 wire serializer，network_wire_encoding_defined=false。",
            "其他论文方案只可作为 paper_reported_reference，不在此 JSON 中独立复现。",
            "log 符号统一按 log2(q) 的比特长度实现，不混用 log m、log2 m、log²m、log³m。",
        ],
        "communication": [asdict(row) for row in communications],
        "storage": [asdict(row) for row in storage],
        "operations": [asdict(row) for row in operations],
        "paper_reported_reference": [],
    }


def communication_cost(
    profile: C2LakeProfile, *, identity_bytes: int = 18, timestamp_bytes: int = 8
) -> CommunicationCost:
    bits_per_zq = _bits_per_zq(profile.q)
    vector_count_per_message = 6
    one_message_paper_compact_bits = vector_count_per_message * profile.n * bits_per_zq
    one_message_paper_compact_bytes = _ceil_bytes(one_message_paper_compact_bits)

    vector_fields = ("P_i0", "P_i1", "X_i", "Y_i", "Z_i", "S_i")
    canonical_hash_encoding_bytes = _encoded_bytes_field_size("domain", len(b"C2LAKE-MESSAGE-v1"))
    canonical_hash_encoding_bytes += _encoded_bytes_field_size("identity", identity_bytes)
    canonical_hash_encoding_bytes += _encoded_uint_field_size("timestamp", timestamp_bytes)
    canonical_hash_encoding_bytes += sum(
        _encoded_vector_field_size(name, profile.n) for name in vector_fields
    )
    one_message_canonical_hash_encoding_bits = canonical_hash_encoding_bytes * 8

    return CommunicationCost(
        profile=profile.name,
        family=profile.family,
        m=profile.m,
        q=profile.q,
        n=profile.n,
        bits_per_zq=bits_per_zq,
        one_message_paper_compact_bits=one_message_paper_compact_bits,
        one_message_paper_compact_bytes=one_message_paper_compact_bytes,
        full_exchange_paper_compact_bits=one_message_paper_compact_bits * 2,
        full_exchange_paper_compact_bytes=one_message_paper_compact_bytes * 2,
        one_message_canonical_hash_encoding_bits=one_message_canonical_hash_encoding_bits,
        one_message_canonical_hash_encoding_bytes=canonical_hash_encoding_bytes,
        full_exchange_canonical_hash_encoding_bits=(one_message_canonical_hash_encoding_bits * 2),
        full_exchange_canonical_hash_encoding_bytes=canonical_hash_encoding_bytes * 2,
        identity_bytes=identity_bytes,
        timestamp_bytes=timestamp_bytes,
        network_wire_encoding_defined=False,
    )


def storage_costs(profile: C2LakeProfile) -> list[StorageCost]:
    n = profile.n
    items = {
        "M": n * n,
        "master_secret_d": n,
        "master_public_P": n,
        "user_private_key_d_i0_d_i1": 2 * n,
        "user_public_key_P_i0_P_i1": 2 * n,
        "ephemeral_state_x_y_z": 3 * n,
        "one_party_transcript_vectors": 6 * n,
    }
    return [_storage_cost(profile, item, elements) for item, elements in items.items()]


def operation_counts(profile: C2LakeProfile) -> list[OperationCount]:
    rows = [
        _make_operation_count(profile, "Setup", vector_times_matrix=1),
        _make_operation_count(profile, "SetSecretValue", vector_times_matrix=1),
        _make_operation_count(
            profile,
            phase="PartialPrivateKeyExtract",
            vector_times_matrix=1,
            vector_add=1,
            scalar_times_vector=1,
            h1=1,
        ),
        _make_operation_count(
            profile,
            phase="initiator_create",
            vector_times_matrix=1,
            matrix_times_vector=2,
            vector_add=2,
            scalar_times_vector=1,
            h2=1,
        ),
        _make_operation_count(
            profile,
            phase="responder_verify_and_reply",
            vector_times_matrix=2,
            matrix_times_vector=2,
            vector_dot=4,
            vector_add=7,
            scalar_times_vector=3,
            h1=1,
            h2=2,
            h3=1,
        ),
        _make_operation_count(
            profile,
            phase="initiator_verify_and_finish",
            vector_times_matrix=1,
            vector_dot=4,
            vector_add=4,
            scalar_times_vector=2,
            h1=1,
            h2=1,
            h3=1,
        ),
    ]
    rows.append(_sum_operations(profile, rows, "full_handshake"))
    return rows


def write_cost_json(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def write_cost_csv(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = _flatten_payload(payload)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "section",
                "profile",
                "family",
                "m",
                "q",
                "n",
                "metric",
                "value",
                "unit",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output


def render_cost_report(payload: dict[str, object]) -> str:
    communication = cast(list[dict[str, object]], payload["communication"])
    storage = cast(list[dict[str, object]], payload["storage"])
    operations = cast(list[dict[str, object]], payload["operations"])
    lines = [
        "# C2LAKE Theoretical Cost Reproduction",
        "",
        "## Scope",
        "",
        "- 仅重算 C2LAKE 自身的通信、存储和运算计数。",
        "- `paper_compact_message_bytes` 按 Zq 元素最小位长估算，沿用论文忽略 ID/T 的紧凑口径。",
        "- `canonical_hash_encoding_bytes` 是当前 SHAKE 输入的长度前缀编码长度。",
        "- 当前项目未实现专用网络 wire serializer：`network_wire_encoding_defined=false`。",
        (
            "- canonical hash encoding 不应解释为实际网络通信开销，"
            "也不能直接用于否定或验证论文通信效率主张。"
        ),
        "- 其他方案数据不在本报告中声称独立复现。",
        "- 所有比特长度使用 `ceil(log2(q))` 或等价 `bit_length(q-1)`。",
        "",
        "## Communication Cost",
        "",
        (
            "| profile | family | m | q | n | paper compact bytes | "
            "canonical hash encoding bytes | wire defined |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in communication:
        lines.append(
            "| {profile} | {family} | {m} | {q} | {n} | {paper} | {canonical} | {wire} |".format(
                profile=row["profile"],
                family=row["family"],
                m=row["m"],
                q=row["q"],
                n=row["n"],
                paper=row["full_exchange_paper_compact_bytes"],
                canonical=row["full_exchange_canonical_hash_encoding_bytes"],
                wire=row["network_wire_encoding_defined"],
            )
        )
    lines.extend(
        [
            "",
            "## Storage Cost",
            "",
            "| profile | item | math ideal bytes | NumPy int64 bytes | optimized estimate bytes |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in storage:
        if row["profile"] == "toy" or row["item"] in {
            "M",
            "user_private_key_d_i0_d_i1",
            "one_party_transcript_vectors",
        }:
            lines.append(
                "| {profile} | {item} | {math} | {numpy} | {optimized} |".format(
                    profile=row["profile"],
                    item=row["item"],
                    math=row["math_ideal_bytes"],
                    numpy=row["numpy_int64_bytes"],
                    optimized=row["optimized_storage_bytes"],
                )
            )
    lines.extend(
        [
            "",
            "## Operation Counts",
            "",
            "| profile | phase | v×M | M×v | dot | add | scalar×v | H1 | H2 | H3 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in operations:
        if row["profile"] in {"toy", "paper_literal_m32", "audited_prime_m32"}:
            lines.append(
                (
                    "| {profile} | {phase} | {vtm} | {mtv} | {dot} | {add} | "
                    "{scalar} | {h1} | {h2} | {h3} |"
                ).format(
                    profile=row["profile"],
                    phase=row["phase"],
                    vtm=row["vector_times_matrix"],
                    mtv=row["matrix_times_vector"],
                    dot=row["vector_dot"],
                    add=row["vector_add"],
                    scalar=row["scalar_times_vector"],
                    h1=row["h1"],
                    h2=row["h2"],
                    h3=row["h3"],
                )
            )
    lines.append("")
    return "\n".join(lines)


def write_cost_report(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_cost_report(payload), encoding="utf-8")
    return output


def _bits_per_zq(q: int) -> int:
    return max(1, (q - 1).bit_length())


def _ceil_bytes(bits: int) -> int:
    return (bits + 7) // 8


def _storage_cost(profile: C2LakeProfile, item: str, elements: int) -> StorageCost:
    bits_per_zq = _bits_per_zq(profile.q)
    math_bits = elements * bits_per_zq
    return StorageCost(
        profile=profile.name,
        family=profile.family,
        m=profile.m,
        q=profile.q,
        n=profile.n,
        bits_per_zq=bits_per_zq,
        item=item,
        element_count=elements,
        math_ideal_bits=math_bits,
        math_ideal_bytes=_ceil_bytes(math_bits),
        numpy_int64_bytes=elements * 8,
        optimized_storage_bytes=elements * _optimized_dtype_bytes(profile.q),
    )


def _optimized_dtype_bytes(q: int) -> int:
    bits = _bits_per_zq(q)
    if bits <= 8:
        return 1
    if bits <= 16:
        return 2
    if bits <= 32:
        return 4
    return 8


def _encoded_bytes_field_size(type_tag: str, payload_bytes: int) -> int:
    return len(type_tag.encode("ascii")) + 8 + payload_bytes


def _encoded_uint_field_size(type_tag: str, payload_bytes: int) -> int:
    return _encoded_bytes_field_size(type_tag, payload_bytes)


def _encoded_vector_field_size(type_tag: str, n: int) -> int:
    payload_bytes = 24 + 8 * n
    return _encoded_bytes_field_size(f"vector:{type_tag}", payload_bytes)


def _make_operation_count(
    profile: C2LakeProfile,
    phase: str,
    *,
    vector_times_matrix: int = 0,
    matrix_times_vector: int = 0,
    vector_dot: int = 0,
    vector_add: int = 0,
    scalar_times_vector: int = 0,
    h1: int = 0,
    h2: int = 0,
    h3: int = 0,
) -> OperationCount:
    return OperationCount(
        profile=profile.name,
        family=profile.family,
        m=profile.m,
        q=profile.q,
        n=profile.n,
        phase=phase,
        vector_times_matrix=vector_times_matrix,
        matrix_times_vector=matrix_times_vector,
        vector_dot=vector_dot,
        vector_add=vector_add,
        scalar_times_vector=scalar_times_vector,
        h1=h1,
        h2=h2,
        h3=h3,
    )


def _sum_operations(
    profile: C2LakeProfile,
    rows: list[OperationCount],
    phase: str,
) -> OperationCount:
    return OperationCount(
        profile=profile.name,
        family=profile.family,
        m=profile.m,
        q=profile.q,
        n=profile.n,
        phase=phase,
        vector_times_matrix=sum(row.vector_times_matrix for row in rows),
        matrix_times_vector=sum(row.matrix_times_vector for row in rows),
        vector_dot=sum(row.vector_dot for row in rows),
        vector_add=sum(row.vector_add for row in rows),
        scalar_times_vector=sum(row.scalar_times_vector for row in rows),
        h1=sum(row.h1 for row in rows),
        h2=sum(row.h2 for row in rows),
        h3=sum(row.h3 for row in rows),
    )


def _flatten_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    communication = cast(list[dict[str, object]], payload["communication"])
    storage = cast(list[dict[str, object]], payload["storage"])
    operations = cast(list[dict[str, object]], payload["operations"])
    for row in communication:
        for metric in (
            "full_exchange_paper_compact_bits",
            "full_exchange_paper_compact_bytes",
            "full_exchange_canonical_hash_encoding_bits",
            "full_exchange_canonical_hash_encoding_bytes",
            "network_wire_encoding_defined",
        ):
            rows.append(
                _csv_row("communication", row, metric, row[metric], _unit_for_metric(metric))
            )
    for row in storage:
        for metric in ("math_ideal_bytes", "numpy_int64_bytes", "optimized_storage_bytes"):
            rows.append(
                _csv_row(
                    "storage",
                    row,
                    f"{row['item']}:{metric}",
                    row[metric],
                    "bytes",
                )
            )
    for row in operations:
        for metric in (
            "vector_times_matrix",
            "matrix_times_vector",
            "vector_dot",
            "vector_add",
            "scalar_times_vector",
            "h1",
            "h2",
            "h3",
        ):
            rows.append(
                _csv_row(
                    "operations",
                    row,
                    f"{row['phase']}:{metric}",
                    row[metric],
                    "count",
                )
            )
    return rows


def _csv_row(
    section: str,
    source: dict[str, object],
    metric: str,
    value: object,
    unit: str,
) -> dict[str, object]:
    return {
        "section": section,
        "profile": source["profile"],
        "family": source["family"],
        "m": source["m"],
        "q": source["q"],
        "n": source["n"],
        "metric": metric,
        "value": value,
        "unit": unit,
        "notes": "",
    }


def _unit_for_metric(metric: str) -> str:
    if metric == "network_wire_encoding_defined":
        return "boolean"
    return "bits" if metric.endswith("_bits") else "bytes"
