"""Tests for akf log — trust-annotated git history CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from akf.cli import main


class TestLogCli:
    """Test the CLI ``akf log`` command."""

    def _run(self, args):
        runner = CliRunner()
        return runner.invoke(main, args, catch_exceptions=False)

    def test_log_runs_without_error(self):
        """Basic smoke test — the log command should run in any git repo."""
        result = self._run(["log"])
        # Should exit cleanly (0) or with no commits message
        assert result.exit_code == 0

    def test_log_with_count(self):
        """The --count flag should limit the number of commits shown."""
        result = self._run(["log", "--count", "3"])
        assert result.exit_code == 0
        # Output lines should not exceed 3 commit entries
        lines = [l for l in result.output.strip().splitlines() if l.strip()]
        assert len(lines) <= 3

    def test_log_with_trust_flag(self):
        """The --trust flag should filter to only trust-annotated commits.

        In a repo without AKF git notes, this should produce no output.
        """
        result = self._run(["log", "--trust"])
        assert result.exit_code == 0

    def test_log_help(self):
        """The --help flag should display usage information."""
        result = self._run(["log", "--help"])
        assert result.exit_code == 0
        assert "trust-annotated" in result.output.lower() or "trust" in result.output.lower()
