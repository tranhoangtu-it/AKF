"""Tests for the Go format handler."""

import pytest

from akf.formats.go_format import GoHandler


@pytest.fixture
def handler() -> GoHandler:
    return GoHandler()


@pytest.fixture
def tmp_go(tmp_path):
    def _make(content: str = "", name: str = "main.go") -> str:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)
    return _make


SAMPLE_GO = 'package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'


class TestGoHandlerAttributes:
    def test_format_name(self, handler: GoHandler) -> None:
        assert handler.FORMAT_NAME == "Go"

    def test_extensions(self, handler: GoHandler) -> None:
        assert ".go" in handler.EXTENSIONS

    def test_mode(self, handler: GoHandler) -> None:
        assert handler.MODE == "embedded"

    def test_no_dependencies(self, handler: GoHandler) -> None:
        assert handler.DEPENDENCIES == []


class TestEmbedExtract:
    def test_round_trip(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go(SAMPLE_GO)
        metadata = {"akf": "1.0", "overall_trust": 0.9, "claims": []}

        handler.embed(filepath, metadata)
        result = handler.extract(filepath)

        assert result is not None
        assert result["akf"] == "1.0"
        assert result["overall_trust"] == 0.9

    def test_preserves_go_code(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go(SAMPLE_GO)
        handler.embed(filepath, {"akf": "1.0", "claims": []})

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "package main" in content
        assert 'import "fmt"' in content
        assert "func main()" in content

    def test_re_embed_replaces(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go(SAMPLE_GO)

        handler.embed(filepath, {"akf": "1.0", "overall_trust": 0.5, "claims": []})
        handler.embed(filepath, {"akf": "1.0", "overall_trust": 0.99, "claims": []})

        result = handler.extract(filepath)
        assert result is not None
        assert result["overall_trust"] == 0.99

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.count("// _akf:") == 1

    def test_go_code_still_valid(self, handler: GoHandler, tmp_go) -> None:
        """Embedded comment should not break Go syntax."""
        filepath = tmp_go(SAMPLE_GO)
        handler.embed(filepath, {"akf": "1.0", "claims": []})

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # First line is the AKF comment
        assert lines[0].startswith("// _akf:")
        # Second line is package declaration
        assert lines[1].startswith("package main")


class TestExtractNone:
    def test_no_akf_comment(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go(SAMPLE_GO)
        assert handler.extract(filepath) is None

    def test_empty_file(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go("")
        assert handler.extract(filepath) is None


class TestIsEnriched:
    def test_enriched(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go(SAMPLE_GO)
        handler.embed(filepath, {"akf": "1.0", "claims": []})
        assert handler.is_enriched(filepath) is True

    def test_not_enriched(self, handler: GoHandler, tmp_go) -> None:
        filepath = tmp_go(SAMPLE_GO)
        assert handler.is_enriched(filepath) is False


class TestModuleConvenience:
    def test_module_embed_extract(self, tmp_go) -> None:
        from akf.formats.go_format import embed as go_embed
        from akf.formats.go_format import extract as go_extract

        filepath = tmp_go(SAMPLE_GO)
        go_embed(filepath, {"akf": "1.0", "claims": []})
        result = go_extract(filepath)
        assert result is not None
        assert result["akf"] == "1.0"
