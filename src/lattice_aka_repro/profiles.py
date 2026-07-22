"""读取冻结的协议 profile，不执行协议公式或参数语义推断。"""

from __future__ import annotations

import re
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Final, cast

import yaml

from lattice_aka_repro.errors import (
    InvalidProfileNameError,
    ProfileDocumentError,
    ProfileMissingFieldsError,
    ProfileNotFoundError,
    ProfileSourceMissingError,
    UnsupportedProtocolError,
)

_PROFILE_NAME_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")
_PROFILE_FILES: Final = {
    "c2lake": Path("c2lake/parameter_profiles.yaml"),
    "lcla_aka": Path("lcla_aka/parameter_profiles.yaml"),
}
_COMMON_FIELDS: Final = frozenset({"family", "m", "n", "q", "beta", "q_must_be_prime"})
_PROTOCOL_FIELDS: Final = {
    "c2lake": frozenset({"matrix_shape", "secret_sampling"}),
    "lcla_aka": frozenset({"backend"}),
}
_SOURCE_CHECKOUT_SPECS_DIR: Final = Path(__file__).resolve().parents[2] / "specs"
_DISTRIBUTION_NAME: Final = "lattice-aka-repro"
_INSTALLED_DATA_ROOT: Final = Path("share/lattice_aka_repro/specs")


def load_profile(
    protocol: str,
    name: str,
    *,
    specs_dir: Path | None = None,
) -> dict[str, object]:
    """从协议 YAML 中载入一个 profile，并校验基础结构与必填字段。

    `specs_dir` 默认优先定位源码仓库中的 ``specs`` 目录，普通安装则读取
    distribution data files。显式参数便于测试，也允许提供外部冻结规格目录。
    """

    if protocol not in _PROFILE_FILES:
        supported = ", ".join(sorted(_PROFILE_FILES))
        raise UnsupportedProtocolError(f"不支持协议 {protocol!r}；可选值：{supported}")
    if not _PROFILE_NAME_PATTERN.fullmatch(name):
        raise InvalidProfileNameError(f"非法 profile 名称 {name!r}")

    source = _resolve_profile_source(protocol, specs_dir)
    document = _read_profile_document(source)

    profiles_value = document.get("profiles")
    if not isinstance(profiles_value, dict):
        raise ProfileDocumentError("顶层字段 'profiles' 必须是映射")
    profiles = cast(dict[object, object], profiles_value)

    if name not in profiles:
        available = sorted(key for key in profiles if isinstance(key, str))
        choices = ", ".join(available) if available else "无"
        raise ProfileNotFoundError(f"协议 {protocol!r} 中不存在 {name!r}；可选值：{choices}")
    profile_value = profiles[name]
    if not isinstance(profile_value, dict):
        raise ProfileDocumentError(f"profile {name!r} 必须是映射")

    raw_profile = cast(dict[object, object], profile_value)
    if any(not isinstance(key, str) for key in raw_profile):
        raise ProfileDocumentError(f"profile {name!r} 的字段名必须是字符串")
    profile = {cast(str, key): deepcopy(value) for key, value in raw_profile.items()}

    required = _COMMON_FIELDS | _PROTOCOL_FIELDS[protocol]
    missing = tuple(sorted(required.difference(profile)))
    if missing:
        raise ProfileMissingFieldsError(name, missing)
    return profile


def _read_profile_document(source: Path) -> dict[object, object]:
    if not source.is_file():
        raise ProfileSourceMissingError(f"找不到 profile 文件：{source}")
    try:
        loaded: object = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ProfileDocumentError(f"无法读取 profile 文件：{source}") from error
    if not isinstance(loaded, dict):
        raise ProfileDocumentError("YAML 顶层必须是映射")
    return cast(dict[object, object], loaded)


def _resolve_profile_source(protocol: str, specs_dir: Path | None) -> Path:
    relative_source = _PROFILE_FILES[protocol]
    if specs_dir is not None:
        return specs_dir / relative_source

    checkout_source = _SOURCE_CHECKOUT_SPECS_DIR / relative_source
    if checkout_source.is_file():
        return checkout_source

    installed_suffix = (_INSTALLED_DATA_ROOT / relative_source).as_posix()
    try:
        package_distribution = distribution(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return checkout_source
    for entry in package_distribution.files or ():
        if entry.as_posix().endswith(installed_suffix):
            installed_source = Path(str(package_distribution.locate_file(entry)))
            if installed_source.is_file():
                return installed_source
    return checkout_source
