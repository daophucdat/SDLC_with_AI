# One-command entry points (Day 5 DoD: "chạy được bằng 1 lệnh"). CI runs the same commands (.github/workflows/ci.yml).
# Windows without make: run the commands of a target by hand (Git Bash), e.g. `docker compose -f infra/docker-compose.yml up --build -d`.

COMPOSE := docker compose -f infra/docker-compose.yml
ifeq ($(OS),Windows_NT)
  PY := backend/.venv/Scripts/python
  BIN := .venv/Scripts
else
  PY := backend/.venv/bin/python
  BIN := .venv/bin
endif

.PHONY: up down logs install lint typecheck test coverage check traceability mutation sbom

up:            ## start the whole stack: http://localhost:5173 (thu.ha / Test@1234)
	$(COMPOSE) up --build -d
	@echo "→ http://localhost:5173  (first start downloads the embedding model, ~2 GB)"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api worker

install:       ## backend venv + web node_modules
	cd backend && python -m venv .venv && $(BIN)/python -m pip install -e ".[dev,otel]"
	cd web && npm ci

lint:          ## format, lint, complexity ≤ 10, import rules
	cd backend && $(BIN)/ruff check . && $(BIN)/black --check . && $(BIN)/lint-imports
	cd web && npm run lint

typecheck:
	cd web && npm run typecheck

test:          ## unit + API tests (integration tests need TEST_DATABASE_URL)
	cd backend && $(BIN)/python -m pytest -q
	cd web && npm test

coverage:      ## coverage gates: ≥ 70 % overall, ≥ 90 % core backend modules
	cd backend && $(BIN)/python -m pytest -q --cov --cov-report=term
	cd backend && $(BIN)/python -m coverage report --fail-under=90 \
	  --include="chatdocs/domain/*,chatdocs/application/qa_service.py,chatdocs/application/retrieval_service.py"
	cd web && npm run test:coverage

traceability:  ## commits since main carry US/EN/REL/BR codes; matrix points at real code and tests
	$(PY) -m pytest -q scripts eval
	$(PY) scripts/check_traceability.py matrix
	$(PY) scripts/check_traceability.py commits origin/main..HEAD

check: lint typecheck coverage traceability   ## every L0 gate that runs locally (CI adds audits, Trivy, gitleaks, E2E)

mutation:      ## mutation score of the core modules (slow; CI runs it weekly)
	cd backend && $(BIN)/mutmut run; $(BIN)/mutmut junitxml > mutmut.xml; $(BIN)/python ../scripts/mutation_score.py mutmut.xml 60

sbom:
	mkdir -p sbom && cd backend && $(BIN)/cyclonedx-py environment --output-format JSON -o ../sbom/backend.cdx.json
	cd web && npm sbom --sbom-format cyclonedx --omit dev > ../sbom/web.cdx.json
