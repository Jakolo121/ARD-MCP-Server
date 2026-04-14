# =============================================================================
# ARD MCP Server — Makefile
# =============================================================================
# Usage:
#   make test          — run unit tests (no network)
#   make test-all      — run ALL tests including live API calls
#   make lint          — run pylint (must stay 10.00/10)
#   make check         — lint + unit tests (CI gate)
#   make run           — start server in stdio mode (local/Claude Desktop)
#   make run-http      — start server in streamable_http mode (remote)
#   make docker-build  — build Docker image
#   make docker-run    — run server via Docker Compose
#   make docker-stop   — stop Docker Compose services
#   make clean         — remove build artefacts and caches
# =============================================================================

.PHONY: test test-all lint check run run-http docker-build docker-run docker-stop docker-logs docker-push k3s-apply k3s-delete k3s-status k3s-logs clean help

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------

test:
	uv run pytest tests/ -m "not integration" -q

test-all:
	uv run pytest tests/ -q

lint:
	uv run pylint src/ard_mcp/

check: lint test

run:
	uv run ard-mcp

run-http:
	MCP_TRANSPORT=streamable_http uv run ard-mcp

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

IMAGE_NAME  ?= ard-mcp
IMAGE_TAG   ?= latest
GHCR_IMAGE  ?= ghcr.io/jakolo121/ard-mcp

docker-build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-push:
	docker build -t $(GHCR_IMAGE):$(IMAGE_TAG) .
	docker push $(GHCR_IMAGE):$(IMAGE_TAG)

docker-run:
	docker compose up -d

docker-stop:
	docker compose down

docker-logs:
	docker compose logs -f ard-mcp

# ---------------------------------------------------------------------------
# k3s / Kubernetes
# ---------------------------------------------------------------------------

k3s-apply:
	kubectl apply -k k3s/

k3s-delete:
	kubectl delete -k k3s/

k3s-status:
	kubectl get pods,svc,ingress,hpa -n ard-mcp

k3s-logs:
	kubectl logs -n ard-mcp -l app=ard-mcp -f --max-log-requests 5

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage coverage.xml

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help:
	@echo ""
	@echo "ARD MCP Server — available targets:"
	@echo ""
	@echo "  test          Run unit tests (fast, no network)"
	@echo "  test-all      Run ALL tests including live API calls"
	@echo "  lint          Run pylint"
	@echo "  check         lint + test (CI gate)"
	@echo "  run           Start server in stdio mode"
	@echo "  run-http      Start server in streamable_http mode"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Start via Docker Compose"
	@echo "  docker-stop   Stop Docker Compose services"
	@echo "  docker-logs   Tail Docker Compose logs"
	@echo "  docker-push   Build and push image to ghcr.io"
	@echo "  k3s-apply     Apply all k8s manifests"
	@echo "  k3s-delete    Delete all k8s resources"
	@echo "  k3s-status    Show pods, services, ingress, HPA"
	@echo "  k3s-logs      Tail logs of all ard-mcp pods"
	@echo "  clean         Remove build artefacts and caches"
	@echo ""
