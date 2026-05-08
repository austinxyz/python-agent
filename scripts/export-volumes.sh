#!/usr/bin/env bash
# Export the three Windows-side python-agent docker volumes to tarballs in
# ./migration/. Designed for the one-time NAS migration described in
# openspec/changes/nas-deployment/design.md §3.
#
# Critical: tar uses `-C /src .` form so extraction at the target produces a
# FLAT layout (no nested <vol_name>/ subdir). Do not change this without
# re-running tests.
#
# Source volumes are mounted :ro so the export cannot write to live data.

set -e

VOLUMES=(qdrant_data sqlite_data uploads)
OUT_DIR="$(pwd)/migration"

mkdir -p "$OUT_DIR"

for V in "${VOLUMES[@]}"; do
  echo "==> exporting python-agent_${V} -> migration/${V}.tar.gz"
  docker run --rm \
    -v "python-agent_${V}:/src:ro" \
    -v "${OUT_DIR}:/dest" \
    alpine \
    tar czf "/dest/${V}.tar.gz" -C /src .
done

echo
echo "Done. Tarballs in ${OUT_DIR}/:"
ls -lh "${OUT_DIR}/"
