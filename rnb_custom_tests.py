"""Run & Bun focused smoke tests for the pokemon-python simulator.

These tests live at the repo root (next to runandbun.lua) so they can be
executed even if the legacy unittest package inside pokemon-python/test is
broken. They focus on two guarantees:

1. The Run & Bun specific data we recently ported (species, abilities, items)
   exists in the dex layer and is fully hydrated.
2. The simulator can run a deterministic single battle that features some of
   those species without crashing.

Usage:
    python rnb_custom_tests.py
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple
from unittest import mock
ROOT = Path(__file__).resolve().parent
SIM_ROOT = ROOT / "pokemon-python"

if not SIM_ROOT.exists():
    raise SystemExit(f"pokemon-python directory not found at {SIM_ROOT}")

# data.dex uses relative paths when loading JSON. Import it from inside the
# pokemon-python directory so those paths resolve, then restore the cwd.
def _bootstrap_sim() -> tuple:
    prev_cwd = os.getcwd()
    os.chdir(SIM_ROOT)
    try:
        from data import dex  # type: ignore
        import sim.sim as sim  # type: ignore
        from sim.structs import PokemonSet  # type: ignore
        from sim.turn import accuracy_check, calc_damage, create_move  # type: ignore
    finally:
        os.chdir(prev_cwd)
    return dex, sim, PokemonSet, accuracy_check, create_move, calc_damage


dex, sim, PokemonSet, accuracy_check, create_move, calc_damage = _bootstrap_sim()

RUN_AND_BUN_SPECIES = (
    "alcremie",
    "applin",
    "appletun",
    "arcaninehisui",
    "arctovish",
    "arctozolt",
    "arrokuda",
    "articunogalar",
    "avalugghisui",
    "barraskewda",
    "basculinwhitestriped",
    "basculegion",
)

RUN_AND_BUN_ABILITIES = (
    "asone",
    "chillingneigh",
    "cottondown",
    "gorillatactics",
    "gulpmissile",
    "hungerswitch",
    "iceface",
    "icescales",
    "libero",
    "neutralizinggas",
    "pastelveil",
    "perishbody",
    "powerspot",
    "punkrock",
    "quickdraw",
    "ripen",
    "sandspit",
    "screencleaner",
    "steamengine",
    "steelyspirit",
    "unseenfist",
    "wanderingspirit",
)

RUN_AND_BUN_ITEMS = (
    "blunderpolicy",
    "ejectpack",
    "leek",
    "roomservice",
    "throatspray",
)


DEFAULT_IVS: Tuple[int, int, int, int, int, int] = (31, 31, 31, 31, 31, 31)


def _build_mon(
    species: str,
    *,
    ability: str,
    moves: Iterable[str],
    item: str = "leftovers",
    nature: str = "modest",
    ivs: Sequence[int] | None = None,
) -> Any:
    iv_values: Tuple[int, int, int, int, int, int]
    if ivs is None:
        iv_values = DEFAULT_IVS
    else:
        iv_list = list(ivs)
        if len(iv_list) != 6:
            raise ValueError("IVs must contain exactly six values")
        iv_values = tuple(int(v) for v in iv_list)  # type: ignore[arg-type]
    return PokemonSet(
        name=species,
        species=species,
        item=item,
        ability=ability,
        moves=list(moves),
        nature=nature,
        ivs=iv_values,
    )


class RunAndBunDataTests(unittest.TestCase):
    def test_species_entries_present(self) -> None:
        missing = [name for name in RUN_AND_BUN_SPECIES if name not in dex.pokedex]
        self.assertFalse(missing, f"Missing species entries: {missing}")

    def test_ability_entries_present(self) -> None:
        missing = [name for name in RUN_AND_BUN_ABILITIES if name not in dex.ability_dex]
        self.assertFalse(missing, f"Missing ability entries: {missing}")

    def test_item_entries_present(self) -> None:
        missing = [name for name in RUN_AND_BUN_ITEMS if name not in dex.item_dex]
        self.assertFalse(missing, f"Missing item entries: {missing}")

    def test_species_have_base_stats(self) -> None:
        empty_stats = [name for name in RUN_AND_BUN_SPECIES if not dex.pokedex[name].baseStats]
        self.assertFalse(empty_stats, f"Species missing base stats: {empty_stats}")


class RunAndBunBattleSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.team_one = [
            _build_mon(
                "alcremie",
                ability="sweetveil",
                item="leftovers",
                moves=("dazzlinggleam", "mysticalfire", "recover", "protect"),
                nature="bold",
            ),
            _build_mon(
                "appletun",
                ability="ripen",
                item="sitrusberry",
                moves=("dragonpulse", "gigadrain", "recover", "protect"),
                nature="quiet",
            ),
        ]
        self.team_two = [
            _build_mon(
                "barraskewda",
                ability="swiftswim",
                item="lifeorb",
                moves=("liquidation", "closecombat", "aquajet", "protect"),
                nature="jolly",
            ),
            _build_mon(
                "arcaninehisui",
                ability="intimidate",
                item="choiceband",
                moves=("flareblitz", "extremespeed", "rockslide", "protect"),
                nature="adamant",
            ),
        ]

    def test_single_turn_executes(self) -> None:
        battle = sim.Battle("single", "Run", self.team_one, "Bun", self.team_two, debug=False)
        sim.choose(battle, 1, "move 0")
        sim.choose(battle, 2, "move 0")
        sim.do_turn(battle)
        self.assertGreaterEqual(battle.turn, 1)
        self.assertFalse(battle.ended)

    def test_run_finishes_battle(self) -> None:
        battle = sim.Battle("single", "Run", self.team_one, "Bun", self.team_two, debug=False)
        sim.run(battle)
        self.assertTrue(battle.ended)
        self.assertIn(battle.winner, {"p1", "p2"})


class RunAndBunMechanicTests(unittest.TestCase):
    def test_drought_sets_permanent_sun(self) -> None:
        sunny_team = [
            _build_mon(
                "torkoal",
                ability="drought",
                item="heatrock",
                moves=("overheat", "yawn", "protect", "bodyslam"),
            )
        ]
        foe_team = [
            _build_mon(
                "pelipper",
                ability="keeneye",
                item="leftovers",
                moves=("scald", "protect", "roost", "hurricane"),
            )
        ]
        battle = sim.Battle("single", "Sun", sunny_team, "Rain", foe_team, debug=False)
        self.assertEqual(battle.weather, "sunlight")
        self.assertTrue(battle.weather_permanent)
        self.assertIsNone(battle.weather_n)
        sim.choose(battle, 1, "move 0")
        sim.choose(battle, 2, "move 0")
        sim.do_turn(battle)
        self.assertEqual(battle.weather, "sunlight")
        self.assertTrue(battle.weather_permanent)

    def test_grassy_surge_and_disguise(self) -> None:
        surge_team = [
            _build_mon(
                "tapubulu",
                ability="grassysurge",
                item="assaultvest",
                moves=("woodhammer", "stoneedge", "megahorn", "protect"),
            )
        ]
        disguise_team = [
            _build_mon(
                "mimikyu",
                ability="disguise",
                item="leftovers",
                moves=("splash", "shadowclaw", "playrough", "woodhammer"),
            )
        ]
        battle = sim.Battle("single", "Surge", surge_team, "Mask", disguise_team, debug=False)
        self.assertEqual(battle.terrain, "grassyterrain")
        self.assertTrue(battle.terrain_permanent)
        defender = battle.p2.active_pokemon[0]
        sim.choose(battle, 1, "move 0")
        sim.choose(battle, 2, "move 0")
        sim.do_turn(battle)
        self.assertEqual(defender.hp, defender.maxhp)
        self.assertTrue(defender.disguise_broken)
        sim.choose(battle, 1, "move 0")
        sim.choose(battle, 2, "move 1")
        sim.do_turn(battle)
        self.assertLess(defender.hp, defender.maxhp)


class RunAndBunMoveBehaviorTests(unittest.TestCase):
    def test_hidden_power_uses_pokemon_ivs(self) -> None:
        ivs = (31, 31, 31, 31, 31, 31)
        hp_user = _build_mon(
            "alakazam",
            ability="synchronize",
            moves=("hiddenpower", "recover"),
            nature="timid",
            ivs=ivs,
        )
        dummy_target = _build_mon(
            "chansey",
            ability="naturalcure",
            moves=("softboiled", "seismictoss"),
            nature="bold",
        )
        battle = sim.Battle("single", "HP", [hp_user], "Dummy", [dummy_target], debug=False)
        user = battle.p1.active_pokemon[0]
        decision = dex.Decision("move", 0)
        move = create_move(battle, user, decision)
        self.assertEqual(move.type, "Dark")
        self.assertEqual(move.base_power, 60)

    def test_electric_thunder_wave_never_misses(self) -> None:
        electric_user = _build_mon(
            "raichu",
            ability="static",
            moves=("thunderwave", "nuzzle"),
            nature="timid",
        )
        evasive_target = _build_mon(
            "garchomp",
            ability="roughskin",
            moves=("swordsdance", "earthquake"),
            nature="jolly",
        )
        battle = sim.Battle("single", "Spark", [electric_user], "Ground", [evasive_target], debug=False)
        user = battle.p1.active_pokemon[0]
        target = battle.p2.active_pokemon[0]
        user.boosts["accuracy"] = -6
        target.boosts["evasion"] = 6
        move = create_move(battle, user, dex.Decision("move", 0))
        with mock.patch("sim.turn.random.randint", return_value=99):
            self.assertTrue(accuracy_check(battle, user, move, target))
        original_types = list(user.types)
        user.types = [t for t in user.types if t != "Electric"]
        if not user.types:
            user.types = ["Normal"]
        with mock.patch("sim.turn.random.randint", return_value=99):
            self.assertFalse(accuracy_check(battle, user, move, target))
        user.types = original_types

    def test_explosion_style_moves_halve_defense(self) -> None:
        attacker = _build_mon(
            "snorlax",
            ability="immunity",
            moves=("selfdestruct", "bodyslam"),
            nature="brave",
        )
        defender = _build_mon(
            "blissey",
            ability="naturalcure",
            moves=("softboiled", "protect"),
            nature="bold",
        )
        battle = sim.Battle("single", "Boom", [attacker], "Wall", [defender], debug=False)
        battle.rng = False
        user = battle.p1.active_pokemon[0]
        target = battle.p2.active_pokemon[0]
        move = create_move(battle, user, dex.Decision("move", 0))
        with mock.patch.object(dex, "RUNANDBUN_DEF_HALVING_MOVES", set()):
            baseline = calc_damage(battle, user, move, target)
        boosted = calc_damage(battle, user, move, target)
        self.assertGreater(boosted, baseline)
        self.assertGreaterEqual(boosted * 100, baseline * 195)


def main() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
