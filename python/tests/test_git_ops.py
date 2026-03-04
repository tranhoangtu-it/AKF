"""Tests for git_ops.py — stamp_commit, read_commit, trust_log.

Uses temporary git repos to avoid polluting the real repo.
"""

import os
import subprocess
import tempfile

import pytest

from akf.git_ops import stamp_commit, read_commit, trust_log


@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a temporary git repo with one commit."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)

    subprocess.run(["git", "init"], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], capture_output=True, check=True)

    # Create initial commit
    (tmp_path / "README.md").write_text("# test")
    subprocess.run(["git", "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], capture_output=True, check=True)

    yield tmp_path

    os.chdir(old_cwd)


class TestStampCommit:
    def test_stamp_and_read_round_trip(self, tmp_git_repo):
        unit = stamp_commit(content="Fixed auth", kind="code_change",
                            evidence=["all tests pass"], agent="test-agent")
        assert unit is not None
        assert unit.claims[0].content == "Fixed auth"

        loaded = read_commit()
        assert loaded is not None
        assert loaded.claims[0].content == "Fixed auth"
        assert loaded.claims[0].kind == "code_change"
        assert len(loaded.claims[0].evidence) == 1
        assert loaded.agent == "test-agent"

    def test_stamp_uses_commit_message_when_empty(self, tmp_git_repo):
        unit = stamp_commit()
        assert unit.claims[0].content == "initial commit"

    def test_read_commit_no_notes(self, tmp_git_repo):
        result = read_commit()
        assert result is None


class TestTrustLog:
    def test_trust_log_with_stamps(self, tmp_git_repo):
        stamp_commit(content="First change", confidence=0.9)

        # Add another commit
        (tmp_git_repo / "file2.txt").write_text("hello")
        subprocess.run(["git", "add", "."], capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "second commit"], capture_output=True, check=True)
        stamp_commit(content="Second change", confidence=0.3)

        log = trust_log(n=5)
        assert "Trust Log" in log
        assert "+" in log or "~" in log or "-" in log

    def test_trust_log_no_stamps(self, tmp_git_repo):
        log = trust_log(n=5)
        assert "?" in log
