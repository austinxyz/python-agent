"""Validates scripts/build-and-push.sh per the nas-deployment spec.

Static checks only — does not actually run the script (pushing real
images requires creds + network).
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "build-and-push.sh"


def _read() -> str:
    if not SCRIPT.exists():
        pytest.fail(f"{SCRIPT} does not exist")
    return SCRIPT.read_text(encoding="utf-8")


class TestBuildPushScript:
    def test_exists(self):
        assert SCRIPT.exists(), f"missing {SCRIPT}"

    def test_executable_bit(self):
        # On Windows the executable bit is not enforced by the FS, but the file
        # still needs to be runnable via `bash`. Check it has a shebang instead.
        content = _read()
        assert content.startswith("#!"), "must have a shebang line"
        assert "bash" in content.split("\n", 1)[0], "shebang should reference bash"

    def test_set_e_strict_mode(self):
        assert re.search(r"^set -e", _read(), flags=re.MULTILINE), (
            "script must use 'set -e' to fail fast on any sub-command failure"
        )

    def test_targets_amd64_only(self):
        content = _read()
        assert "linux/amd64" in content, "must build linux/amd64"
        # Multi-arch (linux/arm64) is explicitly out of scope per design §2
        assert "linux/arm64" not in content, (
            "multi-arch is explicitly out of scope; remove linux/arm64"
        )

    def test_uses_buildx_with_push(self):
        content = _read()
        assert "docker buildx" in content
        assert "--push" in content, "must use --push to publish to registry"
        assert "--load" not in content, "must NOT --load (that's for local-only builds)"

    def test_dual_tags(self):
        """Each repo gets both :latest and :v<date>-<sha> tags. Allow ${VAR}/repo:tag form."""
        content = _read()
        # Accept either literal "xuaustin/" or "${DOCKER_USERNAME}/"
        assert re.search(
            r"(?:xuaustin|\$\{DOCKER_USERNAME\}|\$DOCKER_USERNAME)/python-agent-api:latest",
            content,
        ), "api :latest tag missing"
        assert re.search(
            r"(?:xuaustin|\$\{DOCKER_USERNAME\}|\$DOCKER_USERNAME)/python-agent-frontend:latest",
            content,
        ), "frontend :latest tag missing"
        # If using a variable, ensure it's defined as 'xuaustin'
        if "DOCKER_USERNAME" in content:
            assert re.search(
                r'^DOCKER_USERNAME=["\']?xuaustin["\']?', content, flags=re.MULTILINE
            ), "DOCKER_USERNAME variable must be defined as xuaustin"
        # The dated tag pattern: vYYYYMMDD-<sha>
        assert re.search(
            r"v\$\(date\s+\+%Y%m%d\)", content
        ), "must include a vYYYYMMDD date component in the tag"
        assert "git rev-parse --short HEAD" in content, (
            "tag must include the short git sha"
        )

    def test_two_repos_only(self):
        content = _read()
        # Find all <prefix>/<repo>: tag references where prefix is xuaustin or ${DOCKER_USERNAME}
        repos = set(
            re.findall(
                r"(?:xuaustin|\$\{DOCKER_USERNAME\}|\$DOCKER_USERNAME)/([\w-]+):",
                content,
            )
        )
        assert repos == {"python-agent-api", "python-agent-frontend"}, (
            f"expected exactly 2 repos, got {repos}"
        )

    def test_uses_dockerfile_explicit(self):
        """`-f Dockerfile.api` and `-f Dockerfile.frontend` must be passed."""
        content = _read()
        assert "Dockerfile.api" in content
        assert "Dockerfile.frontend" in content

    def test_syntax_valid_bash(self):
        """`bash -n script.sh` validates syntax without executing.

        On Windows, `bash` may route through WSL which can't read Windows paths.
        Skip in that case — Git Bash run directly validates the same script.
        """
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            text=True,
        )
        if "WSL" in result.stderr and "execvpe" in result.stderr:
            pytest.skip("bash routed via WSL on this host; cannot pass Windows path")
        assert result.returncode == 0, (
            f"bash syntax check failed: {result.stderr}"
        )
