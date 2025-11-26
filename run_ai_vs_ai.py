#!/usr/bin/env python3
"""Run Run & Bun AI vs AI battles with the pokemon-python simulator.

This helper wires the documented heuristic policy in ``ai_policy.py`` into the
fast ``pokemon-python`` simulator so we can pit any pair of trainers defined in
``trainer_data.json`` against one another.  It intentionally mirrors the
``rnb_custom_tests`` bootstrap logic so that relative imports inside the
simulator continue to work even when this script is executed from the Run & Bun
repository root.

The script does *not* execute automatically when imported.  Run it manually once
``pokemon-python`` has been cloned beside this repository:

    python run_ai_vs_ai.py --trainer-a "Youngster Calvin@Brawly Split@single" \
                           --trainer-b "Bug Catcher Rick@Brawly Split@single" \
                           --battle-count 50

It also accepts multiple ``--match "trainerA|trainerB"`` pairs so you can queue
up a gauntlet and lets you seed the underlying PRNG for determinism.  Because
the user currently can't execute the simulator in this environment, the script
focuses on data plumbing and documentation; no battles are run as part of this
commit.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
SIM_ROOT = ROOT / "pokemon-python"
TRAINER_DATA_PATH = ROOT / "trainer_data.json"
IV_ORDER: Tuple[str, ...] = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")


def _ensure_sim_root() -> None:
    if not SIM_ROOT.exists():
        raise SystemExit(
            "pokemon-python directory not found. Clone it beside this repo "
            "(…/pokemon_projectV2/pokemon-python) before running battles."
        )


# Make sure Python can locate both this repo *and* pokemon-python before we try
# to import ai_policy (which, in turn, imports state/data_loader from the
# simulator checkout).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if SIM_ROOT.exists() and str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from ai_policy import ActionType, choose_ai_action  # type: ignore

try:
    # We keep the module import around (rather than only BattleState) because we
    # need to sniff out whichever snapshot helper pokemon-python exposes.
    import state  # type: ignore
except ImportError as exc:  # pragma: no cover - exercised at runtime only
    raise SystemExit(
        "Unable to import the simulator state helpers. Double-check that the "
        "pokemon-python checkout is present and that it exposes a 'state' "
        "module."
    ) from exc

if TYPE_CHECKING:
    from state import BattleState  # type: ignore
else:  # pragma: no cover - type alias for runtime use only
    BattleState = Any


def _bootstrap_sim() -> Tuple[Any, Any, Any]:
    """Import dex/sim/PokemonSet from pokemon-python with the right CWD."""
    _ensure_sim_root()
    prev_cwd = os.getcwd()
    os.chdir(SIM_ROOT)
    try:
        from data import dex  # type: ignore
        import sim.sim as sim  # type: ignore
        from sim.structs import PokemonSet  # type: ignore
    finally:
        os.chdir(prev_cwd)
    return dex, sim, PokemonSet


dex, sim_module, PokemonSet = _bootstrap_sim()


@dataclass(frozen=True)
class Trainer:
    trainer_id: str
    name: str
    battle_format: str
    team: Sequence[Dict[str, Any]]


class TrainerDataset:
    def __init__(self, json_path: Path) -> None:
        self.json_path = json_path
        with json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        trainers = payload.get("trainers", [])
        self._by_id = {entry["id"]: entry for entry in trainers}
        self._by_name = {entry["name"].lower(): entry for entry in trainers}

    def list_ids(self) -> List[str]:
        return sorted(self._by_id.keys())

    def resolve(self, identifier: str) -> Trainer:
        if identifier in self._by_id:
            entry = self._by_id[identifier]
        else:
            entry = self._by_name.get(identifier.lower())
            if entry is None:
                matches = [tid for tid in self._by_id if identifier.lower() in tid.lower()]
                hint = f" Did you mean one of: {', '.join(matches[:5])}?" if matches else ""
                raise KeyError(f"Unknown trainer '{identifier}'.{hint}")
        return Trainer(
            trainer_id=entry["id"],
            name=entry["name"],
            battle_format=entry.get("battle_format", "single"),
            team=entry.get("team", []),
        )


class BattleRequestError(RuntimeError):
    pass


class RunAndBunAIBattleRunner:
    def __init__(self, *, rng: Optional[random.Random] = None) -> None:
        self.dex = dex
        self.sim = sim_module
        self.PokemonSet = PokemonSet
        self.rng = rng or random.Random()
        self._state_builder = _locate_state_builder()

    # ------------------------------------------------------------------
    # Team loading helpers
    # ------------------------------------------------------------------
    def _to_id(self, value: Optional[str]) -> str:
        if not value:
            return ""
        to_id = getattr(self.dex, "to_id", None) or getattr(self.dex, "toId", None)
        if callable(to_id):
            return to_id(value)
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def _build_set(self, mon: Dict[str, Any]) -> Any:
        name = mon["species"]
        moves = [self._to_id(mv) for mv in mon.get("moves", [])]
        ivs = mon.get("ivs", {})
        iv_tuple = tuple(int(ivs.get(stat, 31)) for stat in IV_ORDER)
        evs = mon.get("evs") or {}
        ev_tuple = tuple(int(evs.get(stat, 0)) for stat in IV_ORDER)
        kwargs: Dict[str, Any] = {
            "name": name,
            "species": self._to_id(name),
            "item": self._to_id(mon.get("item")),
            "ability": self._to_id(mon.get("ability")),
            "moves": moves,
            "nature": self._to_id(mon.get("nature") or "bashful"),
            "level": int(mon.get("level", 100)),
            "ivs": iv_tuple,
            "evs": ev_tuple,
        }
        if mon.get("gender"):
            kwargs["gender"] = mon["gender"].lower()
        if mon.get("teraType"):
            kwargs["tera_type"] = self._to_id(mon["teraType"])
        if mon.get("shiny") is not None:
            kwargs["shiny"] = bool(mon["shiny"])
        return self.PokemonSet(**kwargs)

    def _build_team(self, trainer: Trainer) -> List[Any]:
        return [self._build_set(entry) for entry in trainer.team]

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------
    def _fetch_request(self, battle: Any, player_index: int) -> Dict[str, Any]:
        request = None
        if hasattr(self.sim, "get_request_data"):
            request = self.sim.get_request_data(battle, player_index)
        elif hasattr(battle, "get_request_data"):
            request = battle.get_request_data(player_index)
        elif hasattr(battle, "requests"):
            reqs = battle.requests
            if isinstance(reqs, (list, tuple)) and len(reqs) >= player_index:
                request = reqs[player_index - 1]
        if request is None:
            raise BattleRequestError(f"No request payload available for player {player_index}")
        return request

    def _force_switch(self, request: Dict[str, Any]) -> bool:
        forced = request.get("forceSwitch")
        return bool(forced and forced[0])

    def _available_moves(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        active = request.get("active") or []
        if not active:
            return []
        return active[0].get("moves", [])

    def _bench_slots(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        side = request.get("side") or {}
        return side.get("pokemon", [])

    # ------------------------------------------------------------------
    # Battle state helper
    # ------------------------------------------------------------------
    def _snapshot_battle(self, battle: Any) -> BattleState:
        return self._state_builder(battle)

    # ------------------------------------------------------------------
    # Translating ai_policy decisions into simulator commands
    # ------------------------------------------------------------------
    def _translate_move_choice(self, request: Dict[str, Any], move_obj: Any) -> str:
        moves = self._available_moves(request)
        move_id = getattr(move_obj, "id", None) or self._to_id(getattr(move_obj, "name", ""))
        for idx, move in enumerate(moves):
            if move.get("disabled"):
                continue
            req_id = move.get("id") or self._to_id(move.get("move"))
            if req_id == move_id:
                return f"move {idx}"
        # Fallback: pick the first legal slot
        for idx, move in enumerate(moves):
            if not move.get("disabled"):
                return f"move {idx}"
        return "move 0"

    def _translate_switch_choice(self, request: Dict[str, Any], switch_target: Optional[Any]) -> str:
        bench = self._bench_slots(request)
        desired = self._to_id(getattr(switch_target, "species", "")) if switch_target else None
        for idx, slot in enumerate(bench, start=1):
            if slot.get("active"):
                continue
            condition = slot.get("condition", "")
            if condition.startswith("0/"):
                continue
            ident = slot.get("ident", "")
            visible = ident.split(": ", 1)[1] if ": " in ident else ident
            slot_id = self._to_id(slot.get("details") or visible)
            if desired is None or slot_id == desired:
                return f"switch {idx}"
        raise BattleRequestError("No valid switch targets available")

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------
    def run_battle(self, trainer_a: Trainer, trainer_b: Trainer) -> str:
        team_a = self._build_team(trainer_a)
        team_b = self._build_team(trainer_b)
        battle = self.sim.Battle(
            trainer_a.battle_format,
            trainer_a.name,
            team_a,
            trainer_b.name,
            team_b,
            debug=False,
        )
        while not battle.ended:
            p1_req = self._fetch_request(battle, 1)
            p2_req = self._fetch_request(battle, 2)
            state_snapshot = self._snapshot_battle(battle)
            p1_choice = self._make_choice(0, state_snapshot, p1_req)
            p2_choice = self._make_choice(1, state_snapshot, p2_req)
            self.sim.choose(battle, 1, p1_choice)
            self.sim.choose(battle, 2, p2_choice)
            self.sim.do_turn(battle)
        return getattr(battle, "winner", "tie")

    def _make_choice(self, player_idx: int, battle_state: BattleState, request: Dict[str, Any]) -> str:
        ai_side = battle_state.sides[player_idx]
        opp_side = battle_state.sides[1 - player_idx]
        forced_switch = self._force_switch(request)
        action_type, move_obj, switch_target = choose_ai_action(ai_side, opp_side, battle_state)
        if forced_switch or action_type == "switch":
            return self._translate_switch_choice(request, switch_target)
        if move_obj is None:
            raise BattleRequestError("AI returned a move action without a move object")
        return self._translate_move_choice(request, move_obj)

    def run_series(self, trainer_a: Trainer, trainer_b: Trainer, battle_count: int) -> Dict[str, int]:
        results = {"p1": 0, "p2": 0, "ties": 0}
        for _ in range(battle_count):
            winner = self.run_battle(trainer_a, trainer_b)
            if winner in {"p1", "Run"}:
                results["p1"] += 1
            elif winner in {"p2", "Bun"}:
                results["p2"] += 1
            else:
                results["ties"] += 1
        return results


def _locate_state_builder():
    candidates = (
        getattr(state, "snapshot_from_battle", None),
        getattr(state, "battle_to_state", None),
        getattr(state, "from_sim_battle", None),
    )
    for candidate in candidates:
        if callable(candidate):
            return candidate
    battle_state_cls = getattr(state, "BattleState", None)
    if battle_state_cls and hasattr(battle_state_cls, "from_battle"):
        return getattr(battle_state_cls, "from_battle")
    raise SystemExit(
        "Could not locate a battle-state snapshot helper inside pokemon-python's "
        "state module. Please expose a function like 'snapshot_from_battle' or a "
        "BattleState.from_battle classmethod."
    )


def _parse_match(value: str) -> Tuple[str, str]:
    if "|" in value:
        left, right = value.split("|", 1)
    elif "," in value:
        left, right = value.split(",", 1)
    elif ":" in value:
        left, right = value.split(":", 1)
    else:
        raise argparse.ArgumentTypeError(
            "Match strings must look like 'Trainer A|Trainer B'"
        )
    return left.strip(), right.strip()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trainer-a",
        help="Single trainer ID/name to use as player one (if --match not provided)",
    )
    parser.add_argument(
        "--trainer-b",
        help="Single trainer ID/name to use as player two (if --match not provided)",
    )
    parser.add_argument(
        "--match",
        action="append",
        type=_parse_match,
        metavar="TRAINER_A|TRAINER_B",
        help="Queue additional trainer pairs (can be repeated)",
    )
    parser.add_argument(
        "--battle-count",
        type=int,
        default=10,
        help="Number of simulations to run per match (default: 10)",
    )
    parser.add_argument(
        "--trainer-file",
        type=Path,
        default=TRAINER_DATA_PATH,
        help="Path to trainer_data.json (defaults to repo copy)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional random seed so repeated runs stay deterministic",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List known trainer IDs and exit",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    dataset = TrainerDataset(args.trainer_file)
    if args.list:
        for ident in dataset.list_ids():
            print(ident)
        return
    matches: List[Tuple[str, str]] = []
    if args.match:
        matches.extend(args.match)
    elif args.trainer_a and args.trainer_b:
        matches.append((args.trainer_a, args.trainer_b))
    else:
        raise SystemExit("Specify --trainer-a/--trainer-b or at least one --match pair")

    runner = RunAndBunAIBattleRunner(rng=random.Random(args.seed))
    for left, right in matches:
        trainer_a = dataset.resolve(left)
        trainer_b = dataset.resolve(right)
        print(f"▶ {trainer_a.trainer_id} vs {trainer_b.trainer_id} ({args.battle_count} battles)")
        results = runner.run_series(trainer_a, trainer_b, args.battle_count)
        print(
            f"    P1 wins: {results['p1']}, P2 wins: {results['p2']}, Ties: {results['ties']}"
        )


if __name__ == "__main__":
    main()
