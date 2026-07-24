from __future__ import annotations

from pathlib import Path

import pytest

from lattice_aka_repro.errors import (
    InvalidProfileNameError,
    ProfileDocumentError,
    ProfileMissingFieldsError,
    ProfileNotFoundError,
    ProfileSourceMissingError,
    UnsupportedProtocolError,
)
from lattice_aka_repro.profiles import load_profile


def test_load_c2lake_toy_profile() -> None:
    profile = load_profile("c2lake", "toy")

    assert profile["family"] == "toy"
    assert profile["q"] == 257


def test_load_lcla_toy_profile() -> None:
    profile = load_profile("lcla_aka", "toy")

    assert profile["family"] == "toy"
    assert profile["backend"] == "toy"


def test_default_profile_location_does_not_depend_on_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert load_profile("c2lake", "toy")["m"] == 8


def test_unsupported_protocol_has_stable_error_code() -> None:
    with pytest.raises(UnsupportedProtocolError) as caught:
        load_profile("unknown", "toy")

    assert caught.value.code == "PROFILE_UNSUPPORTED_PROTOCOL"


def test_profile_name_rejects_path_traversal() -> None:
    with pytest.raises(InvalidProfileNameError) as caught:
        load_profile("c2lake", "../toy")

    assert caught.value.code == "PROFILE_INVALID_NAME"


def test_unknown_profile_has_stable_error_code() -> None:
    with pytest.raises(ProfileNotFoundError) as caught:
        load_profile("c2lake", "does_not_exist")

    assert caught.value.code == "PROFILE_NOT_FOUND"


def test_missing_profile_source_has_stable_error_code(tmp_path: Path) -> None:
    with pytest.raises(ProfileSourceMissingError) as caught:
        load_profile("c2lake", "toy", specs_dir=tmp_path)

    assert caught.value.code == "PROFILE_SOURCE_MISSING"


def test_missing_fields_are_sorted_and_stable(tmp_path: Path) -> None:
    _write_profile_yaml(tmp_path, "c2lake", "profiles:\n  toy:\n    family: toy\n")

    with pytest.raises(ProfileMissingFieldsError) as caught:
        load_profile("c2lake", "toy", specs_dir=tmp_path)

    assert caught.value.code == "PROFILE_MISSING_FIELDS"
    assert caught.value.fields == (
        "beta",
        "m",
        "matrix_shape",
        "n",
        "q",
        "q_must_be_prime",
        "secret_sampling",
    )


def test_protocol_specific_field_is_required(tmp_path: Path) -> None:
    yaml_text = """\
profiles:
  toy:
    family: toy
    m: 32
    n: 2
    q: 127
    beta: 1.0
    q_must_be_prime: true
"""
    _write_profile_yaml(tmp_path, "lcla_aka", yaml_text)

    with pytest.raises(ProfileMissingFieldsError) as caught:
        load_profile("lcla_aka", "toy", specs_dir=tmp_path)

    assert caught.value.fields == ("backend",)


def test_malformed_yaml_has_stable_error_code(tmp_path: Path) -> None:
    _write_profile_yaml(tmp_path, "c2lake", "profiles: [unterminated")

    with pytest.raises(ProfileDocumentError) as caught:
        load_profile("c2lake", "toy", specs_dir=tmp_path)

    assert caught.value.code == "PROFILE_DOCUMENT_INVALID"


def test_null_profile_is_an_invalid_document(tmp_path: Path) -> None:
    _write_profile_yaml(tmp_path, "c2lake", "profiles:\n  toy: null\n")

    with pytest.raises(ProfileDocumentError) as caught:
        load_profile("c2lake", "toy", specs_dir=tmp_path)

    assert caught.value.code == "PROFILE_DOCUMENT_INVALID"


def test_loaded_profile_is_a_fresh_copy() -> None:
    first = load_profile("c2lake", "toy")
    first["family"] = "changed"

    assert load_profile("c2lake", "toy")["family"] == "toy"


def _write_profile_yaml(root: Path, protocol: str, content: str) -> None:
    directory = root / protocol
    directory.mkdir(parents=True)
    (directory / "parameter_profiles.yaml").write_text(content, encoding="utf-8")
