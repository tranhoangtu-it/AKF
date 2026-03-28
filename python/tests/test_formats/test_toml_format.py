"""Tests for the TOML format handler."""

import json

import pytest

from akf.formats.toml_format import TOMLHandler


@pytest.fixture
def handler() -> TOMLHandler:
    return TOMLHandler()


@pytest.fixture
def tmp_toml(tmp_path):
    """Helper that returns a factory for temp TOML files."""

    def _make(content: str = "", name: str = "test.toml") -> str:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _make


# --------------------------------------------------------------------------
# Class attributes
# --------------------------------------------------------------------------


class TestTOMLHandlerAttributes:
    def test_format_name(self, handler: TOMLHandler) -> None:
        assert handler.FORMAT_NAME == "TOML"

    def test_extensions(self, handler: TOMLHandler) -> None:
        assert ".toml" in handler.EXTENSIONS

    def test_mode(self, handler: TOMLHandler) -> None:
        assert handler.MODE == "embedded"

    def test_no_dependencies(self, handler: TOMLHandler) -> None:
        assert handler.DEPENDENCIES == []


# --------------------------------------------------------------------------
# embed / extract round-trip
# --------------------------------------------------------------------------


class TestEmbedExtract:
    def test_round_trip(self, handler: TOMLHandler, tmp_toml) -> None:
        filepath = tmp_toml('[project]\nname = "myapp"\n')
        metadata = {"akf": "1.0", "overall_trust": 0.85, "claims": []}

        handler.embed(filepath, metadata)
        result = handler.extract(filepath)

        assert result is not None
        assert result["akf"] == "1.0"
        assert result["overall_trust"] == 0.85

    def test_preserves_existing_content(self, handler: TOMLHandler, tmp_toml) -> None:
        original = '[project]\nname = "myapp"\nversion = "1.0"\n'
        filepath = tmp_toml(original)
        metadata = {"akf": "1.0", "claims": []}

        handler.embed(filepath, metadata)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Original content should still be there after the AKF comment
        assert 'name = "myapp"' in content
        assert 'version = "1.0"' in content

    def test_re_embed_replaces(self, handler: TOMLHandler, tmp_toml) -> None:
        filepath = tmp_toml('[project]\nname = "test"\n')

        handler.embed(filepath, {"akf": "1.0", "overall_trust": 0.5, "claims": []})
        handler.embed(filepath, {"akf": "1.0", "overall_trust": 0.95, "claims": []})

        result = handler.extract(filepath)
        assert result is not None
        assert result["overall_trust"] == 0.95

        # Should not have duplicate AKF comments
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.count("# _akf:") == 1


# --------------------------------------------------------------------------
# extract returns None for non-enriched
# --------------------------------------------------------------------------


class TestExtractNone:
    def test_no_akf_comment(self, handler: TOMLHandler, tmp_toml) -> None:
        filepath = tmp_toml('[project]\nname = "test"\n')
        result = handler.extract(filepath)
        assert result is None

    def test_empty_file(self, handler: TOMLHandler, tmp_toml) -> None:
        filepath = tmp_toml("")
        result = handler.extract(filepath)
        assert result is None


# --------------------------------------------------------------------------
# is_enriched
# --------------------------------------------------------------------------


class TestIsEnriched:
    def test_enriched(self, handler: TOMLHandler, tmp_toml) -> None:
        filepath = tmp_toml('[project]\nname = "test"\n')
        handler.embed(filepath, {"akf": "1.0", "claims": []})
        assert handler.is_enriched(filepath) is True

    def test_not_enriched(self, handler: TOMLHandler, tmp_toml) -> None:
        filepath = tmp_toml('[project]\nname = "test"\n')
        assert handler.is_enriched(filepath) is False


# --------------------------------------------------------------------------
# Module-level convenience functions
# --------------------------------------------------------------------------


class TestModuleConvenience:
    def test_module_embed_extract(self, tmp_toml) -> None:
        from akf.formats.toml_format import embed as toml_embed
        from akf.formats.toml_format import extract as toml_extract

        filepath = tmp_toml('[tool]\nkey = "value"\n')
        toml_embed(filepath, {"akf": "1.0", "claims": []})
        result = toml_extract(filepath)
        assert result is not None
        assert result["akf"] == "1.0"
