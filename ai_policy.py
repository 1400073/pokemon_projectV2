# ai_policy.py
"""AI decision policy tuned to the Run & Bun single-battle documents.

The logic mirrors "AI Document for RnB (1.07)" plus the post-KO switch guide.
Scores incorporate the stochastic weights (80/20 etc.) described in Croven's
reference so downstream tooling can rely on the documented behaviour.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple

from data_loader import MoveData
from damage import TYPE_CHART, calculate_damage, type_effectiveness
from state import BattleState, PokemonState, SideState


NON_DAMAGE_MOVE_BASE = 6
ActionType = Literal["move", "switch"]


KILL_BOOST_ABILITIES = {"Moxie", "Beast Boost", "Chilling Neigh", "Grim Neigh"}
HIGH_CRIT_MOVES = {
    "Slash",
    "Night Slash",
    "Shadow Claw",
    "Cross Chop",
    "Poison Tail",
    "Leaf Blade",
    "Drill Run",
    "Stone Edge",
    "Psycho Cut",
    "Karate Chop",
    "Razor Leaf",
    "Crabhammer",
    "Blaze Kick",
    "Air Cutter",
    "Sky Attack",
    "Sniper Shot",
}

TRAPPING_DAMAGE_MOVES = {
    "Fire Spin",
    "Clamp",
    "Whirlpool",
    "Bind",
    "Wrap",
    "Sand Tomb",
    "Magma Storm",
    "Infestation",
    "Snap Trap",
    "Thunder Cage",
}

DAMAGE_ROLL_EXCLUSIONS = {
    "Explosion",
    "Self-Destruct",
    "Misty Explosion",
    "Final Gambit",
    "Relic Song",
    "Rollout",
    "Meteor Beam",
    "Future Sight",
} | TRAPPING_DAMAGE_MOVES

SPEED_CONTROL_MOVES = {"Icy Wind", "Electroweb", "Rock Tomb", "Mud Shot", "Low Sweep"}
ATK_SPATK_DROP_MOVES = {
    "Trop Kick",
    "Chilling Water",
    "Spirit Break",
    "Skitter Smack",
    "Lunge",
    "Breaking Swipe",
    "Apple Acid",
}
SPDEF_TWO_DROP_MOVES = {"Acid Spray"}

RECOVERY_MOVES = {"Recover", "Slack Off", "Heal Order", "Soft-Boiled", "Roost", "Strength Sap"}
SUN_RECOVERY_MOVES = {"Morning Sun", "Synthesis", "Moonlight"}
REST_MOVES = {"Rest"}

SLEEP_STATUS_MOVES = {
    "Yawn",
    "Dark Void",
    "Grasswhistle",
    "Sing",
    "Sleep Powder",
    "Spore",
    "Hypnosis",
}

PARALYSIS_MOVES = {"Thunder Wave", "Stun Spore", "Glare", "Nuzzle", "Zap Cannon"}
WILL_O_WISP_MOVES = {"Will-O-Wisp"}
POISON_STATUS_MOVES = {"Toxic", "Poison Powder", "Poison Gas", "Toxic Thread"}

STICKY_WEB_SET = {"Sticky Web"}
SPIKES_SET = {"Spikes", "Toxic Spikes"}

PROTECT_MOVES = {"Protect", "Detect", "King's Shield"}
SUBSTITUTE_MOVES = {"Substitute"}

SCREENS = {"Light Screen", "Reflect"}
TERRAIN_MOVES = {"Electric Terrain", "Psychic Terrain", "Grassy Terrain", "Misty Terrain"}
TAILWIND_MOVES = {"Tailwind"}
TRICK_ROOM_MOVES = {"Trick Room"}
FAKE_OUT_MOVES = {"Fake Out"}
HELPING_HAND_MOVES = {"Helping Hand", "Follow Me"}
TRICK_MOVES = {"Trick", "Switcheroo"}
BATON_PASS_MOVES = {"Baton Pass"}
COACHING_MOVES = {"Coaching"}
FOCUS_ENERGY_MOVES = {"Focus Energy", "Laser Focus"}
DESTINY_BOND_MOVES = {"Destiny Bond"}
MEMENTO_MOVES = {"Memento"}
BOOM_MOVES = {"Explosion", "Self-Destruct", "Misty Explosion"}
FINAL_GAMBIT_MOVES = {"Final Gambit"}
TAIL_GLOW_MOVES = {"Tail Glow", "Nasty Plot", "Work Up"}
SHELL_SMASH_MOVES = {"Shell Smash"}
BELLY_DRUM_MOVES = {"Belly Drum"}
AGILITY_MOVES = {"Agility", "Rock Polish", "Autotomize"}
COUNTER_MOVES = {"Counter", "Mirror Coat"}
POISONING_BONUS_MOVES = {"Venoshock", "Venom Drench"}

GENERAL_SETUP_MOVES = {
    "Power-up Punch",
    "Swords Dance",
    "Howl",
    "Stuff Cheeks",
    "Barrier",
    "Acid Armor",
    "Iron Defense",
    "Cotton Guard",
    "Charge Beam",
    "Tail Glow",
    "Nasty Plot",
    "Cosmic Power",
    "Bulk Up",
    "Calm Mind",
    "Dragon Dance",
    "Coil",
    "Hone Claws",
    "Quiver Dance",
    "Shift Gear",
    "Shell Smash",
    "Growth",
    "Work Up",
    "Curse",
    "No Retreat",
}

UNAWARE_IGNORED_MOVES = {"Power-up Punch", "Swords Dance", "Howl"}
OFFENSIVE_SETUP_MOVES = {"Dragon Dance", "Shift Gear", "Swords Dance", "Howl", "Sharpen", "Meditate", "Hone Claws", "Power-up Punch", "Charge Beam", "Work Up", "Growth", "Curse", "No Retreat"}
DEFENSIVE_SETUP_MOVES = {"Acid Armor", "Barrier", "Cotton Guard", "Harden", "Iron Defense", "Stockpile", "Cosmic Power", "Stuff Cheeks"}
MIXED_SETUP_MOVES = {"Bulk Up", "Calm Mind", "Coil", "Quiver Dance", "No Retreat"}
BOTH_DEF_BOOST_MOVES = {"Cosmic Power", "Stockpile"}

HEX_MOVES = {"Hex"}
FLINCH_MOVES = {"Air Slash", "Bite", "Crunch", "Dark Pulse", "Fake Out", "Iron Head", "Rock Slide", "Waterfall", "Zen Headbutt", "Icicle Crash", "Stomp", "Headbutt"}
SOUND_MOVES = {"Boomburst", "Bug Buzz", "Chatter", "Clanging Scales", "Clangorous Soul", "Disarming Voice", "Echoed Voice", "Hyper Voice", "Metal Sound", "Overdrive", "Relic Song", "Round", "Snarl", "Sparkling Aria", "Uproar"}

SLEEP_PREVENT_ABILITIES = {"Insomnia", "Vital Spirit", "Comatose", "Sweet Veil", "Purifying Salt"}
PARALYZE_IMMUNE_ABILITIES = {"Limber"}
POISON_IMMUNE_ABILITIES = {"Immunity", "Leaf Guard", "Pastel Veil", "Purifying Salt"}

SLEEP_HEAL_ITEMS = {"Lum Berry", "Chesto Berry"}


@dataclass
class MoveDamageInfo:
    min_damage: int
    max_damage: int
    roll: int
    kills: bool
    is_highest: bool = False


def _is_damaging(move: MoveData) -> bool:
    return move.category in ("Physical", "Special") and move.power > 0


def _get_side_index(state: BattleState, mon: PokemonState) -> Optional[int]:
    for idx, side in enumerate(state.sides):
        if mon in side.active or mon in side.party:
            return idx
    return None


def _build_damage_snapshot(
    attacker: PokemonState,
    defender: PokemonState,
    state: BattleState,
    moves: Optional[Sequence[MoveData]] = None,
) -> Dict[MoveData, MoveDamageInfo]:
    moves = moves or attacker.moves
    snapshot: Dict[MoveData, MoveDamageInfo] = {}
    att_idx = _get_side_index(state, attacker)
    def_idx = _get_side_index(state, defender)
    highest_roll = -1
    highest: List[MoveData] = []

    for mv in moves:
        if not _is_damaging(mv):
            continue

        dmg_min, dmg_max = calculate_damage(
            attacker,
            defender,
            mv,
            state.field,
            attacker_side_idx=att_idx,
            defender_side_idx=def_idx,
        )

        if dmg_max <= 0:
            roll = 0
        else:
            roll = random.randint(max(1, dmg_min), dmg_max)

        info = MoveDamageInfo(
            min_damage=max(0, dmg_min),
            max_damage=max(0, dmg_max),
            roll=roll,
            kills=dmg_max >= defender.current_hp,
        )
        snapshot[mv] = info

        if mv.name in DAMAGE_ROLL_EXCLUSIONS:
            continue
        if roll > highest_roll:
            highest_roll = roll
            highest = [mv]
        elif roll == highest_roll:
            highest.append(mv)

    for mv in highest:
        if mv in snapshot:
            snapshot[mv].is_highest = True
    return snapshot


def _roll_high_damage_bonus() -> int:
    return 8 if random.random() < 0.2 else 6


def _roll_pair(low: int, high: int, high_prob: float) -> int:
    return high if random.random() < high_prob else low


def _calc_speed(mon: PokemonState, state: BattleState) -> int:
    idx = _get_side_index(state, mon)
    return mon.get_effective_speed(state.field, idx)


def _player_damage_bounds(attacker: PokemonState, defender: PokemonState, state: BattleState) -> Tuple[int, int]:
    return best_damage(attacker, defender, attacker.moves or [], state)


def _player_can_ko(attacker: PokemonState, defender: PokemonState, state: BattleState) -> bool:
    _, mx = _player_damage_bounds(attacker, defender, state)
    return mx >= defender.current_hp


def _player_two_hko(attacker: PokemonState, defender: PokemonState, state: BattleState) -> bool:
    _, mx = _player_damage_bounds(attacker, defender, state)
    return mx * 2 >= defender.current_hp


def _player_has_move_category(mon: PokemonState, category: str) -> bool:
    for mv in mon.moves or []:
        if mv.category == category and _is_damaging(mv):
            return True
    return False


def _player_has_sound_move(mon: PokemonState) -> bool:
    for mv in mon.moves or []:
        if mv.name in SOUND_MOVES:
            return True
    return False


def _player_has_move_named(mon: PokemonState, names: Iterable[str]) -> bool:
    targets = set(names)
    return any(mv.name in targets for mv in mon.moves or [])


def _player_incapacitated(mon: PokemonState) -> bool:
    if mon.status in {"slp", "frz"}:
        return True
    if mon.volatiles.get("recharge"):
        return True
    if mon.volatiles.get("truant"):
        return True
    return False


def _has_sturdy_or_sash(mon: PokemonState) -> bool:
    if mon.current_hp < mon.max_hp:
        return False
    if mon.ability == "Sturdy":
        return True
    if mon.item == "Focus Sash":
        return True
    return False


def _first_turn_out(mon: PokemonState) -> bool:
    return mon.last_move_used is None


def _has_hex_option(mon: PokemonState, side: SideState) -> bool:
    if mon.ability == "Hex":
        return True
    if _player_has_move_named(mon, HEX_MOVES):
        return True
    if len(side.active) > 1:
        partner = side.active[1]
        if partner and _player_has_move_named(partner, HEX_MOVES):
            return True
    return False


def _has_flinch_option(mon: PokemonState) -> bool:
    return any(mv.name in FLINCH_MOVES for mv in mon.moves or [])


def _player_has_damaging_moves(mon: PokemonState) -> bool:
    return any(_is_damaging(mv) for mv in mon.moves or [])


def _can_be_poisoned(target: PokemonState) -> bool:
    if target.status is not None:
        return False
    if "Steel" in target.types or "Poison" in target.types:
        return False
    if target.ability in POISON_IMMUNE_ABILITIES:
        return False
    return True


def _can_be_paralyzed(target: PokemonState, field) -> bool:
    if target.status is not None:
        return False
    if "Ground" in target.types:
        return False
    if target.ability in PARALYZE_IMMUNE_ABILITIES:
        return False
    if field.has_terrain("Misty") and target.is_grounded(field):
        return False
    return True


def _can_be_put_to_sleep(target: PokemonState, field) -> bool:
    if target.status is not None:
        return False
    if target.ability in SLEEP_PREVENT_ABILITIES:
        return False
    if field.has_terrain("Electric") and target.is_grounded(field):
        return False
    if field.has_terrain("Misty") and target.is_grounded(field):
        return False
    return True


def _should_ai_recover(attacker: PokemonState, defender: PokemonState, state: BattleState, heal_percent: int) -> bool:
    if attacker.status == "tox":
        return False

    heal_amount = max(1, attacker.max_hp * heal_percent // 100)
    _, opp_max = _player_damage_bounds(defender, attacker, state)
    if opp_max >= heal_amount:
        return False

    attacker_speed = _calc_speed(attacker, state)
    defender_speed = _calc_speed(defender, state)

    healed_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)

    if attacker_speed > defender_speed:
        if opp_max >= attacker.current_hp and opp_max < healed_hp:
            return True
        if opp_max < attacker.current_hp:
            pct = attacker.current_hp * 100 // attacker.max_hp
            if pct < 40:
                return True
            if 40 <= pct < 66:
                return random.random() < 0.5
    else:
        pct = attacker.current_hp * 100 // attacker.max_hp
        if pct < 50:
            return True
        if pct < 70:
            return random.random() < 0.75

    return False


def _score_recovery_move(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    if attacker.current_hp >= attacker.max_hp:
        return -20
    if attacker.current_hp * 100 // attacker.max_hp >= 85:
        return -6

    if move.name in SUN_RECOVERY_MOVES and state.field.has_weather("Sun"):
        if _should_ai_recover(attacker, defender, state, 67):
            return 7
        should = _should_ai_recover(attacker, defender, state, 50)
        return 7 if should else 5

    if move.name in REST_MOVES:
        should = _should_ai_recover(attacker, defender, state, 100)
        if not should:
            return 5
        has_sleep_cure = (
            attacker.item in SLEEP_HEAL_ITEMS
            or attacker.ability in ("Shed Skin", "Early Bird", "Hydration")
            or _player_has_move_named(attacker, {"Sleep Talk", "Snore"})
        )
        return 8 if has_sleep_cure else 7

    should = _should_ai_recover(attacker, defender, state, 50)
    return 7 if should else 5


def _score_sleep_move(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    if not _can_be_put_to_sleep(defender, state.field):
        return -10
    base = 6
    if random.random() < 0.25:
        if _player_has_move_named(attacker, {"Dream Eater", "Nightmare"}) and not _player_has_move_named(defender, {"Snore", "Sleep Talk"}):
            base += 1
        if _player_has_move_named(attacker, HEX_MOVES):
            base += 1
        base += 1
    return base


def _score_paralysis_move(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    if not _can_be_paralyzed(defender, state.field):
        return -10
    score = 8
    attacker_speed = _calc_speed(attacker, state)
    defender_speed = _calc_speed(defender, state)
    slower_after_para = defender_speed > attacker_speed and defender_speed // 4 <= attacker_speed
    if not slower_after_para and not _has_hex_option(attacker, state.sides[_get_side_index(state, attacker) or 0]) and not _has_flinch_option(attacker):
        score = 7
    if random.random() < 0.5:
        score -= 1
    return score


def _score_wisp(attacker: PokemonState, defender: PokemonState) -> int:
    if defender.status is not None or "Fire" in defender.types or defender.ability == "Flash Fire":
        return -10
    score = 6
    if random.random() < 0.37:
        if _player_has_move_category(defender, "Physical"):
            score += 1
        if _player_has_move_named(attacker, HEX_MOVES):
            score += 1
    return score


def _score_poison_status(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    if not _can_be_poisoned(defender):
        return -10
    score = 6
    if random.random() < 0.38 and not _player_can_ko(defender, attacker, state):
        if defender.current_hp * 100 // defender.max_hp > 20 and not _player_has_damaging_moves(defender):
            has_bonus_tool = (
                attacker.ability == "Merciless"
                or _player_has_move_named(attacker, HEX_MOVES | POISONING_BONUS_MOVES)
            )
            if has_bonus_tool:
                score += 2
    return score


def _score_imprison(attacker: PokemonState, defender: PokemonState) -> int:
    attacker_moves = {mv.name for mv in attacker.moves or []}
    defender_moves = {mv.name for mv in defender.moves or []}
    if attacker_moves & defender_moves:
        return 9
    return -20


def _is_status_neg_state(mon: PokemonState) -> bool:
    if mon.status in {"brn", "psn", "tox"}:
        return True
    if mon.volatiles.get("leech_seed") is not None:
        return True
    if mon.volatiles.get("infatuated_with") is not None:
        return True
    if mon.volatiles.get("perish_song"):
        return True
    if mon.volatiles.get("yawn_turns"):
        return True
    return False


def _player_has_neg_state(mon: PokemonState) -> bool:
    if mon.status in {"brn", "psn", "tox", "par", "slp"}:
        return True
    if mon.volatiles.get("leech_seed") is not None:
        return True
    if mon.volatiles.get("infatuated_with") is not None:
        return True
    if mon.volatiles.get("perish_song"):
        return True
    if mon.volatiles.get("yawn_turns"):
        return True
    return False


def _predict_residual_damage(mon: PokemonState, state: BattleState) -> int:
    if mon.current_hp <= 0:
        return 0
    if mon.ability == "Magic Guard":
        return 0

    max_hp = max(1, mon.max_hp)
    damage = 0

    if mon.status == "brn":
        damage += max(1, max_hp // 16)
    elif mon.status == "psn":
        damage += max(1, max_hp // 8)
    elif mon.status == "tox":
        counter = max(1, mon.toxic_counter or 1)
        damage += max(1, (max_hp // 16) * counter)

    if mon.volatiles.get("leech_seed") is not None:
        damage += max(1, max_hp // 8)

    if mon.volatiles.get("partial_trap"):
        damage += max(1, max_hp // 8)

    if mon.is_salt_cure:
        damage += max(1, max_hp // 8)

    weather = state.field.weather
    if weather == "Sandstorm":
        if not any(t in mon.types for t in ("Rock", "Ground", "Steel")) and mon.ability not in ("Sand Force", "Sand Rush"):
            if mon.ability not in ("Overcoat", "Magic Guard") and mon.item != "Safety Goggles":
                damage += max(1, max_hp // 16)
    elif weather in ("Hail", "Snow"):
        if "Ice" not in mon.types and mon.ability not in ("Ice Body", "Snow Cloak") and mon.item != "Safety Goggles" and mon.ability != "Overcoat":
            damage += max(1, max_hp // 16)

    return damage


def _score_protect(attacker: PokemonState, defender: PokemonState, move: MoveData, state: BattleState) -> int:
    score = 6
    if _is_status_neg_state(attacker):
        score -= 2
    if _player_has_neg_state(defender):
        score += 1
    if _first_turn_out(attacker):
        score -= 1
    if _predict_residual_damage(attacker, state) >= attacker.current_hp:
        return -20
    streak = attacker.volatiles.get("protect_streak", 0)
    if streak >= 2:
        return -20
    if streak == 1 and random.random() < 0.5:
        return -20
    return score


def _score_hazard(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    attacker_idx = _get_side_index(state, attacker) or 0
    defender_idx = 1 - attacker_idx
    first_turn = _first_turn_out(attacker)

    if move.name == "Stealth Rock":
        base = _roll_pair(9 if first_turn else 7, 8 if first_turn else 6, 0.25)
        if state.field.stealth_rocks[defender_idx]:
            base -= 1
        return base
    if move.name in ("Spikes", "Toxic Spikes"):
        base = _roll_pair(9 if first_turn else 7, 8 if first_turn else 6, 0.25)
        layers = state.field.spikes if move.name == "Spikes" else state.field.toxic_spikes
        max_layers = 3 if move.name == "Spikes" else 2
        if layers[defender_idx] >= max_layers:
            return -10
        if layers[defender_idx] > 0:
            base -= 1
        return base
    if move.name == "Sticky Web":
        base = _roll_pair(12 if first_turn else 9, 9 if first_turn else 6, 0.75)
        if state.field.sticky_web[defender_idx]:
            base -= 1
        return base
    return NON_DAMAGE_MOVE_BASE


def _score_substitute(attacker: PokemonState, defender: PokemonState) -> int:
    if attacker.current_hp * 2 <= attacker.max_hp:
        return -20
    if defender.ability == "Infiltrator":
        return -20
    score = 6
    if defender.status == "slp":
        score += 2
    if defender.volatiles.get("leech_seed") is not None and _calc_speed(attacker, BattleState([SideState([], [])], None)) > _calc_speed(defender, BattleState([SideState([], [])], None)):
        score += 2
    if random.random() < 0.5:
        score -= 1
    if _player_has_sound_move(defender):
        score -= 8
    return score


def _score_tailwind(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    faster = _calc_speed(attacker, state) < _calc_speed(defender, state)
    return 9 if faster else 5


def _score_trick_room(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    field = state.field
    faster = _calc_speed(attacker, state) < _calc_speed(defender, state)
    if field.is_trick_room_active():
        return -20
    return 10 if faster else 5


def _score_fake_out(attacker: PokemonState, defender: PokemonState) -> int:
    if not _first_turn_out(attacker):
        return -10
    if defender.ability in ("Shield Dust", "Inner Focus"):
        return -10
    return 9


def _score_tail_glow(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    score = 6
    if _player_incapacitated(defender):
        score += 3
    elif not _player_two_hko(defender, attacker, state):
        score += 1
    if _calc_speed(attacker, state) > _calc_speed(defender, state):
        score += 1
    if _player_two_hko(defender, attacker, state):
        score -= 5
    if attacker.stat_stages.get("SpA", 0) >= 2:
        score -= 1
    return score


def _score_shell_smash(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    if attacker.stat_stages.get("Atk", 0) >= 1 or attacker.stat_stages.get("SpA", 0) >= 6:
        return -20
    score = 6
    if _player_incapacitated(defender):
        score += 3
    if not _player_can_ko(defender, attacker, state):
        score += 2
    else:
        score -= 2
    return score


def _score_belly_drum(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    if _player_incapacitated(defender):
        return 9
    if not _player_can_ko(defender, attacker, state):
        return 8
    return 4


def _score_agility(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    if _calc_speed(attacker, state) >= _calc_speed(defender, state):
        return -20
    return 7


def _score_focus_energy(attacker: PokemonState) -> int:
    if attacker.ability in ("Super Luck", "Sniper"):
        return 7
    if attacker.item in ("Scope Lens", "Razor Claw"):
        return 7
    if any(mv.name in HIGH_CRIT_MOVES for mv in attacker.moves or []):
        return 7
    return 6


def _score_coaching(attacker: PokemonState, state: BattleState) -> int:
    idx = _get_side_index(state, attacker) or 0
    side = state.sides[idx]
    if len(side.active) == 1:
        return -20
    partner = side.active[1]
    if partner.ability == "Contrary":
        return -20
    score = 6
    atk_stage = partner.stat_stages.get("Atk", 0)
    def_stage = partner.stat_stages.get("Def", 0)
    if atk_stage < 2:
        score += 1 - atk_stage
    if def_stage < 2:
        score += 1 - def_stage
    if random.random() < 0.8:
        score += 1
    return score


def _has_pass_targets(side: SideState, active: PokemonState) -> bool:
    for mon in side.party:
        if mon is active:
            continue
        if mon.current_hp > 0 and mon not in side.active:
            return True
    return False


def _score_baton_pass(attacker: PokemonState, side: SideState) -> int:
    if not _has_pass_targets(side, attacker):
        return -20
    has_boost = any(stage > 0 for stage in attacker.stat_stages.values()) or attacker.substitute_hp is not None
    if has_boost:
        return 14
    return 0


def _score_terrain(attacker: PokemonState, move: MoveData) -> int:
    return 9 if attacker.item == "Terrain Extender" else 8


def _score_screens(attacker: PokemonState, defender: PokemonState, move: MoveData) -> int:
    score = 6
    if move.name == "Reflect" and _player_has_move_category(defender, "Physical"):
        score += 1
    if move.name == "Light Screen" and _player_has_move_category(defender, "Special"):
        score += 1
    if attacker.item == "Light Clay":
        score += 1
    if random.random() < 0.5:
        score += 1
    return score


def _score_explosion(attacker: PokemonState, defender: PokemonState, move: MoveData) -> int:
    if "Ghost" in defender.types:
        return -20
    hp_pct = attacker.current_hp * 100 // attacker.max_hp
    if hp_pct < 10:
        return 10
    if hp_pct < 33:
        return 8 if random.random() < 0.7 else 0
    if hp_pct < 66:
        return 7 if random.random() < 0.5 else 0
    score = 7 if random.random() < 0.05 else 0
    if attacker.current_hp == defender.current_hp == 1:
        score -= 1
    return score


def _score_memento(attacker: PokemonState) -> int:
    hp_pct = attacker.current_hp * 100 // attacker.max_hp
    if hp_pct < 10:
        return 16
    if hp_pct < 33:
        return 14 if random.random() < 0.7 else 6
    if hp_pct < 66:
        return 13 if random.random() < 0.5 else 6
    return 13 if random.random() < 0.05 else 6


def _score_destiny_bond(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    faster = _calc_speed(attacker, state) > _calc_speed(defender, state)
    if faster and _player_can_ko(defender, attacker, state):
        return 7 if random.random() < 0.81 else 6
    if faster:
        return 6
    return 5 if random.random() < 0.5 else 6


def _score_final_gambit(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    faster = _calc_speed(attacker, state) > _calc_speed(defender, state)
    if faster and attacker.current_hp > defender.current_hp:
        return 8
    if faster and _player_can_ko(defender, attacker, state):
        return 7
    return 6


def _score_trick_move(attacker: PokemonState, move: MoveData) -> int:
    if attacker.item in {"Toxic Orb", "Flame Orb", "Black Sludge"}:
        return 7 if random.random() < 0.5 else 6
    if attacker.item in {"Iron Ball", "Lagging Tail", "Sticky Barb"}:
        return 7
    return 5


def _score_taunt(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    if _player_has_move_named(defender, TRICK_ROOM_MOVES) and not state.field.is_trick_room_active():
        return 9
    if _player_has_move_named(defender, {"Defog"}) and state.field.aurora_veil and _calc_speed(attacker, state) > _calc_speed(defender, state):
        return 9
    return 5


def _score_encore(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    if defender.volatiles.get("encore"):
        return -20
    if _first_turn_out(defender):
        return -20
    faster = _calc_speed(attacker, state) > _calc_speed(defender, state)
    if faster:
        return 7
    return 6 if random.random() < 0.5 else 5


def _score_counter(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    if _player_can_ko(defender, attacker, state) and not _has_sturdy_or_sash(attacker):
        return -20
    only_split = not _player_has_move_category(defender, "Physical" if move.name == "Counter" else "Special")
    score = 6
    if only_split:
        score += 2 if random.random() < 0.8 else 0
    if _calc_speed(attacker, state) > _calc_speed(defender, state) and random.random() < 0.25:
        score -= 1
    if any(mv.category == "Status" for mv in defender.moves or []) and random.random() < 0.25:
        score -= 1
    return score


def _score_status_move(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    name = move.name
    if name in RECOVERY_MOVES or name in SUN_RECOVERY_MOVES or name in REST_MOVES:
        return _score_recovery_move(attacker, defender, state, move)
    if name in SLEEP_STATUS_MOVES:
        return _score_sleep_move(attacker, defender, state, move)
    if name in PARALYSIS_MOVES:
        return _score_paralysis_move(attacker, defender, state, move)
    if name in WILL_O_WISP_MOVES:
        return _score_wisp(attacker, defender)
    if name in POISON_STATUS_MOVES:
        return _score_poison_status(attacker, defender, state)
    if name in PROTECT_MOVES:
        return _score_protect(attacker, defender, move, state)
    if name in STICKY_WEB_SET | {"Stealth Rock", "Spikes", "Toxic Spikes"}:
        return _score_hazard(attacker, defender, state, move)
    if name in SUBSTITUTE_MOVES:
        return _score_substitute(attacker, defender)
    if name in TAILWIND_MOVES:
        return _score_tailwind(attacker, defender, state)
    if name in TRICK_ROOM_MOVES:
        return _score_trick_room(attacker, defender, state)
    if name in FAKE_OUT_MOVES:
        return _score_fake_out(attacker, defender)
    if name in TERRAIN_MOVES:
        return _score_terrain(attacker, move)
    if name in SCREENS:
        return _score_screens(attacker, defender, move)
    if name in HELPING_HAND_MOVES:
        return 6
    if name in TRICK_MOVES:
        return _score_trick_move(attacker, move)
    if name == "Imprison":
        return _score_imprison(attacker, defender)
    if name in BATON_PASS_MOVES:
        idx = _get_side_index(state, attacker) or 0
        return _score_baton_pass(attacker, state.sides[idx])
    if name in COACHING_MOVES:
        return _score_coaching(attacker, state)
    if name in FOCUS_ENERGY_MOVES:
        return _score_focus_energy(attacker)
    if name in DESTINY_BOND_MOVES:
        return _score_destiny_bond(attacker, defender, state)
    if name in MEMENTO_MOVES:
        return _score_memento(attacker)
    if name in COUNTER_MOVES:
        return _score_counter(attacker, defender, state, move)
    if name in TAIL_GLOW_MOVES:
        return _score_tail_glow(attacker, defender, state, move)
    if name in SHELL_SMASH_MOVES:
        return _score_shell_smash(attacker, defender, state)
    if name in BELLY_DRUM_MOVES:
        return _score_belly_drum(attacker, defender, state)
    if name in AGILITY_MOVES:
        return _score_agility(attacker, defender, state)
    if name == "Taunt":
        return _score_taunt(attacker, defender, state)
    if name == "Encore":
        return _score_encore(attacker, defender, state)
    return _score_setup_move(attacker, defender, state, move)


def _apply_kill_bonuses(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData, info: MoveDamageInfo) -> int:
    if not info.kills:
        return 0
    att_speed = _calc_speed(attacker, state)
    def_speed = _calc_speed(defender, state)
    goes_first = att_speed >= def_speed
    if goes_first or (move.priority > 0 and att_speed < def_speed):
        bonus = 6
    else:
        bonus = 3
    if attacker.ability in KILL_BOOST_ABILITIES:
        bonus += 1
    return bonus


def _score_setup_move(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData) -> int:
    if move.name in GENERAL_SETUP_MOVES:
        if defender.ability == "Unaware" and move.name not in UNAWARE_IGNORED_MOVES:
            return -20
        if _player_can_ko(defender, attacker, state) and not _has_sturdy_or_sash(attacker):
            return -20

    if move.name in TAIL_GLOW_MOVES:
        return _score_tail_glow(attacker, defender, state, move)
    if move.name in SHELL_SMASH_MOVES:
        return _score_shell_smash(attacker, defender, state)
    if move.name in BELLY_DRUM_MOVES:
        return _score_belly_drum(attacker, defender, state)
    if move.name in AGILITY_MOVES:
        return _score_agility(attacker, defender, state)

    score = 6
    two_hko = _player_two_hko(defender, attacker, state)
    if move.name in DEFENSIVE_SETUP_MOVES:
        if _calc_speed(attacker, state) < _calc_speed(defender, state) and two_hko:
            score -= 5
        if random.random() < 0.95:
            if _player_incapacitated(defender):
                score += 2
            if move.name in BOTH_DEF_BOOST_MOVES and (
                attacker.stat_stages.get("Def", 0) < 2 or attacker.stat_stages.get("SpD", 0) < 2
            ):
                score += 2
        return score

    offensive = move.name in OFFENSIVE_SETUP_MOVES
    if move.name in MIXED_SETUP_MOVES:
        has_physical = _player_has_move_category(defender, "Physical")
        has_special = _player_has_move_category(defender, "Special")
        if move.name in {"Bulk Up", "Coil", "No Retreat"}:
            offensive = not (has_physical and not has_special)
        else:
            offensive = not (has_special and not has_physical)

    if offensive:
        if _player_incapacitated(defender):
            score += 3
        if _calc_speed(attacker, state) < _calc_speed(defender, state) and two_hko:
            score -= 5
        return score

    return score


def _score_special_damaging_move(attacker: PokemonState, defender: PokemonState, state: BattleState, move: MoveData, info: MoveDamageInfo) -> Optional[int]:
    name = move.name
    if name in TRAPPING_DAMAGE_MOVES:
        return _roll_high_damage_bonus()
    if name in SPEED_CONTROL_MOVES and not info.is_highest:
        blocked = defender.ability in {"Contrary", "Clear Body", "White Smoke"}
        if blocked:
            return -10
        slower = _calc_speed(attacker, state) < _calc_speed(defender, state)
        return 6 if slower else 5
    if name in ATK_SPATK_DROP_MOVES and not info.is_highest:
        blocked = defender.ability in {"Contrary", "Clear Body", "White Smoke"}
        if blocked:
            return -10
        relevant = _player_has_move_category(defender, "Physical" if name in {"Trop Kick", "Lunge", "Breaking Swipe"} else "Special")
        return 6 if relevant else 5
    if name in SPDEF_TWO_DROP_MOVES:
        base = _roll_high_damage_bonus() if info.is_highest else 0
        return base + 6
    if name == "Future Sight":
        faster = _calc_speed(attacker, state) > _calc_speed(defender, state)
        dead = _player_can_ko(defender, attacker, state)
        return 8 if faster and dead else 6
    if name == "Relic Song":
        if "Pirouette" in attacker.species:
            return -20
        return 10
    if name == "Sucker Punch" and attacker.last_move_used == "Sucker Punch":
        return -20 if random.random() < 0.5 else None
    if name == "Pursuit":
        score = 0
        kill = info.kills or defender.current_hp * 100 // defender.max_hp <= 20
        if kill:
            score += 10
        elif defender.current_hp * 100 // defender.max_hp <= 40:
            score += 8 if random.random() < 0.5 else 0
        if _calc_speed(attacker, state) > _calc_speed(defender, state):
            score += 3
        return score
    if name == "Fell Stinger" and attacker.stat_stages.get("Atk", 0) < 6 and info.kills:
        faster = _calc_speed(attacker, state) >= _calc_speed(defender, state)
        return 23 if faster and random.random() < 0.2 else 21 if faster else (17 if random.random() < 0.2 else 15)
    if name == "Rollout":
        return 7
    if name in BOOM_MOVES:
        return _score_explosion(attacker, defender, move)
    if name in MEMENTO_MOVES:
        return _score_memento(attacker)
    if name in FINAL_GAMBIT_MOVES:
        return _score_final_gambit(attacker, defender, state)
    return None


def score_move(
    attacker: PokemonState,
    defender: PokemonState,
    move: MoveData,
    state: BattleState,
    damage_snapshot: Optional[Dict[MoveData, MoveDamageInfo]] = None,
) -> int:
    if move.category == "Status" or move.power == 0:
        return _score_status_move(attacker, defender, state, move)

    snapshot = damage_snapshot or _build_damage_snapshot(attacker, defender, state)
    info = snapshot.get(move, MoveDamageInfo(0, 0, 0, False, False))

    special_score = _score_special_damaging_move(attacker, defender, state, move, info)
    score = 0 if special_score is None else special_score

    if info.is_highest and move.name not in TRAPPING_DAMAGE_MOVES:
        score += _roll_high_damage_bonus()

    score += _apply_kill_bonuses(attacker, defender, state, move, info)

    if move.name in HIGH_CRIT_MOVES and type_effectiveness(move.type, defender.types, state.field) > 1 and random.random() < 0.5:
        score += 1

    _, opp_max = _player_damage_bounds(defender, attacker, state)
    if move.priority > 0 and _calc_speed(attacker, state) < _calc_speed(defender, state) and opp_max >= attacker.current_hp:
        score += 11

    return int(score)


def choose_move(
    ai_mon: PokemonState,
    player_mon: PokemonState,
    state: BattleState,
    moves: List[MoveData],
) -> Tuple[MoveData, PokemonState]:
    snapshot = _build_damage_snapshot(ai_mon, player_mon, state, moves)
    best_score = -999
    best_moves: List[MoveData] = []
    for mv in moves:
        s = score_move(ai_mon, player_mon, mv, state, snapshot)
        if s > best_score:
            best_score = s
            best_moves = [mv]
        elif s == best_score:
            best_moves.append(mv)
    chosen = random.choice(best_moves) if best_moves else moves[0]
    return chosen, player_mon


def best_damage(attacker: PokemonState, defender: PokemonState, moves: List[MoveData], state: BattleState) -> Tuple[int, int]:
    best_min = 0
    best_max = 0
    if not moves:
        return 0, 0
    for mv in moves:
        if getattr(mv, "pp", 1) == 0:
            continue
        att_idx = _get_side_index(state, attacker)
        def_idx = _get_side_index(state, defender)
        mn, mx = calculate_damage(
            attacker,
            defender,
            mv,
            state.field,
            attacker_side_idx=att_idx,
            defender_side_idx=def_idx,
        )
        if mx > best_max:
            best_max = mx
            best_min = mn
    return best_min, best_max


def post_ko_switch_score(candidate: PokemonState, opp_mon: PokemonState, state: BattleState) -> int:
    cand_hp = max(1, candidate.current_hp)
    opp_hp = max(1, opp_mon.current_hp)

    _, cand_to_opp_max = best_damage(candidate, opp_mon, candidate.moves, state)
    _, opp_to_cand_max = best_damage(opp_mon, candidate, opp_mon.moves, state)

    cand_spe = candidate.calc_stat("Spe")
    opp_spe = opp_mon.calc_stat("Spe")
    cand_faster = cand_spe > opp_spe
    cand_slower = cand_spe < opp_spe

    cand_ohko = cand_to_opp_max >= opp_hp
    opp_ohko = opp_to_cand_max >= cand_hp

    cand_pct = cand_to_opp_max * 100 // opp_hp if opp_hp > 0 else 0
    opp_pct = opp_to_cand_max * 100 // cand_hp if cand_hp > 0 else 0

    score = 0

    if cand_slower and opp_ohko:
        score = -1
    else:
        if cand_faster and cand_ohko:
            score = 5
        elif cand_slower and cand_ohko and not opp_ohko:
            score = 4
        elif cand_faster and cand_pct > opp_pct:
            score = 3
        elif cand_slower and cand_pct > opp_pct:
            score = 2
        elif cand_faster:
            score = 1

    if candidate.species == "Ditto":
        score = max(score, 2)
    if candidate.species in {"Wynaut", "Wobbuffet"} and not (cand_slower and opp_ohko):
        score = max(score, 2)

    return score


def choose_switch_in(side: SideState, opp_mon: PokemonState, state: BattleState, candidates: Optional[List[PokemonState]] = None) -> Optional[PokemonState]:
    if candidates is None:
        candidates = [m for m in side.party if m.current_hp > 0 and m not in side.active]
    if not candidates:
        return None
    best_score = -999
    best_list: List[PokemonState] = []
    for mon in candidates:
        s = post_ko_switch_score(mon, opp_mon, state)
        if s > best_score:
            best_score = s
            best_list = [mon]
        elif s == best_score:
            best_list.append(mon)
    if not best_list:
        return None
    return random.choice(best_list)


def should_consider_switch(ai_active: PokemonState, ai_side: SideState, opp_active: PokemonState, state: BattleState) -> Optional[PokemonState]:
    bench = [m for m in ai_side.party if m.current_hp > 0 and m not in ai_side.active]
    if not bench:
        return None

    snapshot = _build_damage_snapshot(ai_active, opp_active, state, ai_active.moves or [])
    best_move_score = max((score_move(ai_active, opp_active, mv, state, snapshot) for mv in ai_active.moves or []), default=-999)
    if best_move_score > -5:
        return None

    if ai_active.current_hp * 2 < ai_active.max_hp:
        return None

    opp_speed = opp_active.calc_stat("Spe")
    found_faster = False
    viable: List[PokemonState] = []

    for mon in bench:
        mon_speed = mon.calc_stat("Spe")
        raw_fast = mon_speed > opp_speed
        if raw_fast:
            found_faster = True
        considered_fast = raw_fast or found_faster

        _, opp_to_mon_max = best_damage(opp_active, mon, opp_active.moves, state)
        mon_hp = max(1, mon.current_hp)

        not_ohko = opp_to_mon_max < mon_hp
        not_two_hko = opp_to_mon_max * 2 < mon_hp

        cond2 = (considered_fast and not_ohko) or ((not considered_fast) and not_two_hko)
        if cond2:
            viable.append(mon)

    if not viable:
        return None

    if random.random() >= 0.5:
        return None

    return choose_switch_in(ai_side, opp_active, state, viable)


def choose_ai_action(ai_side: SideState, opp_side: SideState, state: BattleState) -> Tuple[ActionType, Optional[MoveData], Optional[PokemonState]]:
    ai_active = ai_side.active[0]
    opp_active = opp_side.active[0]

    switch_target = None
    if state.field.game_type == "Singles":
        switch_target = should_consider_switch(ai_active, ai_side, opp_active, state)

    if switch_target is not None:
        return "switch", None, switch_target

    moves = ai_active.moves or []
    if not moves:
        return "move", None, opp_active

    best_move, target = choose_move(ai_active, opp_active, state, moves)
    return "move", best_move, target

RECOVERY_MOVES = {
    "Recover",
    "Roost",
    "Soft-Boiled",
    "Slack Off",
    "Milk Drink",
    "Synthesis",
    "Morning Sun",
    "Moonlight",
    "Shore Up",
    "Heal Order",
}

BOOSTING_MOVES: Dict[str, Tuple[str, int]] = {
    "Swords Dance": ("Atk", 2),
    "Dragon Dance": ("Atk", 1),
    "Bulk Up": ("Atk", 1),
    "Calm Mind": ("SpA", 1),
    "Nasty Plot": ("SpA", 2),
    "Quiver Dance": ("SpA", 1),
    "Coil": ("Atk", 1),
    "Work Up": ("Atk", 1),
}

HAZARD_MOVES = {"Stealth Rock", "Spikes", "Toxic Spikes", "Sticky Web"}
PHASING_MOVES = {"Roar", "Whirlwind", "Dragon Tail", "Circle Throw"}
STATUS_LOCK_MOVES = {"Will-O-Wisp", "Thunder Wave", "Spore", "Sleep Powder", "Glare", "Toxic"}


def _get_side_index(state: BattleState, mon: PokemonState) -> Optional[int]:
    for idx, side in enumerate(state.sides):
        if mon in side.active or mon in side.party:
            return idx
    return None


def _expected_damage_percent(attacker: PokemonState, defender: PokemonState, move: MoveData, state: BattleState) -> Tuple[float, int, int]:
    att_idx = _get_side_index(state, attacker)
    def_idx = _get_side_index(state, defender)
    dmg_min, dmg_max = calculate_damage(
        attacker,
        defender,
        move,
        state.field,
        attacker_side_idx=att_idx,
        defender_side_idx=def_idx,
    )
    accuracy = move.accuracy if move.accuracy else 100
    avg = (dmg_min + dmg_max) / 2.0
    expected = avg * (accuracy / 100.0)
    percent = expected * 100.0 / max(1, defender.current_hp)
    return percent, dmg_min, dmg_max


def best_damage(attacker: PokemonState, defender: PokemonState, moves: List[MoveData], state: BattleState) -> Tuple[int, int]:
    best_min = 0
    best_max = 0
    if not moves:
        return 0, 0
    for mv in moves:
        if getattr(mv, "pp", 1) == 0:
            continue
        att_idx = _get_side_index(state, attacker)
        def_idx = _get_side_index(state, defender)
        mn, mx = calculate_damage(
            attacker,
            defender,
            mv,
            state.field,
            attacker_side_idx=att_idx,
            defender_side_idx=def_idx,
        )
        if mx > best_max:
            best_max = mx
            best_min = mn
    return best_min, best_max

def post_ko_switch_score(candidate: PokemonState, opp_mon: PokemonState, state: BattleState) -> int:
    cand_hp = max(1, candidate.current_hp)
    opp_hp = max(1, opp_mon.current_hp)

    _, cand_to_opp_max = best_damage(candidate, opp_mon, candidate.moves, state)
    _, opp_to_cand_max = best_damage(opp_mon, candidate, opp_mon.moves, state)

    cand_spe = candidate.calc_stat("Spe")
    opp_spe = opp_mon.calc_stat("Spe")
    cand_faster = cand_spe > opp_spe
    cand_slower = cand_spe < opp_spe

    cand_ohko = cand_to_opp_max >= opp_hp
    opp_ohko = opp_to_cand_max >= cand_hp

    cand_pct = cand_to_opp_max * 100 // opp_hp if opp_hp > 0 else 0
    opp_pct = opp_to_cand_max * 100 // cand_hp if cand_hp > 0 else 0

    score = 0

    # -1: slower and is OHKO’d
    if cand_slower and opp_ohko:
        score = -1
    else:
        # +5: faster and OHKO’s
        if cand_faster and cand_ohko:
            score = 5
        # +4: slower, OHKO’s, and is not OHKO’d
        elif cand_slower and cand_ohko and not opp_ohko:
            score = 4
        # +3 / +2: deals more % damage than it takes
        elif cand_faster and cand_pct > opp_pct:
            score = 3
        elif cand_slower and cand_pct > opp_pct:
            score = 2
        # +1: just faster
        elif cand_faster:
            score = 1
        else:
            score = 0

    # Ditto special case (+2)
    if candidate.species == "Ditto":
        score = max(score, 2)

    # Wynaut / Wobbuffet (+2 if not worse)
    if candidate.species in ["Wynaut", "Wobbuffet"] and not (cand_slower and opp_ohko):
        score = max(score, 2)

    return score

def choose_switch_in(side: SideState, opp_mon: PokemonState, state: BattleState, candidates: Optional[List[PokemonState]] = None) -> Optional[PokemonState]:
    if candidates is None:
        candidates = [m for m in side.party if m.current_hp > 0 and m not in side.active]
    if not candidates:
        return None
    best_score = -999
    best_list: List[PokemonState] = []
    for mon in candidates:
        s = post_ko_switch_score(mon, opp_mon, state)
        if s > best_score:
            best_score = s
            best_list = [mon]
        elif s == best_score:
            best_list.append(mon)
    if not best_list:
        return None
    return random.choice(best_list)


def matchup_score(attacker: PokemonState, defender: PokemonState, state: BattleState) -> int:
    _, atk_max = best_damage(attacker, defender, attacker.moves, state)
    _, def_max = best_damage(defender, attacker, defender.moves, state)
    offense = atk_max * 100 // max(1, defender.current_hp)
    defense = def_max * 100 // max(1, attacker.current_hp)
    speed_bonus = 10 if attacker.calc_stat("Spe") > defender.calc_stat("Spe") else 0
    return offense - defense + speed_bonus


def should_consider_switch(ai_active: PokemonState, ai_side: SideState, opp_active: PokemonState, state: BattleState) -> Optional[PokemonState]:
    bench = [m for m in ai_side.party if m.current_hp > 0 and m not in ai_side.active]
    if not bench:
        return None

    best_move_score = max((score_move(ai_active, opp_active, mv, state) for mv in ai_active.moves or []), default=-999)
    active_matchup = matchup_score(ai_active, opp_active, state)

    best_candidate = None
    best_candidate_score = active_matchup
    for mon in bench:
        cand_score = matchup_score(mon, opp_active, state)
        if cand_score > best_candidate_score:
            best_candidate_score = cand_score
            best_candidate = mon

    if best_candidate is None:
        return None

    improvement = best_candidate_score - active_matchup
    if improvement < 8 and best_move_score >= 10:
        return None

    if random.random() < 0.7:
        return best_candidate
    return None

def choose_ai_action(ai_side: SideState, opp_side: SideState, state: BattleState) -> Tuple[ActionType, Optional[MoveData], Optional[PokemonState]]:
    ai_active = ai_side.active[0]
    opp_active = opp_side.active[0]

    switch_target = None
    if state.field.game_type == "Singles":
        switch_target = should_consider_switch(ai_active, ai_side, opp_active, state)

    if switch_target is not None:
        return "switch", None, switch_target

    moves = ai_active.moves or []
    if not moves:
        return "move", None, opp_active

    best_move, target = choose_move(ai_active, opp_active, state, moves)
    return "move", best_move, target
