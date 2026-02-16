# Project Status Snapshot

Date: 2026-02-16
Scope: freeze note (no code changes)

## Current state

- Landing (`docs/index.html`) is live and updated on `agentsmd.abvx.xyz`.
- Hero/header/sticker layout is stabilized for desktop + mobile.
- Theme toggle (light/dark) is working.
- README screenshot is updated to:
  - `docs/assets/agentsmd-landing-v0.1.2.png`
- GitHub Action guard supports pack drift checks (`pack_check`, `pack_format`).
- Release assets and docs are aligned to `v0.1.2`.

## CI / checks status baseline

- Local baseline checks pass in this repo:
  - `ruff format --check .`
  - `ruff check .`
  - `pytest -q`
  - `python -m agentsgen._smoke`

## External repo trial run (safe mode)

- Dry-run scan completed for:
  - `markoblogo/-abvx-shortener`
  - `markoblogo/toki-pona-translator`
- Result: both repos need bootstrap (`agentsgen init`) and pack generation (`agentsgen pack`).
- No files were written (dry-run/check only).

## Notes

- This snapshot is informational and intended as a freeze point.
