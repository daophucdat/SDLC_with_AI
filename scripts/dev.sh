#!/usr/bin/env bash
# Same targets as the Makefile, for machines without `make` (Windows + Git Bash):  bash scripts/dev.sh <target>
#   up | down | logs | install | lint | typecheck | test | coverage | traceability | check | sbom
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
if [ -d backend/.venv/Scripts ]; then BIN="$ROOT/backend/.venv/Scripts"; else BIN="$ROOT/backend/.venv/bin"; fi
PY="$BIN/python"
COMPOSE="docker compose -f infra/docker-compose.yml"
CORE="chatdocs/domain/*,chatdocs/application/qa_service.py,chatdocs/application/retrieval_service.py"

target="${1:-help}"
case "$target" in
  up)        $COMPOSE up --build -d && echo "→ http://localhost:5173  (thu.ha / Test@1234)" ;;
  down)      $COMPOSE down ;;
  logs)      $COMPOSE logs -f api worker ;;
  install)   (cd backend && python -m venv .venv && "$PY" -m pip install -e ".[dev,otel]") && (cd web && npm ci) \
               && git config core.hooksPath .githooks ;;
  lint)      (cd backend && "$BIN/ruff" check . && "$BIN/black" --check . && "$BIN/lint-imports") && (cd web && npm run lint) ;;
  typecheck) (cd web && npm run typecheck) ;;
  test)      (cd backend && "$PY" -m pytest -q) && (cd web && npm test) ;;
  coverage)
    (cd backend && "$PY" -m pytest -q --cov --cov-report=term && "$PY" -m coverage report --fail-under=90 --include="$CORE")
    (cd web && npm run test:coverage) ;;
  traceability)
    "$PY" -m pytest -q -p no:cacheprovider scripts eval
    "$PY" scripts/check_traceability.py matrix
    "$PY" scripts/check_skills.py
    "$PY" scripts/check_traceability.py commits "${RANGE:-origin/main..HEAD}" ;;
  check)     for t in lint typecheck coverage traceability; do echo "== $t"; bash "$0" "$t"; done; echo "== all local L0 gates passed" ;;
  sbom)      mkdir -p sbom && (cd backend && "$BIN/cyclonedx-py" environment --output-format JSON -o ../sbom/backend.cdx.json) \
               && (cd web && npm sbom --sbom-format cyclonedx --omit dev > ../sbom/web.cdx.json) ;;
  *)         sed -n '2,3p' "$0"; exit 2 ;;
esac
