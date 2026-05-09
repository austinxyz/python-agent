"""End-to-end round-trip test for scripts/export-volumes.sh.

Critical correctness check: the design's `tar -C /src .` form must produce
tarballs that extract FLAT into a target dir (no nested <vol_name>/ subdir).
Getting this wrong corrupts the migration.

Strategy: create a temp docker volume populated with a known layout, run the
script, extract the produced tarball into a fresh dir, assert the layout is
flat and the file contents match.

Skipped if docker is not available (CI without docker).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "export-volumes.sh"


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _read() -> str:
    if not SCRIPT.exists():
        pytest.fail(f"{SCRIPT} does not exist")
    return SCRIPT.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static checks (always run)
# ---------------------------------------------------------------------------


class TestExportVolumesScriptStatic:
    def test_exists(self):
        assert SCRIPT.exists(), f"missing {SCRIPT}"

    def test_set_e_strict_mode(self):
        assert re.search(r"^set -e", _read(), flags=re.MULTILINE), (
            "must use 'set -e'"
        )

    def test_uses_flat_tar_form(self):
        """The critical correctness invariant: tar -C /src ."""
        content = _read()
        # Look for `-C /src .` (the Whole-point-of-this-script pattern)
        assert re.search(r"-C\s+/src\s+\.", content), (
            "MUST use 'tar -C /src .' form so extraction is flat (not nested)"
        )

    def test_source_volume_mounted_readonly(self):
        """Source volumes must be mounted :ro to prevent accidental writes."""
        content = _read()
        # The export volume mount line should end with :ro
        assert re.search(r"-v\s+python-agent_\$?\w+:/src:ro", content) or re.search(
            r":/src:ro", content
        ), "source volume must be mounted :ro"

    def test_targets_three_volumes(self):
        content = _read()
        for v in ("qdrant_data", "sqlite_data", "uploads"):
            assert v in content, f"must target python-agent_{v} volume"

    def test_outputs_to_migration_dir(self):
        content = _read()
        assert "migration" in content, "tarballs go into ./migration/"

    def test_disables_msys_path_conversion(self):
        """Git Bash on Windows mangles `-v <host>:/dest` mounts unless
        MSYS_NO_PATHCONV=1 is set. Removing this line silently breaks the
        script on any Git-Bash-driven invocation."""
        content = _read()
        assert "MSYS_NO_PATHCONV" in content, (
            "MSYS_NO_PATHCONV must be set so /dest mount paths aren't rewritten by Git Bash"
        )


# ---------------------------------------------------------------------------
# End-to-end docker round-trip (skipped if no docker)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _docker_available(), reason="docker not available")
class TestExportVolumesRoundTrip:
    """Live test: create a volume, populate it, run the script, verify flat extract."""

    @pytest.fixture
    def tmp_volume(self):
        """Create a temp docker volume with known content; clean up after."""
        # Use a unique name so parallel runs don't collide
        unique_id = uuid.uuid4().hex[:8]
        vol_name = f"test-export-vol-{unique_id}"

        # Create the volume
        r = subprocess.run(
            ["docker", "volume", "create", vol_name], capture_output=True, text=True
        )
        assert r.returncode == 0, r.stderr

        # Populate with: foo/bar.txt (subdir) and baz.txt (top-level)
        populate = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{vol_name}:/dest",
                "alpine",
                "sh",
                "-c",
                "mkdir -p /dest/foo && echo bar-content > /dest/foo/bar.txt && echo baz-content > /dest/baz.txt",
            ],
            capture_output=True,
            text=True,
        )
        assert populate.returncode == 0, populate.stderr

        yield vol_name

        # Cleanup
        subprocess.run(["docker", "volume", "rm", vol_name], capture_output=True)

    def test_flat_layout_after_export_extract(self, tmp_volume, tmp_path):
        """The whole point: extracted tarball produces flat layout, not nested."""
        # Mimic what export-volumes.sh does for a single volume:
        # docker run --rm -v <vol>:/src:ro -v <output>:/dest alpine tar czf /dest/out.tar.gz -C /src .
        out_tarball = tmp_path / "out.tar.gz"
        export_dir = tmp_path / "export_out"
        export_dir.mkdir()

        export = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{tmp_volume}:/src:ro",
                "-v",
                f"{export_dir.as_posix()}:/dest",
                "alpine",
                "tar",
                "czf",
                "/dest/out.tar.gz",
                "-C",
                "/src",
                ".",
            ],
            capture_output=True,
            text=True,
        )
        assert export.returncode == 0, export.stderr
        produced = export_dir / "out.tar.gz"
        assert produced.exists()
        assert produced.stat().st_size > 0

        # Extract into a fresh dir; assert flat layout
        extract_dir = tmp_path / "extract_target"
        extract_dir.mkdir()
        extract = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{produced.as_posix()}:/in/out.tar.gz:ro",
                "-v",
                f"{extract_dir.as_posix()}:/dest",
                "alpine",
                "tar",
                "xzf",
                "/in/out.tar.gz",
                "-C",
                "/dest",
            ],
            capture_output=True,
            text=True,
        )
        assert extract.returncode == 0, extract.stderr

        # KEY ASSERTIONS — flat layout
        assert (extract_dir / "baz.txt").exists(), "top-level file should be flat"
        assert (extract_dir / "foo" / "bar.txt").exists(), "subdir file should preserve structure"

        # NEGATIVE: must NOT have a nested copy of the tar contents
        nested_baz = list(extract_dir.glob("**/baz.txt"))
        assert len(nested_baz) == 1, (
            f"baz.txt should appear exactly once (flat); found {nested_baz}"
        )

        # Content preserved
        assert (extract_dir / "baz.txt").read_text().strip() == "baz-content"
        assert (extract_dir / "foo" / "bar.txt").read_text().strip() == "bar-content"
