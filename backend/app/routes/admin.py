"""Admin routes — require admin role.

GET /api/admin/cert-status  — Tailscale + TLS cert health summary.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

from flask import Blueprint, jsonify

from ..middleware import require_admin
from ..services import tailscale_service

admin_bp = Blueprint("admin", __name__)


def _tailscale_hostname() -> str:
    """Derive FQDN from APP_BASE_URL (set to https://... after nas-https deploy).

    Pre-HTTPS-deploy: APP_BASE_URL is http://, so hostname falls back to
    TAILSCALE_HOSTNAME env var.  If neither is set, returns "unknown" — the
    service call will attempt to read "unknown.crt", fail silently, and return
    tailscale_status=online with cert fields null.  This is the expected state
    before Group 4 deploys the HTTPS config.
    """
    base_url = os.environ.get("APP_BASE_URL", "")
    if base_url.startswith("https://"):
        host = urlparse(base_url).hostname
        if host:
            return host
    return os.environ.get("TAILSCALE_HOSTNAME", "unknown")


@admin_bp.get("/cert-status")
@require_admin
def cert_status():
    return jsonify(tailscale_service.get_cert_status(_tailscale_hostname()))
