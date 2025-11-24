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
