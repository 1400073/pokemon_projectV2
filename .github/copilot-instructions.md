## Quick context

This repository mixes a fast Python battle engine (primary work) with a few JS/TS/Lua artifacts. The canonical simulator lives in the `pokemon-python/` package. The AI scoring policy for Run & Bun lives in `ai_policy.py` at the repo root and is tuned to the project's Run & Bun documents.

Keep changes scoped to one language at a time. Most active development and tests are inside `pokemon-python/`.

## Architecture (big picture)

- `pokemon-python/` — the battle engine and data. Key pieces:
  - `pokemon-python/sim/` and `pokemon-python/sim/*.py` — simulation engine entry points (e.g. `sim.sim`, `sim.turn`). Use `new_battle`, `do_turn`, and `run` to drive sims.
  - `pokemon-python/data/` — JSON-backed canonical game data (moves.json, pokedex.json, abilities.json, etc.). `pokemon-python/data/dex.py` wraps these as namedtuples/lookup structures (Decision, Action, Move, Pokemon).
  - `pokemon-python/test/` — unit tests that validate simulator behaviour (uses Python's unittest).

- Root-level files like `moves.ts`, `species.ts`, `gen8.js`, and `runandbun.lua` are reference ports or tooling artifacts. Before editing them, confirm whether you should update the Python engine or the external artifact (they are separate targets).

## Developer workflows

- Run unit tests (discovery from repo root):

```powershell
python -m unittest discover -s "pokemon-python/test"
```

- Run a single test file:

```powershell
python -m unittest "pokemon-python/test/test_crit.py"
```

- Quick local simulation (via API): import the simulator from the `pokemon-python` package and call `sim.new_battle(...)`, `sim.choose(...)`, `sim.do_turn()` or `sim.run()` as shown in `pokemon-python/README.md`.

## Project-specific conventions & patterns

- Data-first model: canonical game state (moves, pokedex, items, formats) is stored as JSON under `pokemon-python/data/` and loaded early by `data/dex.py`. When adding fields, update both the JSON and the corresponding namedtuple mappings in `dex.py`.

- Decision API: decisions are represented by `Decision` namedtuple (see `data/dex.py`) and `Action` objects. Use these when creating or testing player inputs.

- Determinism for tests: many simulation functions accept `debug` and `rng` flags (see `sim/sim.py` and tests). For deterministic test runs, pass `rng=False` or seed RNG where available.

- AI policy: `ai_policy.py` encodes a deterministic-ish scoring policy used by higher-level AIs. It is heavy on heuristics and random tie-breaking; if you change scoring, add targeted tests in `pokemon-python/test/` that assert outcomes or deterministic seeds.

## Integration points and cross-component notes

- JSON data files are the single source of truth for game data. Changes must stay backward-compatible for existing tests unless tests are intentionally updated.

- The Python engine exposes a small API surface for driving battles (see `pokemon-python/sim/sim.py`). External tools (JS/TS/Lua) are NOT wired into the Python package automatically—treat them as separate.

- Tests import simulator modules using package-style imports (e.g. `from sim.battle import Battle`) — prefer running tests via discovery from the repo root so imports resolve.

## Useful file references (examples to open)

- `ai_policy.py` — Run & Bun tuned AI scoring rules (use for AI changes / reference of expected behaviour).
- `pokemon-python/README.md` — quick usage examples for the Python simulator (`new_battle`, `choose`, `do_turn`, `run`).
- `pokemon-python/data/dex.py` — how JSON becomes runtime objects and Decision/Action namedtuples.
- `pokemon-python/sim/sim.py` — public helper wrappers (`new_battle`, `choose`, `run`, `do_turn`).
- `pokemon-python/test/` — tests showing expected behaviour (run them after edits).

## Short checklist for edits

1. If change touches gameplay or data: update JSON under `pokemon-python/data/` and `dex.py` mappings as needed.
2. Add/modify unit tests under `pokemon-python/test/` using `unittest` and validate with discovery.
3. For AI changes: update `ai_policy.py` and add a deterministic test (set `rng=False` where used).
4. When modifying JS/TS/Lua files, confirm which project/component consumes them; do not assume the Python sim will pick up those edits.

## When unsure — quick questions to ask in a PR

- Is this change intended to affect the Python simulator or an external tool (TS/JS/Lua)?
- Does the JSON schema in `pokemon-python/data/` need bumping? If so, include a small migration example in the PR.
- Does the change require deterministic tests? If yes, add a test and use `rng=False` or seed the RNG.

---

If you'd like, I can refine any section (for example add explicit test commands, note CI expectations, or extract frequently changed JSON keys). What should I expand or clarify?
