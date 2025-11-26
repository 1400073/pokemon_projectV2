# Run & Bun custom tests

`rnb_custom_tests.py` lives at the repo root next to the Run & Bun reference
files (for example `runandbun.lua`). It intentionally sits outside the legacy
`pokemon-python/test` suite so we can validate new Run & Bun specific data even
when the historical tests fail to import `sim.battle`.

## What the harness covers

- **Data sanity** – ensures every Run & Bun species, ability, and item we added
  to the dex exists and has base stats/descriptions wired up.
- **Simulation smoke test** – spins up a single battle that features the newly
  added species (Alcremie/Appletun vs. Barraskewda/Arcanine-Hisui) and verifies
  we can play at least one turn as well as auto-resolve the whole match without
  crashing.
- **Mechanic checks** – verifies permanent weather/terrain setters stay active,
  terrain boosts apply, and Disguise negates the first damaging hit before
  breaking.

## How to run

```powershell
python rnb_custom_tests.py
```

The script automatically updates `sys.path`, imports the simulator, and restores
`cwd`, so it can be launched from the repo root without extra environment
variables.

## Next steps

As we implement more Run & Bun mechanics, add targeted asserts to the same file
(or split out additional suites) so we keep deterministic coverage for every new
feature.

## AI vs. AI harness

When you want to pit two trainers from `trainer_data.json` against each other
using the Run & Bun AI policy, use `run_ai_vs_ai.py`. It shares the same
bootstrap requirements as `rnb_custom_tests.py`, so make sure a sibling
`pokemon-python/` checkout exists before launching battles.

Example usage (don’t run until the simulator is available):

```powershell
python run_ai_vs_ai.py `
  --trainer-a "Youngster Calvin@Brawly Split@single" `
  --trainer-b "Bug Catcher Rick@Brawly Split@single" `
  --battle-count 50
```

You can supply `--match "Trainer One|Trainer Two"` multiple times to queue a
gauntlet and `--seed 1337` for reproducibility. The script surfaces clear error
messages if it can’t locate the simulator state helpers so you know to clone
`pokemon-python/` first.
