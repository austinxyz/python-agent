#!/usr/bin/env bash
# Build and push python-agent images to Docker Hub.
# Single-arch (linux/amd64) — UGREEN NAS is amd64; multi-arch is out of scope.
# Each push tags both :latest and :vYYYYMMDD-<short-sha>.
#
# Prerequisites: `docker login` once before running.
# See openspec/changes/nas-deployment/design.md §2 for rationale.

set -e

DOCKER_USERNAME="xuaustin"
TAG="v$(date +%Y%m%d)-$(git rev-parse --short HEAD)"

echo "Building python-agent images for linux/amd64"
echo "Tag: ${TAG} (and :latest)"
echo

# Ensure buildx multiarch builder exists, then use it.
if ! docker buildx ls | grep -q multiarch; then
  echo "Creating buildx 'multiarch' builder..."
  docker buildx create --name multiarch --use
fi
docker buildx use multiarch

# api image
echo "==> Building xuaustin/python-agent-api"
docker buildx build \
  --platform linux/amd64 \
  -t "${DOCKER_USERNAME}/python-agent-api:latest" \
  -t "${DOCKER_USERNAME}/python-agent-api:${TAG}" \
  -f Dockerfile.api \
  --push \
  .

# frontend image
echo "==> Building xuaustin/python-agent-frontend"
docker buildx build \
  --platform linux/amd64 \
  -t "${DOCKER_USERNAME}/python-agent-frontend:latest" \
  -t "${DOCKER_USERNAME}/python-agent-frontend:${TAG}" \
  -f Dockerfile.frontend \
  --push \
  .

echo
echo "Pushed both images with tag ${TAG}"
