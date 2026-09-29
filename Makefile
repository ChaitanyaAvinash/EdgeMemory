# EdgeMemory make targets (CLAUDE.md). Works with GNU make on Windows (Git Bash) and Unix.
ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python
else
PY := .venv/bin/python
endif
ARM ?= C
SPLIT ?= dev
BACKEND ?= hindsight

.PHONY: setup seed reset test lint api web gate1 eval replay budget spike rehearse specs cases

setup:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check api scripts tests
	$(PY) -m ruff format --check api scripts tests

spike:
	$(PY) -m scripts.phase0_spike --part all

budget:
	$(PY) -m scripts.estimate_budget

gate1:
	$(PY) -m scripts.gate1

# Demo bank (SPEC §8.1, §18): the 37 seeds marked demo_bank=y; E1 and the E4 override happen live.
seed:
	$(PY) -c "import asyncio, api.main as m; print(asyncio.run(m.admin_seed()))"

api:
	$(PY) -m uvicorn api.main:app --port 8000

reset:
	$(PY) -c "import asyncio, api.main as m; print(asyncio.run(m.admin_reset()))"

eval:
	$(PY) -m eval.run_arms --arm $(ARM) --dataset bench --split $(SPLIT)

# SPEC §13 benchmark specs: check each builds its scenario against the master data (code only, no LLM).
specs:
	$(PY) -m scripts.check_specs

# Specs → messy narratives in data/cases/<split>/ (one Groq narrative call per case, cached; run make budget first).
cases:
	$(PY) -m scripts.generate_cases data/cases/specs.json

web:
	cd web && npm run dev

# Full SPEC §18 rehearsal through the running API (make api first): reset, seed, every beat.
rehearse:
	$(PY) -m scripts.rehearse

# Later phases (SPEC §17). Each fails loudly until its phase builds it.
replay:
	@echo "make $@: not built yet (see SPEC §17 for the phase that adds it)" && exit 1
