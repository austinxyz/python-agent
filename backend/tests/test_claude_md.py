"""Asserts CLAUDE.md gains a Deployment section + new pitfall entry."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def _read() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


class TestClaudeMdDeploymentSection:
    def test_deployment_section_exists(self):
        assert "## Deployment" in _read(), (
            "CLAUDE.md must gain a '## Deployment' section"
        )

    def test_deployment_mentions_build_push(self):
        # Find the Deployment section content
        content = _read()
        deploy_start = content.index("## Deployment")
        # Take the section until the next ## or end
        rest = content[deploy_start:]
        next_section = rest.find("\n## ", 1)
        section = rest[:next_section] if next_section > 0 else rest
        assert "build-and-push.sh" in section, (
            "Deployment section must reference scripts/build-and-push.sh"
        )

    def test_deployment_mentions_ui_workflow(self):
        content = _read()
        rest = content[content.index("## Deployment"):]
        # Should mention UI Pull / Restart pattern
        assert "Pull" in rest, "must mention the NAS UI 'Pull' action"
        assert "Restart" in rest or "Apply" in rest, (
            "must mention the NAS UI 'Restart' or 'Apply' action"
        )

    def test_deployment_mentions_dev_up(self):
        content = _read()
        rest = content[content.index("## Deployment"):]
        assert "dev:up" in rest or "npm run dev" in rest, (
            "must reference the local dev shortcut"
        )

    def test_deployment_mentions_rollback_tag_format(self):
        content = _read()
        rest = content[content.index("## Deployment"):]
        # Must mention how to roll back (vYYYYMMDD-<sha> tag pattern)
        assert "vYYYYMMDD" in rest or "v$(date" in rest or "rollback" in rest.lower(), (
            "must document the rollback path (pin a versioned tag)"
        )

    def test_known_pitfalls_mentions_tar_flat_layout(self):
        content = _read()
        # Find the Known Pitfalls section
        assert "## Known Pitfalls" in content
        rest = content[content.index("## Known Pitfalls"):]
        # New pitfall entry mentioning the flat-layout tar requirement
        assert "tar -C" in rest or "flat layout" in rest or "tar `-C" in rest, (
            "Known Pitfalls must gain an entry covering the tar -C /src . flat-layout requirement"
        )


class TestClaudeMdAdminUiUserManagement:
    def test_admin_ui_is_primary_path(self):
        content = _read()
        assert "/admin/users" in content, (
            "CLAUDE.md must reference /admin/users as the user management UI"
        )
        lower = content.lower()
        assert "primary" in lower or "web ui" in lower or "web interface" in lower, (
            "CLAUDE.md must position the web UI as the primary path for user management"
        )

    def test_cli_is_emergency_fallback(self):
        content = _read()
        assert "app.cli.invite_user" in content, (
            "CLAUDE.md must retain the CLI reference for emergency use"
        )
        lower = content.lower()
        assert (
            "fallback" in lower
            or "emergency" in lower
            or "emergenc" in lower
        ), (
            "CLAUDE.md must position the CLI as emergency fallback, not primary path"
        )
