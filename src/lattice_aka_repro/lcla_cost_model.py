"""LCLA-AKA 理论通信、存储与运算成本模型。"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from lattice_aka_repro.lcla_backends import load_lcla_profile
from lattice_aka_repro.lcla_hashes import encode_bit_array, encode_zq_array
from lattice_aka_repro.lcla_types import LCLAProfile


@dataclass(frozen=True, slots=True)
class LCLACommunicationCost:
    profile: str
    family: str
    m: int
    n: int
    q: int
    bits_per_zq: int
    network_rounds: int
    network_packets: int
    transmitted_fields: int
    paper_identity_bits: int
    actual_identity_bytes: int
    paper_compact_message_bits: int
    paper_compact_message_bytes: int
    actual_identity_compact_message_bits: int
    actual_identity_compact_message_bytes: int
    canonical_hash_encoding_bytes: int
    network_wire_encoding_defined: bool


@dataclass(frozen=True, slots=True)
class LCLAStorageCost:
    profile: str
    family: str
    item: str
    element_kind: str
    element_count: int
    mathematical_ideal_bits: int | None
    mathematical_ideal_bytes: int | None
    numpy_reference_bytes: int | None
    availability: str
    note: str


@dataclass(frozen=True, slots=True)
class LCLAOperationCount:
    profile: str
    family: str
    phase: str
    matrix_multiply: int = 0
    matrix_vector: int = 0
    vector_add_sub: int = 0
    scalar_multiply: int = 0
    gaussian_samples: int = 0
    signal_s: int = 0
    mod2: int = 0
    h1: int = 0
    mac_a: int = 0
    mac_b: int = 0
    id_mask: int = 0
    session_kdf: int = 0
    xor: int = 0


def profile_names(repo_root: Path) -> list[str]:
    """返回冻结 LCLA profile 顺序。"""

    return [
        "toy",
        "paper_correctness",
        "paper_performance",
        "audited_preserve_keylen",
        "audited_preserve_dimension",
    ]


def communication_cost(
    profile: LCLAProfile,
    *,
    identity: str | bytes = "alice@example.test",
) -> LCLACommunicationCost:
    """由三轮七字段推导紧凑通信与 canonical transcript 编码长度。"""

    identity_bytes = identity.encode("utf-8") if isinstance(identity, str) else bytes(identity)
    if not identity_bytes:
        raise ValueError("identity 不能为空")
    bits_per_zq = profile.q.bit_length()
    matrix_bits = profile.m * profile.m * bits_per_zq
    fixed_bit_vectors = 4 * profile.m  # delta_A, h_A, h_B, delta_B
    paper_identity_bits = profile.m
    paper_bits = 2 * matrix_bits + fixed_bit_vectors + paper_identity_bits
    actual_bits = 2 * matrix_bits + fixed_bit_vectors + len(identity_bytes) * 8
    canonical_bytes = canonical_transcript_encoding_bytes(
        profile,
        identity_length=len(identity_bytes),
    )
    return LCLACommunicationCost(
        profile=profile.name,
        family=profile.family,
        m=profile.m,
        n=profile.n,
        q=profile.q,
        bits_per_zq=bits_per_zq,
        network_rounds=3,
        network_packets=3,
        transmitted_fields=7,
        paper_identity_bits=paper_identity_bits,
        actual_identity_bytes=len(identity_bytes),
        paper_compact_message_bits=paper_bits,
        paper_compact_message_bytes=_ceil_bytes(paper_bits),
        actual_identity_compact_message_bits=actual_bits,
        actual_identity_compact_message_bytes=_ceil_bytes(actual_bits),
        canonical_hash_encoding_bytes=canonical_bytes,
        network_wire_encoding_defined=False,
    )


def canonical_transcript_encoding_bytes(
    profile: LCLAProfile,
    *,
    identity_length: int,
) -> int:
    """计算当前 transcript SHAKE 输入的 canonical payload 长度。

    该值仅描述哈希输入编码，绝不表示网络 wire 大小。
    """

    if identity_length <= 0:
        raise ValueError("identity_length 必须为正")
    matrix = np.zeros((profile.m, profile.m), dtype=np.int64)
    bits = np.zeros(profile.m, dtype=np.int64)
    encoded = b"".join(
        (
            encode_zq_array(
                matrix,
                q=profile.q,
                profile_version=profile.name,
                tag="C_A",
            ),
            encode_bit_array(bits, profile_version=profile.name, tag="delta_A"),
            encode_bit_array(bits, profile_version=profile.name, tag="h_A"),
            encode_zq_array(
                matrix,
                q=profile.q,
                profile_version=profile.name,
                tag="C_B",
            ),
            encode_bit_array(bits, profile_version=profile.name, tag="h_B"),
            _typed_field_size(tag="T_A", payload_size=identity_length),
            encode_bit_array(bits, profile_version=profile.name, tag="delta_B"),
        )
    )
    return len(encoded)


def storage_costs(profile: LCLAProfile) -> list[LCLAStorageCost]:
    """推导数学理想存储与 NumPy reference 存储。"""

    zq_bits = profile.q.bit_length()
    m = profile.m
    n = profile.n
    items = [
        ("A", "zq", n * m, "available", "公共矩阵 n×m"),
        (
            "trapdoor",
            "opaque",
            0,
            "unavailable",
            "官方 FrodoKEM 不提供论文要求的 TrapGen/SamplePre，无法量化真实 trapdoor。",
        ),
        ("static_private_s1_s2_s", "zq", 3 * m, "constructed_only", "含公开 s2 与组合 s"),
        ("static_error_f", "zq", n, "constructed_only", "constructed relation 的 f"),
        ("static_public_pk_u1_u2", "zq", 3 * n, "constructed_only", "三个 n 维向量"),
        ("alice_ephemeral_X_E_e", "zq", n * m + m * m + m, "available", "X_A、E_A、e_A"),
        ("bob_ephemeral_X_E", "zq", n * m + m * m, "available", "X_B、E_B"),
        ("transcript_matrices", "zq", 2 * m * m, "available", "C_A、C_B"),
        ("transcript_bits", "bit", 4 * m, "available", "delta_A、h_A、h_B、delta_B"),
        ("session_shared_bits", "bit", 2 * m, "available", "m1、m2"),
    ]
    rows: list[LCLAStorageCost] = []
    for item, kind, count, availability, note in items:
        if kind == "opaque":
            ideal_bits = ideal_bytes = numpy_bytes = None
        else:
            ideal_bits = count * (zq_bits if kind == "zq" else 1)
            ideal_bytes = _ceil_bytes(ideal_bits)
            numpy_bytes = count * 8
        rows.append(
            LCLAStorageCost(
                profile=profile.name,
                family=profile.family,
                item=item,
                element_kind=kind,
                element_count=count,
                mathematical_ideal_bits=ideal_bits,
                mathematical_ideal_bytes=ideal_bytes,
                numpy_reference_bytes=numpy_bytes,
                availability=availability,
                note=note,
            )
        )
    return rows


def operation_counts(profile: LCLAProfile) -> list[LCLAOperationCount]:
    """按静态密钥与三轮协议阶段统计高层原语调用。"""

    rows = [
        _operation(profile, "setup"),
        _operation(
            profile,
            "entity_key_generation",
            matrix_vector=2,
            vector_add_sub=2,
            scalar_multiply=2,
            gaussian_samples=3,
        ),
        _operation(profile, "kgc_key_generation", matrix_vector=1, vector_add_sub=1, h1=1),
        _operation(
            profile,
            "entity_verify_and_assemble",
            matrix_vector=2,
            vector_add_sub=3,
            scalar_multiply=1,
            h1=1,
        ),
        _operation(
            profile,
            "alice_create",
            matrix_multiply=1,
            matrix_vector=1,
            vector_add_sub=2,
            scalar_multiply=2,
            gaussian_samples=3,
            signal_s=1,
            mod2=1,
            h1=1,
            mac_a=1,
        ),
        _operation(
            profile,
            "bob_verify_and_reply",
            matrix_multiply=1,
            matrix_vector=1,
            vector_add_sub=1,
            scalar_multiply=1,
            gaussian_samples=2,
            mod2=1,
            mac_a=1,
            mac_b=1,
        ),
        _operation(
            profile,
            "alice_verify_and_finish",
            matrix_vector=1,
            vector_add_sub=1,
            scalar_multiply=1,
            gaussian_samples=1,
            signal_s=1,
            mod2=1,
            mac_b=1,
            id_mask=1,
            session_kdf=1,
            xor=1,
        ),
        _operation(
            profile,
            "bob_finish",
            matrix_vector=1,
            mod2=1,
            h1=1,
            id_mask=1,
            session_kdf=1,
            xor=1,
        ),
    ]
    protocol_rows = [row for row in rows if row.phase in _PROTOCOL_PHASES]
    rows.append(_sum_operations(profile, protocol_rows, "full_handshake"))
    return rows


def build_cost_tables(repo_root: Path) -> dict[str, object]:
    """构建所有 profile 的机器成本表。"""

    profiles = [load_lcla_profile(repo_root, name) for name in profile_names(repo_root)]
    communication = [communication_cost(profile) for profile in profiles]
    storage = [row for profile in profiles for row in storage_costs(profile)]
    operations = [row for profile in profiles for row in operation_counts(profile)]
    return {
        "schema_version": 1,
        "result": "cost_model_complete_with_unavailable_real_trapdoor_storage",
        "source": "derived_from_lcla_protocol_field_definitions",
        "network_rounds": 3,
        "network_packets": 3,
        "transmitted_fields": 7,
        "transmitted_field_names": [
            "C_A",
            "delta_A",
            "h_A",
            "C_B",
            "h_B",
            "T_A",
            "delta_B",
        ],
        "network_wire_encoding_defined": False,
        "communication": [asdict(row) for row in communication],
        "storage": [asdict(row) for row in storage],
        "operations": [asdict(row) for row in operations],
        "notes": [
            "paper_compact_message_bits 使用 q 元素最小位长，并按论文 m-bit identity 假设。",
            "canonical_hash_encoding_bytes 是当前 SHAKE transcript 输入编码，不是网络通信量。",
            "项目未实现专用 wire serializer，不能用 canonical 编码验证论文通信效率主张。",
            "七个 transmitted fields 属于三个网络 packet，不是七轮或七个独立 packet。",
            "真实 trapdoor 后端不可用，因此 trapdoor 存储不能伪造估值。",
        ],
    }


def write_cost_outputs(
    payload: dict[str, object],
    *,
    json_output: Path,
    csv_output: Path,
    report_output: Path,
) -> None:
    """写入 JSON、长表 CSV 与报告。"""

    json_output.parent.mkdir(parents=True, exist_ok=True)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = _flatten_cost_rows(payload)
    fieldnames = sorted({key for row in rows for key in row})
    with csv_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report_output.write_text(render_cost_report(payload), encoding="utf-8")


def render_cost_report(payload: dict[str, object]) -> str:
    """渲染理论成本报告。"""

    communication = payload["communication"]
    assert isinstance(communication, list)
    lines = [
        "# LCLA-AKA 通信与理论成本复现",
        "",
        "## 口径结论",
        "",
        "- 协议是 3 个网络轮次、3 个 packet、7 个论文统计字段；7 不是网络 packet 数。",
        "- `paper_compact_message_bits` 按每个 Zq 元素的最小位长和论文 m-bit identity 假设推导。",
        "- `canonical_hash_encoding_bytes` 仅是当前 SHAKE transcript 的类型化长度前缀编码。",
        "- `network_wire_encoding_defined=false`；项目没有专用网络 wire serializer。",
        "- 因此 canonical hash encoding 不能直接用于验证或否定论文通信效率主张。",
        "",
        "## 通信结果",
        "",
        "| profile | m | n | q | 紧凑位数 | 实际 identity 紧凑位数 | canonical hash bytes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for raw in communication:
        assert isinstance(raw, dict)
        lines.append(
            f"| {raw['profile']} | {raw['m']} | {raw['n']} | {raw['q']} | "
            f"{raw['paper_compact_message_bits']} | "
            f"{raw['actual_identity_compact_message_bits']} | "
            f"{raw['canonical_hash_encoding_bytes']} |"
        )
    lines.extend(
        [
            "",
            "紧凑位数推导为 `2*m^2*ceil(log2(q)) + 4*m + identity_bits`：",
            "`C_A/C_B` 各含 `m^2` 个 Zq 元素；`delta_A/h_A/h_B/delta_B` 各 m bits；",
            "`T_A` 长度等于 Alice identity 的字节长度。",
            "",
            "## 存储边界",
            "",
            "JSON/CSV 同时报告数学理想位长与 NumPy int64 实际数组字节数。",
            "真实 TrapGen/SamplePre 不可用，trapdoor 的结构和存储量标为 unavailable，",
            "不使用普通短向量冒充。",
            "",
            "## 运算计数",
            "",
            "按 setup、静态密钥生成/验证、Alice create、Bob verify/reply、Alice finish、",
            "Bob finish 与 full handshake 分阶段统计矩阵乘、矩阵向量乘、加减、标量乘、",
            "离散高斯、S、Mod2、H1、各 H2 分域及 XOR。计数是高层原语次数，",
            "不等同于底层标量乘加数，也不是论文 Frodo 原生计时。",
            "",
        ]
    )
    return "\n".join(lines)


_PROTOCOL_PHASES = {
    "alice_create",
    "bob_verify_and_reply",
    "alice_verify_and_finish",
    "bob_finish",
}


def _operation(profile: LCLAProfile, phase: str, **counts: int) -> LCLAOperationCount:
    return LCLAOperationCount(
        profile=profile.name,
        family=profile.family,
        phase=phase,
        **counts,
    )


def _sum_operations(
    profile: LCLAProfile,
    rows: list[LCLAOperationCount],
    phase: str,
) -> LCLAOperationCount:
    fields = (
        "matrix_multiply",
        "matrix_vector",
        "vector_add_sub",
        "scalar_multiply",
        "gaussian_samples",
        "signal_s",
        "mod2",
        "h1",
        "mac_a",
        "mac_b",
        "id_mask",
        "session_kdf",
        "xor",
    )
    counts = {field: sum(getattr(row, field) for row in rows) for field in fields}
    return _operation(profile, phase, **counts)


def _typed_field_size(*, tag: str, payload_size: int) -> bytes:
    size = 8 + len(tag.encode("ascii")) + 8 + payload_size
    return bytes(size)


def _ceil_bytes(bits: int) -> int:
    return (bits + 7) // 8


def _flatten_cost_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for section in ("communication", "storage", "operations"):
        raw_rows = payload[section]
        assert isinstance(raw_rows, list)
        for raw in raw_rows:
            assert isinstance(raw, dict)
            rows.append({"section": section, **raw})
    return rows
