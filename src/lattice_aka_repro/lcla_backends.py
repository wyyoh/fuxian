"""LCLA-AKA 参数加载与静态密钥后端。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import numpy as np
import yaml

from lattice_aka_repro.lcla_gaussian import DiscreteGaussianSampler
from lattice_aka_repro.lcla_hashes import LCLAHashSuite, normalize_identity
from lattice_aka_repro.lcla_modular import (
    map_centered_to_zq,
    matrix_vector_mod,
    scalar_multiply_mod,
    vector_add_mod,
    vector_sub_mod,
)
from lattice_aka_repro.lcla_types import (
    BackendName,
    DistributionVariant,
    LCLABackendCapabilities,
    LCLAEntityContribution,
    LCLAError,
    LCLAKGCShare,
    LCLAParameters,
    LCLAProfile,
    LCLAStaticKeyPair,
    LCLAStaticPrivateKey,
    LCLAStaticPublicComponents,
    LCLATrapdoorHandle,
)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def load_lcla_profile(repo_root: Path, name: str) -> LCLAProfile:
    """从冻结 YAML 加载并再次执行运行时不变量检查。"""

    path = repo_root / "specs" / "lcla_aka" / "parameter_profiles.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("profiles"), dict):
        raise LCLAError("PROFILE_ERROR", "LCLA profile YAML 结构非法")
    profiles = cast(dict[object, object], document["profiles"])
    raw = profiles.get(name)
    if not isinstance(raw, dict):
        raise LCLAError("PROFILE_ERROR", f"未知 profile={name!r}")
    values = cast(Mapping[object, object], raw)
    try:
        family = values["family"]
        m = values["m"]
        n = values["n"]
        q = values["q"]
        beta = values["beta"]
        q_must_be_prime = values["q_must_be_prime"]
    except KeyError as exc:
        raise LCLAError("PROFILE_ERROR", f"profile 缺字段 {exc}") from exc
    if (
        not isinstance(family, str)
        or isinstance(m, bool)
        or not isinstance(m, int)
        or isinstance(n, bool)
        or not isinstance(n, int)
        or isinstance(q, bool)
        or not isinstance(q, int)
        or isinstance(beta, bool)
        or not isinstance(beta, (int, float))
        or not isinstance(q_must_be_prime, bool)
    ):
        raise LCLAError("PROFILE_ERROR", "profile 字段类型非法")
    profile = LCLAProfile(
        name=name,
        family=family,
        m=m,
        n=n,
        q=q,
        beta=float(beta),
        q_must_be_prime=q_must_be_prime,
    )
    if profile.family == "audited" and not profile.q_must_be_prime:
        raise LCLAError("PROFILE_ERROR", "audited profile 必须要求素数")
    if profile.q_must_be_prime and not _is_prime(profile.q):
        raise LCLAError("PROFILE_ERROR", "q_must_be_prime profile 的 q 不是素数")
    return profile


def backend_capabilities(keygen_backend: str) -> LCLABackendCapabilities:
    """返回后端的机器可检查能力声明。"""

    if keygen_backend == "constructed_relation":
        return LCLABackendCapabilities(
            name=keygen_backend,
            real_trapdoor=False,
            sample_pre=False,
            arbitrary_parameters=True,
            programmed_h1=True,
            status="available_with_evidence_downgrade",
        )
    if keygen_backend == "real_trapdoor":
        return LCLABackendCapabilities(
            name=keygen_backend,
            real_trapdoor=False,
            sample_pre=False,
            arbitrary_parameters=False,
            programmed_h1=False,
            status="unavailable",
        )
    if keygen_backend == "toy_trapdoor":
        return LCLABackendCapabilities(
            name=keygen_backend,
            real_trapdoor=False,
            sample_pre=False,
            arbitrary_parameters=False,
            programmed_h1=True,
            status="not_implemented",
        )
    raise LCLAError("BACKEND_ERROR", f"未知 keygen backend={keygen_backend!r}")


def setup_lcla(
    *,
    profile: LCLAProfile,
    backend: BackendName,
    keygen_backend: str,
    seed: int,
    distribution_variant: DistributionVariant = "legacy_reference",
) -> LCLAParameters:
    """生成公共 A；真实 TrapGen 不可用时不创建虚假 trapdoor。"""

    if backend not in {"safe", "fast"}:
        raise LCLAError("BACKEND_ERROR", f"不支持 backend={backend!r}")
    capabilities = backend_capabilities(keygen_backend)
    if keygen_backend != "constructed_relation":
        raise LCLAError(
            "BACKEND_UNAVAILABLE",
            f"{keygen_backend} status={capabilities.status}",
        )
    rng = np.random.Generator(np.random.PCG64(seed))
    matrix_a = np.asarray(
        rng.integers(0, profile.q, size=(profile.n, profile.m), dtype=np.int64),
        dtype=np.int64,
    )
    hash_suite = LCLAHashSuite(profile=profile, programmed=True)
    return LCLAParameters(
        profile=profile,
        backend=backend,
        keygen_backend=keygen_backend,
        distribution_variant=distribution_variant,
        matrix_a=matrix_a,
        hash_suite=hash_suite,
        trapdoor=LCLATrapdoorHandle(
            backend=keygen_backend,
            status="unavailable",
            opaque_reference=None,
        ),
    )


def entity_key_generation(
    parameters: LCLAParameters,
    identity: str | bytes,
    *,
    seed: int,
) -> LCLAEntityContribution:
    """constructed backend：预采样 s2 后构造并注册 H1(ID)=pk_full。"""

    if parameters.keygen_backend != "constructed_relation":
        raise LCLAError("BACKEND_UNAVAILABLE", "仅 constructed_relation 可用")
    identity_bytes = normalize_identity(identity)
    profile = parameters.profile
    variant = parameters.distribution_variant
    if variant == "paper_literal_distribution":
        s1_rng = np.random.Generator(np.random.PCG64(seed))
        s1 = np.asarray(
            s1_rng.integers(0, profile.q, size=profile.m, dtype=np.int64),
            dtype=np.int64,
        )
        sampler = DiscreteGaussianSampler(
            beta=profile.beta,
            seed=seed + 1_000_019,
            exponent_variant="paper_definition3",
        )
    else:
        sampler = DiscreteGaussianSampler(
            beta=profile.beta,
            seed=seed,
            exponent_variant="standard_lattice",
        )
        s1 = map_centered_to_zq(sampler.sample((profile.m,)).centered, q=profile.q)
    error_f = map_centered_to_zq(sampler.sample((profile.n,)).centered, q=profile.q)
    s2 = map_centered_to_zq(sampler.sample((profile.m,)).centered, q=profile.q)
    combined_s = vector_add_mod(s1, s2, q=profile.q)
    a_combined = matrix_vector_mod(
        parameters.matrix_a,
        combined_s,
        q=profile.q,
        backend=parameters.backend,
    )
    pk_full = vector_add_mod(a_combined, scalar_multiply_mod(2, error_f, q=profile.q), q=profile.q)
    parameters.hash_suite.register_h1(identity_bytes, pk_full)
    entity_share_u1 = vector_add_mod(
        matrix_vector_mod(
            parameters.matrix_a,
            s1,
            q=profile.q,
            backend=parameters.backend,
        ),
        scalar_multiply_mod(2, error_f, q=profile.q),
        q=profile.q,
    )
    return LCLAEntityContribution(
        identity=identity_bytes,
        s1=s1,
        error_f=error_f,
        entity_share_u1=entity_share_u1,
        pk_full=pk_full,
        constructed_s2=s2,
        q=profile.q,
        profile=profile.name,
        backend=parameters.backend,
        keygen_backend=parameters.keygen_backend,
        distribution_variant=variant,
    )


def kgc_key_generation(
    parameters: LCLAParameters,
    contribution: LCLAEntityContribution,
) -> LCLAKGCShare:
    """constructed backend 的 KGC relation 步骤。"""

    _check_contribution_context(parameters, contribution)
    bound_pk = parameters.hash_suite.h1(contribution.identity)
    if not np.array_equal(bound_pk, contribution.pk_full):
        raise LCLAError("H1_BINDING_ERROR", "H1(ID) 与 pk_full 不一致")
    u2 = vector_sub_mod(contribution.pk_full, contribution.entity_share_u1, q=parameters.profile.q)
    preimage = matrix_vector_mod(
        parameters.matrix_a,
        contribution.constructed_s2,
        q=parameters.profile.q,
        backend=parameters.backend,
    )
    if not np.array_equal(preimage, u2):
        raise LCLAError("PREIMAGE_ERROR", "constructed A*s2 != u2")
    return LCLAKGCShare(
        identity=contribution.identity,
        kgc_share_s2=contribution.constructed_s2,
        kgc_target_u2=u2,
        programmed_h1=True,
        trapdoor_used=False,
        sample_pre_used=False,
        q=parameters.profile.q,
        profile=parameters.profile.name,
        backend=parameters.backend,
        keygen_backend=parameters.keygen_backend,
        distribution_variant=contribution.distribution_variant,
    )


def assemble_static_key(
    parameters: LCLAParameters,
    contribution: LCLAEntityContribution,
    kgc_share: LCLAKGCShare,
) -> LCLAStaticKeyPair:
    """组装并验证静态密钥。"""

    _check_contribution_context(parameters, contribution)
    if contribution.identity != kgc_share.identity:
        raise LCLAError("IDENTITY_ERROR", "contribution/KGC identity 不一致")
    if (
        kgc_share.q != parameters.profile.q
        or kgc_share.profile != parameters.profile.name
        or kgc_share.backend != parameters.backend
        or kgc_share.distribution_variant != parameters.distribution_variant
    ):
        raise LCLAError("CONTEXT_ERROR", "KGC share 上下文不一致")
    combined_s = vector_add_mod(contribution.s1, kgc_share.kgc_share_s2, q=parameters.profile.q)
    public = LCLAStaticPublicComponents(
        identity=contribution.identity,
        pk_full=contribution.pk_full,
        entity_share_u1=contribution.entity_share_u1,
        kgc_target_u2=kgc_share.kgc_target_u2,
        q=parameters.profile.q,
        profile=parameters.profile.name,
        backend=parameters.backend,
        keygen_backend=parameters.keygen_backend,
        distribution_variant=contribution.distribution_variant,
    )
    private = LCLAStaticPrivateKey(
        identity=contribution.identity,
        s1=contribution.s1,
        kgc_share_s2=kgc_share.kgc_share_s2,
        combined_s=combined_s,
        error_f=contribution.error_f,
        q=parameters.profile.q,
        profile=parameters.profile.name,
        backend=parameters.backend,
        keygen_backend=parameters.keygen_backend,
        distribution_variant=contribution.distribution_variant,
    )
    key_pair = LCLAStaticKeyPair(
        public_components=public,
        private_key=private,
        programmed_h1=kgc_share.programmed_h1,
        trapdoor_used=kgc_share.trapdoor_used,
        sample_pre_used=kgc_share.sample_pre_used,
        distribution_variant=contribution.distribution_variant,
    )
    if not verify_static_key(parameters, key_pair):
        raise LCLAError("STATIC_KEY_VERIFY_ERROR", "静态密钥验证式失败")
    return key_pair


def verify_static_key(
    parameters: LCLAParameters,
    key_pair: LCLAStaticKeyPair,
    *,
    identity: str | bytes | None = None,
) -> bool:
    """验证 A(s1+s2)+2f=pk_full 以及 u1/u2/preimage 关系。"""

    public = key_pair.public_components
    private = key_pair.private_key
    if identity is not None and normalize_identity(identity) != public.identity:
        return False
    if (
        public.q != parameters.profile.q
        or public.profile != parameters.profile.name
        or public.backend != parameters.backend
        or public.distribution_variant != parameters.distribution_variant
    ):
        return False
    try:
        bound_pk = parameters.hash_suite.h1(public.identity)
        recomputed_pk = vector_add_mod(
            matrix_vector_mod(
                parameters.matrix_a,
                private.combined_s,
                q=parameters.profile.q,
                backend=parameters.backend,
            ),
            scalar_multiply_mod(2, private.error_f, q=parameters.profile.q),
            q=parameters.profile.q,
        )
        recomputed_u1 = vector_add_mod(
            matrix_vector_mod(
                parameters.matrix_a,
                private.s1,
                q=parameters.profile.q,
                backend=parameters.backend,
            ),
            scalar_multiply_mod(2, private.error_f, q=parameters.profile.q),
            q=parameters.profile.q,
        )
        preimage = matrix_vector_mod(
            parameters.matrix_a,
            private.kgc_share_s2,
            q=parameters.profile.q,
            backend=parameters.backend,
        )
    except LCLAError:
        return False
    return bool(
        np.array_equal(bound_pk, public.pk_full)
        and np.array_equal(recomputed_pk, public.pk_full)
        and np.array_equal(recomputed_u1, public.entity_share_u1)
        and np.array_equal(preimage, public.kgc_target_u2)
        and np.array_equal(
            vector_add_mod(
                public.entity_share_u1,
                public.kgc_target_u2,
                q=parameters.profile.q,
            ),
            public.pk_full,
        )
    )


def generate_static_key_pair(
    parameters: LCLAParameters,
    identity: str | bytes,
    *,
    seed: int,
) -> LCLAStaticKeyPair:
    """完整 constructed static-key 流程。"""

    contribution = entity_key_generation(parameters, identity, seed=seed)
    kgc_share = kgc_key_generation(parameters, contribution)
    return assemble_static_key(parameters, contribution, kgc_share)


def _check_contribution_context(
    parameters: LCLAParameters, contribution: LCLAEntityContribution
) -> None:
    if (
        contribution.q != parameters.profile.q
        or contribution.profile != parameters.profile.name
        or contribution.backend != parameters.backend
        or contribution.keygen_backend != parameters.keygen_backend
        or contribution.distribution_variant != parameters.distribution_variant
    ):
        raise LCLAError("CONTEXT_ERROR", "entity contribution 上下文不一致")
