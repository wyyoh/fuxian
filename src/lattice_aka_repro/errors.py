"""供调用方稳定识别的项目异常。"""

from __future__ import annotations

from typing import ClassVar


class ReproductionError(ValueError):
    """所有可预期输入错误的基类。"""

    code: ClassVar[str] = "REPRODUCTION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(f"{self.code}: {message}")


class UnsupportedProtocolError(ReproductionError):
    """协议名称不在冻结白名单中。"""

    code = "PROFILE_UNSUPPORTED_PROTOCOL"


class InvalidProfileNameError(ReproductionError):
    """profile 名称不符合安全标识符格式。"""

    code = "PROFILE_INVALID_NAME"


class ProfileSourceMissingError(ReproductionError):
    """找不到 profile YAML 来源。"""

    code = "PROFILE_SOURCE_MISSING"


class ProfileDocumentError(ReproductionError):
    """profile YAML 不能解析为约定结构。"""

    code = "PROFILE_DOCUMENT_INVALID"


class ProfileNotFoundError(ReproductionError):
    """指定 profile 不存在。"""

    code = "PROFILE_NOT_FOUND"


class ProfileMissingFieldsError(ReproductionError):
    """profile 缺少当前协议要求的基础字段。"""

    code = "PROFILE_MISSING_FIELDS"

    def __init__(self, profile: str, fields: tuple[str, ...]) -> None:
        self.profile = profile
        self.fields = fields
        super().__init__(f"profile {profile!r} 缺少字段：{', '.join(fields)}")


class SeedNotIntegerError(ReproductionError):
    """seed 不是整数。"""

    code = "SEED_NOT_INTEGER"


class SeedNegativeError(ReproductionError):
    """seed 是负数。"""

    code = "SEED_NEGATIVE"


class MetadataValidationError(ReproductionError):
    """运行元数据不满足 evidence 基础约束。"""

    code = "METADATA_INVALID"
