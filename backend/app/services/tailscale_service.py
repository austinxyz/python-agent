"""Tailscale service — cert metadata + daemon status.

get_cert_status(hostname) returns a 5-field dict.
On any failure (CLI missing, cert absent, parse error) returns the
offline sentinel — never raises.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_NULL_CERT = {
    "cert_expiry_iso": None,
    "days_remaining": None,
    "last_renew_iso": None,
}


def get_cert_status(hostname: str) -> dict:
    """Return 5-field dict. Never raises."""
    # --- daemon status (best-effort; CLI may not be present in the api container) ---
    ts_status = "offline"
    cli_available = False
    try:
        proc = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        data = json.loads(proc.stdout)
        ts_status = "online" if data.get("BackendState") == "Running" else "degraded"
        cli_available = True
    except Exception as exc:
        logger.debug("tailscale status failed: %s", exc)
        # Don't return early — still attempt cert read below.

    # --- cert metadata ---
    cert_dir = os.environ.get("TAILSCALE_CERTS_PATH", "/var/lib/tailscale/certs")
    cert_path = Path(cert_dir) / f"{hostname}.crt"

    try:
        from cryptography import x509

        cert_data = cert_path.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        expiry = cert.not_valid_after_utc
        last_renew = datetime.fromtimestamp(cert_path.stat().st_mtime, tz=timezone.utc)
        # Negative when cert is already expired — intentional, frontend handles it.
        days_remaining = (expiry - datetime.now(timezone.utc)).days

        # When the CLI is unavailable (e.g. NAS api container), infer online from
        # a valid cert: Tailscale must be running to provision and auto-renew it.
        if not cli_available and days_remaining > 0:
            ts_status = "online"

        return {
            "hostname": hostname,
            "cert_expiry_iso": expiry.isoformat(),
            "days_remaining": days_remaining,
            "tailscale_status": ts_status,
            "last_renew_iso": last_renew.isoformat(),
        }
    except Exception as exc:
        logger.debug("cert read/parse failed for %s: %s", cert_path, exc)
        return {"hostname": hostname, "tailscale_status": ts_status, **_NULL_CERT}
