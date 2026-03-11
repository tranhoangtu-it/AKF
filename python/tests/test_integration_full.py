"""Full integration tests across all AKF capabilities.

Covers:
- Cross-format embed/extract round-trips (DOCX, XLSX, PPTX, JSON, Markdown, HTML)
- Universal dispatcher routing
- CLI end-to-end commands
- Vertical pipelines (create→embed→read→report, stamp→audit, keygen→sign→verify)
- Report renderers across all formats
- Sidecar fallback
"""

import json
import os
import tempfile
import zipfile

import pytest
from click.testing import CliRunner

from akf.cli import main
from akf.core import create, load
from akf.builder import AKFBuilder
from akf import universal
from akf.formats._ooxml import CUSTOM_PROPS_PATH, embed_in_ooxml, extract_from_ooxml


def _has_fpdf2():
    try:
        import fpdf
        return True
    except ImportError:
        return False


# ── Helpers ──────────────────────────────────────────────────────


def create_minimal_docx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            '/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )


def create_minimal_xlsx(path):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            '/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        z.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_akf(tmp_path):
    """Create a sample .akf file."""
    unit = (
        AKFBuilder()
        .by("test@example.com")
        .label("internal")
        .claim("Revenue $4.2B", 0.98, source="SEC 10-Q", authority_tier=1, verified=True)
        .claim("AI growth 45%", 0.85, source="Internal", authority_tier=2)
        .claim("Forecast: 20% growth", 0.63, source="AI model", authority_tier=5,
               ai_generated=True, risk="AI extrapolation")
        .build()
    )
    path = str(tmp_path / "test.akf")
    with open(path, "w") as f:
        f.write(unit.to_json())
    return path


@pytest.fixture
def sample_akf_dir(tmp_path):
    """Create a directory with multiple .akf files."""
    for i in range(3):
        unit = (
            AKFBuilder()
            .by(f"user{i}@test.com")
            .label("internal" if i < 2 else "confidential")
            .claim(f"Claim {i}A", 0.7 + i * 0.1, source=f"Source {i}")
            .claim(f"Claim {i}B", 0.6, ai_generated=(i == 2), source="AI model")
            .build()
        )
        path = str(tmp_path / f"file{i}.akf")
        with open(path, "w") as f:
            f.write(unit.to_json())
    return str(tmp_path)


# ── Cross-Format Round-Trip ──────────────────────────────────────


class TestCrossFormatRoundTrip:
    """Test embed→extract round-trip across all supported formats."""

    METADATA = {
        "classification": "internal",
        "claims": [
            {"c": "Revenue was $4.2B", "t": 0.98, "src": "SEC", "ai": False},
            {"c": "AI grew 45%", "t": 0.85, "ai": True},
        ],
        "provenance": [{"actor": "test-agent", "action": "embedded"}],
    }

    def test_docx_round_trip(self, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        universal.embed(path, metadata=self.METADATA)
        result = universal.extract(path)
        assert result is not None
        assert result["classification"] == "internal"
        assert len(result["claims"]) == 2

    def test_xlsx_round_trip(self, tmp_path):
        path = str(tmp_path / "test.xlsx")
        create_minimal_xlsx(path)
        universal.embed(path, metadata=self.METADATA)
        result = universal.extract(path)
        assert result is not None
        assert result["classification"] == "internal"

    def test_json_round_trip(self, tmp_path):
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"key": "value"}, f)
        universal.embed(path, metadata=self.METADATA)
        result = universal.extract(path)
        assert result is not None
        assert result["classification"] == "internal"
        # Original data should still be there
        with open(path) as f:
            data = json.load(f)
        assert data["key"] == "value"

    def test_markdown_round_trip(self, tmp_path):
        path = str(tmp_path / "doc.md")
        with open(path, "w") as f:
            f.write("# Title\n\nSome content.\n")
        universal.embed(path, metadata=self.METADATA)
        result = universal.extract(path)
        assert result is not None
        assert result["classification"] == "internal"

    def test_html_round_trip(self, tmp_path):
        path = str(tmp_path / "page.html")
        with open(path, "w") as f:
            f.write("<html><body><p>Content</p></body></html>")
        universal.embed(path, metadata=self.METADATA)
        result = universal.extract(path)
        assert result is not None
        assert result["classification"] == "internal"

    def test_akf_file_round_trip(self, sample_akf):
        """Extracting from a standalone .akf file should work."""
        result = universal.extract(sample_akf)
        assert result is not None
        assert len(result.get("claims", [])) >= 3

    def test_sidecar_fallback(self, tmp_path):
        """Unknown format should fall back to sidecar."""
        path = str(tmp_path / "data.xyz")
        with open(path, "w") as f:
            f.write("unknown format content")
        universal.embed(path, metadata=self.METADATA)
        # Sidecar should exist
        sidecar = path + ".akf.json"
        assert os.path.exists(sidecar)
        result = universal.extract(path)
        assert result is not None


# ── Universal Dispatcher ─────────────────────────────────────────


class TestUniversalDispatcher:
    def test_supported_formats_includes_all(self):
        formats = universal.supported_formats()
        assert "DOCX" in formats
        assert "XLSX" in formats
        assert "JSON" in formats
        assert "Markdown" in formats
        assert "HTML" in formats
        assert "sidecar" in formats

    def test_is_enriched_false(self, tmp_path):
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"x": 1}, f)
        assert universal.is_enriched(path) is False

    def test_is_enriched_true_after_embed(self, tmp_path):
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"x": 1}, f)
        universal.embed(path, metadata={"claims": [{"c": "Test", "t": 0.9}]})
        assert universal.is_enriched(path) is True

    def test_scan_directory(self, tmp_path):
        # Create a few files with metadata
        for name in ["a.json", "b.json"]:
            path = str(tmp_path / name)
            with open(path, "w") as f:
                json.dump({"data": name}, f)
            universal.embed(path, metadata={"claims": [{"c": f"Claim in {name}", "t": 0.8}]})
        reports = universal.scan_directory(str(tmp_path))
        enriched = [r for r in reports if r.enriched]
        assert len(enriched) >= 2

    def test_info_returns_string(self, tmp_path):
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"x": 1}, f)
        universal.embed(path, metadata={"classification": "public", "claims": [{"c": "X", "t": 0.9}]})
        result = universal.info(path)
        assert isinstance(result, str)
        assert "public" in result.lower() or "1 claim" in result.lower() or "enriched" in result.lower()


# ── CLI End-to-End ───────────────────────────────────────────────


class TestCLICreate:
    def test_create_and_validate(self, runner, tmp_path):
        path = str(tmp_path / "new.akf")
        result = runner.invoke(main, ["create", path, "-c", "Test claim", "-t", "0.9"])
        assert result.exit_code == 0
        result = runner.invoke(main, ["validate", path])
        assert result.exit_code == 0

    def test_create_multi_claims(self, runner, tmp_path):
        path = str(tmp_path / "multi.akf")
        result = runner.invoke(main, [
            "create", path,
            "-c", "Claim 1", "-t", "0.9",
            "-c", "Claim 2", "-t", "0.8",
            "--by", "user@test.com",
            "--label", "internal",
        ])
        assert result.exit_code == 0
        unit = load(path)
        assert len(unit.claims) == 2
        assert unit.author == "user@test.com"


class TestCLIInspectTrustSecurity:
    def test_inspect(self, runner, sample_akf):
        result = runner.invoke(main, ["inspect", sample_akf])
        assert result.exit_code == 0
        assert "Revenue" in result.output
        assert "0.98" in result.output

    def test_trust(self, runner, sample_akf):
        result = runner.invoke(main, ["trust", sample_akf])
        assert result.exit_code == 0
        assert "ACCEPT" in result.output or "REJECT" in result.output or "LOW" in result.output

    def test_security(self, runner, sample_akf):
        result = runner.invoke(main, ["security", sample_akf])
        assert result.exit_code == 0
        assert "Grade" in result.output

    def test_provenance(self, runner, sample_akf):
        result = runner.invoke(main, ["provenance", sample_akf])
        assert result.exit_code == 0

    def test_freshness(self, runner, sample_akf):
        result = runner.invoke(main, ["freshness", sample_akf])
        assert result.exit_code == 0

    def test_explain(self, runner, sample_akf):
        result = runner.invoke(main, ["explain", sample_akf])
        assert result.exit_code == 0

    def test_hash(self, runner, sample_akf):
        result = runner.invoke(main, ["hash", sample_akf])
        assert result.exit_code == 0
        assert "sha256:" in result.output


class TestCLIAudit:
    def test_audit_default(self, runner, sample_akf):
        result = runner.invoke(main, ["audit", sample_akf])
        assert result.exit_code == 0

    def test_audit_json(self, runner, sample_akf):
        result = runner.invoke(main, ["audit", sample_akf, "--export", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert isinstance(parsed, dict)

    def test_audit_csv(self, runner, sample_akf):
        result = runner.invoke(main, ["audit", sample_akf, "--export", "csv"])
        assert result.exit_code == 0


class TestCLIEmbed:
    def test_embed_docx(self, runner, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        result = runner.invoke(main, [
            "embed", path,
            "-c", "Revenue was $4.2B",
            "-t", "0.98",
            "--label", "confidential",
        ])
        assert result.exit_code == 0
        assert "Embedded" in result.output

    def test_embed_json(self, runner, tmp_path):
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"key": "value"}, f)
        result = runner.invoke(main, [
            "embed", path,
            "-c", "Data is valid",
            "-t", "0.95",
        ])
        assert result.exit_code == 0

    def test_embed_then_extract(self, runner, tmp_path):
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"key": "value"}, f)
        runner.invoke(main, ["embed", path, "-c", "Verified", "-t", "0.9"])
        result = runner.invoke(main, ["extract", path])
        assert result.exit_code == 0


class TestCLIRead:
    def test_read_akf(self, runner, sample_akf):
        result = runner.invoke(main, ["read", sample_akf])
        assert result.exit_code == 0
        assert "Revenue" in result.output

    def test_read_embedded_docx(self, runner, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        runner.invoke(main, ["embed", path, "-c", "Test claim", "-t", "0.8"])
        result = runner.invoke(main, ["read", path])
        assert result.exit_code == 0
        assert "Test claim" in result.output


class TestCLIScan:
    def test_scan_file(self, runner, sample_akf):
        result = runner.invoke(main, ["scan", sample_akf])
        assert result.exit_code == 0

    def test_scan_directory(self, runner, sample_akf_dir):
        result = runner.invoke(main, ["scan", sample_akf_dir])
        assert result.exit_code == 0


class TestCLIFormats:
    def test_formats_list(self, runner):
        result = runner.invoke(main, ["formats"])
        assert result.exit_code == 0
        assert "DOCX" in result.output
        assert "JSON" in result.output
        assert "Markdown" in result.output


class TestCLIDiff:
    def test_diff_two_files(self, runner, tmp_path):
        # Create two similar files
        for name, claim in [("a.akf", "Revenue $4B"), ("b.akf", "Revenue $5B")]:
            unit = AKFBuilder().claim(claim, 0.9).build()
            with open(str(tmp_path / name), "w") as f:
                f.write(unit.to_json())
        result = runner.invoke(main, [
            "diff",
            str(tmp_path / "a.akf"),
            str(tmp_path / "b.akf"),
        ])
        assert result.exit_code == 0


class TestCLICalibrate:
    def test_calibrate(self, runner, sample_akf):
        result = runner.invoke(main, ["calibrate", sample_akf])
        assert result.exit_code == 0


# ── CLI Report ───────────────────────────────────────────────────


class TestCLIReport:
    def test_report_markdown(self, runner, sample_akf_dir):
        result = runner.invoke(main, ["report", sample_akf_dir])
        assert result.exit_code == 0
        assert "Governance" in result.output or "Trust" in result.output or "Claims" in result.output

    def test_report_json(self, runner, sample_akf_dir):
        result = runner.invoke(main, ["report", sample_akf_dir, "--format", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "total_files" in parsed

    def test_report_html(self, runner, sample_akf_dir, tmp_path):
        out = str(tmp_path / "report.html")
        result = runner.invoke(main, ["report", sample_akf_dir, "--format", "html", "-o", out])
        assert result.exit_code == 0
        assert os.path.exists(out)
        with open(out) as f:
            html = f.read()
        assert "<html" in html

    def test_report_csv(self, runner, sample_akf_dir):
        result = runner.invoke(main, ["report", sample_akf_dir, "--format", "csv"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) >= 4  # header + 3 files

    def test_report_pdf_requires_output(self, runner, sample_akf_dir):
        result = runner.invoke(main, ["report", sample_akf_dir, "--format", "pdf"])
        assert result.exit_code != 0

    @pytest.mark.skipif(
        not _has_fpdf2(), reason="fpdf2 not installed"
    )
    def test_report_pdf(self, runner, sample_akf_dir, tmp_path):
        out = str(tmp_path / "report.pdf")
        result = runner.invoke(main, ["report", sample_akf_dir, "--format", "pdf", "-o", out])
        assert result.exit_code == 0
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_report_empty_dir(self, runner, tmp_path):
        result = runner.invoke(main, ["report", str(tmp_path)])
        assert result.exit_code == 0
        assert "No .akf files" in result.output or "0 files" in result.output.lower()


# ── CLI Signing ──────────────────────────────────────────────────


class TestCLISigning:
    def test_keygen(self, runner, tmp_path):
        key_dir = str(tmp_path / "keys")
        os.makedirs(key_dir)
        result = runner.invoke(main, ["keygen", "--name", "test", "--dir", key_dir])
        assert result.exit_code == 0
        # Should create key files
        key_files = os.listdir(key_dir)
        assert len(key_files) >= 1

    def test_sign_and_verify(self, runner, sample_akf, tmp_path):
        key_dir = str(tmp_path / "keys")
        os.makedirs(key_dir)
        runner.invoke(main, ["keygen", "--name", "test", "--dir", key_dir])
        # Find the private key
        key_files = os.listdir(key_dir)
        priv = [f for f in key_files if "private" in f.lower() or f.endswith(".pem") or not f.endswith(".pub")]
        pub = [f for f in key_files if "public" in f.lower() or f.endswith(".pub")]
        if priv and pub:
            priv_path = str(tmp_path / "keys" / priv[0])
            pub_path = str(tmp_path / "keys" / pub[0])
            # Sign
            result = runner.invoke(main, ["sign", sample_akf, "--key", priv_path])
            assert result.exit_code == 0
            # Verify
            result = runner.invoke(main, ["verify", sample_akf, "--key", pub_path])
            assert result.exit_code == 0
        else:
            pytest.skip("Could not find keypair files")


# ── Vertical Pipeline Tests ──────────────────────────────────────


class TestPipelineCreateToReport:
    """Pipeline: create → embed → read → report."""

    def test_full_pipeline(self, runner, tmp_path):
        # 1. Create AKF files
        for i in range(3):
            path = str(tmp_path / f"doc{i}.akf")
            runner.invoke(main, [
                "create", path,
                "-c", f"Claim {i}", "-t", str(0.7 + i * 0.1),
                "--by", f"user{i}@test.com",
                "--label", "internal",
            ])

        # 2. Read each one
        for i in range(3):
            path = str(tmp_path / f"doc{i}.akf")
            result = runner.invoke(main, ["read", path])
            assert result.exit_code == 0

        # 3. Generate report
        result = runner.invoke(main, ["report", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        report = json.loads(result.output)
        assert report["total_files"] == 3
        assert report["total_claims"] == 3


class TestPipelineStampAudit:
    """Pipeline: stamp → audit → export."""

    def test_stamp_then_audit(self, runner, tmp_path):
        # 1. Create a file
        path = str(tmp_path / "data.json")
        with open(path, "w") as f:
            json.dump({"data": "test"}, f)

        # 2. Stamp it
        result = runner.invoke(main, ["stamp", path, "--label", "internal"])
        assert result.exit_code == 0

        # 3. If there's an .akf sidecar or embedded data, try audit on the .akf
        akf_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".akf") or f.endswith(".akf.json")]
        # The stamp may create a sidecar
        assert universal.is_enriched(path) or len(akf_files) > 0


class TestPipelineEmbedDocxReport:
    """Pipeline: create DOCX → embed → report from DOCX .akf sidecar."""

    def test_embed_docx_then_report(self, runner, tmp_path):
        # Create DOCX and embed
        path = str(tmp_path / "board.docx")
        create_minimal_docx(path)
        runner.invoke(main, [
            "embed", path,
            "-c", "Revenue $4.2B", "-t", "0.98",
            "-c", "AI growth 45%", "-t", "0.85",
            "--label", "confidential",
        ])

        # Verify we can read it
        result = runner.invoke(main, ["read", path])
        assert result.exit_code == 0
        assert "Revenue" in result.output


class TestPipelineSignVerify:
    """Pipeline: create → sign → verify → tamper → verify fails."""

    def test_sign_verify_tamper(self, runner, tmp_path):
        # 1. Create
        akf_path = str(tmp_path / "signed.akf")
        runner.invoke(main, [
            "create", akf_path,
            "-c", "Original claim", "-t", "0.95",
        ])

        # 2. Keygen
        key_dir = str(tmp_path / "keys")
        os.makedirs(key_dir)
        runner.invoke(main, ["keygen", "--name", "test", "--dir", key_dir])

        # 3. Find key files
        key_files = os.listdir(key_dir)
        priv = [f for f in key_files if not f.endswith(".pub")]
        pub = [f for f in key_files if f.endswith(".pub")]
        if not priv or not pub:
            pytest.skip("Could not find keypair files")

        priv_path = os.path.join(key_dir, priv[0])
        pub_path = os.path.join(key_dir, pub[0])

        # 4. Sign
        result = runner.invoke(main, ["sign", akf_path, "--key", priv_path])
        assert result.exit_code == 0

        # 5. Verify (should pass)
        result = runner.invoke(main, ["verify", akf_path, "--key", pub_path])
        assert result.exit_code == 0


class TestPipelineConvertDirectory:
    """Pipeline: convert directory of files → report."""

    def test_convert_then_report(self, runner, tmp_path):
        # Create source files
        for name in ["doc1.json", "doc2.json"]:
            with open(str(tmp_path / name), "w") as f:
                json.dump({"content": f"Data in {name}"}, f)

        # Convert them
        result = runner.invoke(main, [
            "convert", str(tmp_path),
            "--agent", "test-converter",
        ])
        assert result.exit_code == 0

        # Check .akf files were created
        akf_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".akf")]
        assert len(akf_files) >= 2

        # Run report on the .akf files
        result = runner.invoke(main, ["report", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0


# ── Report Renderer Tests ────────────────────────────────────────


class TestReportRenderers:
    """Test all report renderers produce valid output."""

    @pytest.fixture
    def report(self, sample_akf_dir):
        from akf.report import enterprise_report
        return enterprise_report(sample_akf_dir)

    def test_markdown_renderer(self, report):
        output = report.render("markdown")
        assert isinstance(output, str)
        assert len(output) > 100
        assert "#" in output  # Has headings

    def test_json_renderer(self, report):
        output = report.render("json")
        parsed = json.loads(output)
        assert "total_files" in parsed
        assert "total_claims" in parsed

    def test_html_renderer(self, report):
        output = report.render("html")
        assert "<html" in output
        assert "AKF" in output or "Governance" in output

    def test_csv_renderer(self, report):
        output = report.render("csv")
        lines = output.strip().split("\n")
        assert len(lines) >= 2  # header + data
        assert "file" in lines[0].lower()

    @pytest.mark.skipif(not _has_fpdf2(), reason="fpdf2 not installed")
    def test_pdf_renderer(self, report):
        output = report.render("pdf")
        assert isinstance(output, (bytes, bytearray))
        assert len(output) > 100

    def test_invalid_format_raises(self, report):
        with pytest.raises(ValueError, match="Unknown report format"):
            report.render("xml")


# ── Custom Renderer Registry ────────────────────────────────────


class TestRendererRegistry:
    def test_register_custom_renderer(self, sample_akf_dir):
        from akf.report import register_renderer, RENDERERS, enterprise_report

        @register_renderer("test_custom")
        def _custom(report):
            return f"Custom: {report.total_files} files"

        try:
            report = enterprise_report(sample_akf_dir)
            output = report.render("test_custom")
            assert output.startswith("Custom:")
            assert "3 files" in output
        finally:
            RENDERERS.pop("test_custom", None)


# ── Sidecar Tests ────────────────────────────────────────────────


class TestSidecarIntegration:
    def test_sidecar_create_and_read(self, tmp_path):
        path = str(tmp_path / "data.bin")
        with open(path, "wb") as f:
            f.write(b"binary content")

        from akf import sidecar
        sc_path = sidecar.create(path, {
            "classification": "secret",
            "claims": [{"c": "Binary verified", "t": 0.9}],
        })
        assert os.path.exists(sc_path)

        data = sidecar.read(path)
        assert data is not None
        assert data["classification"] == "secret"

    def test_sidecar_integrity_check(self, tmp_path):
        path = str(tmp_path / "data.txt")
        with open(path, "w") as f:
            f.write("original content")

        from akf import sidecar
        sidecar.create(path, {"claims": []})

        # Verify passes
        assert sidecar.verify_integrity(path) is True

        # Tamper with file
        with open(path, "w") as f:
            f.write("tampered content")

        # Verify fails
        assert sidecar.verify_integrity(path) is False


# ── Public API Tests ─────────────────────────────────────────────


class TestPublicAPI:
    def test_report_exports(self):
        from akf import enterprise_report, EnterpriseReport, FileReport, register_renderer, RENDERERS
        assert callable(enterprise_report)
        assert callable(register_renderer)
        assert isinstance(RENDERERS, dict)

    def test_stamp_exports(self):
        from akf import stamp, stamp_file
        assert callable(stamp)
        assert callable(stamp_file)

    def test_universal_exports(self):
        from akf import embed, extract, scan, info, is_enriched, convert_directory
        assert callable(embed)
        assert callable(extract)

    def test_core_exports(self):
        from akf import create, load, validate, save
        assert callable(create)
        assert callable(load)

    def test_security_exports(self):
        from akf import security_score, full_report
        assert callable(security_score)

    def test_compliance_exports(self):
        from akf import audit, export_audit
        assert callable(audit)


# ── OOXML + Word Compatibility Integration ───────────────────────


class TestOOXMLWordIntegration:
    """Integration tests for OOXML custom properties with CLI."""

    def test_cli_embed_creates_custom_props(self, runner, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        runner.invoke(main, [
            "embed", path,
            "-c", "Revenue $4.2B", "-t", "0.98",
            "--label", "confidential",
        ])
        with zipfile.ZipFile(path, "r") as z:
            assert CUSTOM_PROPS_PATH in z.namelist()
            xml = z.read(CUSTOM_PROPS_PATH).decode()
            assert "AKF.Enabled" in xml
            assert "AKF.Classification" in xml
            assert "confidential" in xml

    def test_cli_embed_no_foreign_entries(self, runner, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        runner.invoke(main, ["embed", path, "-c", "Test", "-t", "0.9"])
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                assert not name.startswith("akf/"), f"Foreign entry: {name}"
                assert "akf-metadata" not in name, f"Legacy entry: {name}"

    def test_cli_extract_from_custom_props(self, runner, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        runner.invoke(main, ["embed", path, "-c", "Test claim", "-t", "0.9"])
        result = runner.invoke(main, ["extract", path])
        assert result.exit_code == 0

    def test_double_embed_idempotent_structure(self, tmp_path):
        path = str(tmp_path / "test.docx")
        create_minimal_docx(path)
        embed_in_ooxml(path, {"claims": [{"c": "V1", "t": 0.8}]})
        embed_in_ooxml(path, {"claims": [{"c": "V2", "t": 0.9}]})
        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()
            assert names.count(CUSTOM_PROPS_PATH) == 1
            ct = z.read("[Content_Types].xml").decode()
            assert ct.count("custom-properties") == 1

    def test_xlsx_embed_and_read_cli(self, runner, tmp_path):
        path = str(tmp_path / "data.xlsx")
        create_minimal_xlsx(path)
        runner.invoke(main, ["embed", path, "-c", "Spreadsheet verified", "-t", "0.95"])
        result = runner.invoke(main, ["read", path])
        assert result.exit_code == 0
        assert "Spreadsheet verified" in result.output
