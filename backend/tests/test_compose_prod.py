"""Validates docker-compose.prod.yml shape per the nas-deployment spec.

This test runs `docker compose config` to ensure the file parses cleanly,
then asserts the shape: bind mounts to ./data/*, ports 891x, named
containers, no top-level volumes block, restart policy.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_COMPOSE = REPO_ROOT / "docker-compose.prod.yml"


def _load_prod_compose() -> dict:
    """Read the raw YAML — used for structure assertions docker compose config rewrites."""
    if not PROD_COMPOSE.exists():
        pytest.fail(f"{PROD_COMPOSE} does not exist")
    with PROD_COMPOSE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _docker_compose_config() -> dict:
    """Validate via docker — proves the file is parseable by compose itself."""
    result = subprocess.run(
        ["docker", "compose", "-f", str(PROD_COMPOSE), "config", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        pytest.fail(f"docker compose config failed:\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}")
    return json.loads(result.stdout)


class TestProdComposeShape:
    def test_file_exists(self):
        assert PROD_COMPOSE.exists(), f"missing {PROD_COMPOSE}"

    def test_compose_config_validates(self):
        # Raises pytest.fail if `docker compose config` rejects the file.
        _docker_compose_config()

    def test_three_services(self):
        cfg = _load_prod_compose()
        assert set(cfg["services"].keys()) == {"qdrant", "api", "frontend"}

    def test_container_names(self):
        cfg = _load_prod_compose()
        assert cfg["services"]["qdrant"]["container_name"] == "python-agent-qdrant"
        assert cfg["services"]["api"]["container_name"] == "python-agent-api"
        assert cfg["services"]["frontend"]["container_name"] == "python-agent-frontend"

    def test_restart_policy(self):
        cfg = _load_prod_compose()
        for svc in ("qdrant", "api", "frontend"):
            assert cfg["services"][svc]["restart"] == "unless-stopped", (
                f"{svc} must have restart: unless-stopped"
            )

    def test_uses_image_refs_not_build(self):
        cfg = _load_prod_compose()
        for svc in ("api", "frontend"):
            assert "image" in cfg["services"][svc], f"{svc} must use image:"
            assert "build" not in cfg["services"][svc], f"{svc} must NOT have build:"
        # qdrant always uses image
        assert cfg["services"]["qdrant"]["image"] == "qdrant/qdrant:v1.9.2"

    def test_image_repos(self):
        cfg = _load_prod_compose()
        assert cfg["services"]["api"]["image"].startswith("xuaustin/python-agent-api:")
        assert cfg["services"]["frontend"]["image"].startswith("xuaustin/python-agent-frontend:")

    def test_host_ports(self):
        cfg = _load_prod_compose()
        # nas-https: frontend is loopback-only so tailscale serve reaches localhost:8910
        # but the LAN cannot. api remains LAN-accessible (intentional for admin tools).
        assert "127.0.0.1:8910:3000" in cfg["services"]["frontend"]["ports"]
        assert "8911:5000" in cfg["services"]["api"]["ports"]

    def test_qdrant_not_exposed_on_host(self):
        """SECURITY: qdrant 1.9 has no auth; do not bind it to the host network.
        The api communicates over the docker internal network."""
        cfg = _load_prod_compose()
        qdrant_ports = cfg["services"]["qdrant"].get("ports", [])
        assert not qdrant_ports, (
            "qdrant must not bind any host port — v1.9 has no auth, would expose "
            "the entire vector store to the LAN. Use `docker exec` for ad-hoc debug."
        )

    def test_bind_mounts_to_data_subdirs(self):
        cfg = _load_prod_compose()
        # api: ./data/sqlite -> /app/data, ./data/uploads -> /app/uploads
        api_volumes = cfg["services"]["api"]["volumes"]
        assert "./data/sqlite:/app/data" in api_volumes
        assert "./data/uploads:/app/uploads" in api_volumes
        # qdrant: ./data/qdrant -> /qdrant/storage
        qdrant_volumes = cfg["services"]["qdrant"]["volumes"]
        assert "./data/qdrant:/qdrant/storage" in qdrant_volumes

    def test_tailscale_certs_readonly_mount_in_api(self):
        """nas-https: api needs read-only access to Tailscale certs to serve cert-status.
        Without this, GET /api/admin/cert-status returns the offline fallback on the NAS."""
        cfg = _load_prod_compose()
        api_volumes = cfg["services"]["api"]["volumes"]
        assert "/volume1/docker/tailscale/certs:/tailscale/certs:ro" in api_volumes

    def test_no_top_level_volumes_block(self):
        cfg = _load_prod_compose()
        # Bind mounts don't need a top-level volumes: declaration. Having one
        # would imply named volumes, which contradicts the design.
        assert "volumes" not in cfg or not cfg.get("volumes"), (
            "Prod compose must not declare a top-level volumes block; bind mounts only"
        )

    def test_api_depends_on_qdrant_healthy(self):
        cfg = _load_prod_compose()
        depends = cfg["services"]["api"]["depends_on"]
        # depends_on can be a list or dict; we want dict form for healthcheck condition
        assert isinstance(depends, dict), "api depends_on must use dict form for service_healthy"
        assert depends["qdrant"]["condition"] == "service_healthy"

    def test_qdrant_has_healthcheck(self):
        cfg = _load_prod_compose()
        assert "healthcheck" in cfg["services"]["qdrant"]

    def test_api_has_env_file(self):
        cfg = _load_prod_compose()
        env_file = cfg["services"]["api"].get("env_file")
        # accepts string ".env" or list [".env"]
        if isinstance(env_file, str):
            assert env_file == ".env"
        else:
            assert ".env" in env_file
