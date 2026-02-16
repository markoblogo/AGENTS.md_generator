.PHONY: install test lint format snapshot agents pack pack-check release

install:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install -U pip
	. .venv/bin/activate && python -m pip install -e ".[dev]"

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && ruff check .

format:
	. .venv/bin/activate && ruff format .

snapshot:
	. .venv/bin/activate && python scripts/snapshot.py

agents:
	. .venv/bin/activate && agentsgen update --autodetect

pack:
	. .venv/bin/activate && agentsgen pack --autodetect

pack-check:
	. .venv/bin/activate && agentsgen pack --autodetect --check

release:
	@echo "Usage: ./scripts/release.sh vX.Y.Z A|B|C"
