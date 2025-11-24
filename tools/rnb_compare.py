"""Compare Run & Bun reference lists (runandbun.lua + gen8.js) to pokemon-python data.

Produces tools/rnb_full_diff.json containing missing species, moves, abilities, and items
and, when possible, close-match suggestions from the python dataset.

This intentionally focuses on the global comparison (not trainer filtering).
"""
import json
import re
from pathlib import Path
from difflib import get_close_matches

ROOT = Path(r"c:/Users/mw742/pokemon_projectV2")
DATA_DIR = ROOT / 'pokemon-python' / 'data'

def norm(s: str) -> str:
    if not s:
        return ''
    s = s.lower()
    # replace fancy quotes
    s = s.replace('’', "'").replace('‘', "'")
    # strip non-alnum
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))

def extract_rnb_lists():
    lua_txt = (ROOT / 'runandbun.lua').read_text(encoding='utf-8')
    js_txt = (ROOT / 'gen8.js').read_text(encoding='utf-8')

    # attempt to extract move list from lua
    rnb_moves = set()
    m = re.search(r"move\s*=\s*\{(.*?)\}\s*\n", lua_txt, re.S)
    if m:
        block = m.group(1)
        names = re.findall(r'"([^"]+)"|\'([^\']+)' , block)
        for a, b in names:
            rnb_moves.add(a or b)

    # extract mons list
    rnb_mons = set()
    m = re.search(r"mons\s*=\s*\{(.*?)\}\s*\n", lua_txt, re.S)
    if m:
        block = m.group(1)
        names = re.findall(r'"([^"]+)"|\'([^\']+)' , block)
        for a, b in names:
            rnb_mons.add(a or b)

    # from gen8.js, pull species keys and sets (moves/abilities/items)
    gen8_species = set(re.findall(r'"([^"]+)"\s*:\s*\{', js_txt))

    gen8_moves = set(re.findall(r'"moves"\s*:\s*\[([^\]]+)\]', js_txt))
    gm = set()
    for block in gen8_moves:
        for name in re.findall(r'"([^\"]+)"', block):
            gm.add(name)

    gen8_abilities = set(re.findall(r'"ability"\s*:\s*"([^"]+)"', js_txt))
    gen8_items = set(re.findall(r'"item"\s*:\s*"([^"]+)"', js_txt))

    # combine
    moves = set(rnb_moves) | gm
    species = set(rnb_mons) | gen8_species
    abilities = set(gen8_abilities)
    items = set(gen8_items)

    # normalize empties
    moves = {m for m in moves if m}
    species = {s for s in species if s}
    abilities = {a for a in abilities if a}
    items = {i for i in items if i}

    return species, moves, abilities, items

def build_py_sets():
    pokedex = load_json(DATA_DIR / 'pokedex.json')
    old_moves = load_json(DATA_DIR / 'old_moves.json')
    moves_base = load_json(ROOT / 'moves_base.json')
    abilities = load_json(DATA_DIR / 'abilities.json')
    items = load_json(DATA_DIR / 'items.json')

    py_species = set()
    for k, v in pokedex.items():
        py_species.add(norm(k))
        if isinstance(v, dict):
            n = v.get('species') or v.get('name')
            if n:
                py_species.add(norm(n))

    py_moves = set()
    for k in moves_base.keys():
        py_moves.add(norm(k))
    for k, v in old_moves.items():
        if isinstance(v, dict):
            n = v.get('name')
            if n:
                py_moves.add(norm(n))

    py_abilities = set()
    for k, v in abilities.items():
        if isinstance(v, dict):
            n = v.get('name')
            py_abilities.add(norm(n) if n else norm(k))

    py_items = set()
    for k, v in items.items():
        if isinstance(v, dict):
            n = v.get('name')
            py_items.add(norm(n) if n else norm(k))

    # also build lookup maps to provide original keys for suggestions
    py_moves_map = {norm(k): k for k in list(moves_base.keys())}
    for k, v in old_moves.items():
        if isinstance(v, dict) and v.get('name'):
            py_moves_map[norm(v.get('name'))] = v.get('name')

    py_species_map = {norm(k): k for k in pokedex.keys()}
    py_items_map = {norm(v.get('name')): v.get('name') for k, v in items.items() if isinstance(v, dict) and v.get('name')}
    py_abilities_map = {norm(v.get('name')): v.get('name') for k, v in abilities.items() if isinstance(v, dict) and v.get('name')}

    return (py_species, py_moves, py_abilities, py_items,
            py_species_map, py_moves_map, py_items_map, py_abilities_map)

def find_missing_and_suggest(rnb_set, py_set, py_map, label):
    missing = []
    py_list = list(py_set)
    for name in sorted(rnb_set):
        n = norm(name)
        if not n:
            continue
        if n in py_set:
            continue
        # find close matches
        suggestions = get_close_matches(n, py_list, n=5, cutoff=0.7)
        sugg_readable = [py_map.get(s, s) for s in suggestions]
        missing.append({'name': name, 'norm': n, 'suggestions': sugg_readable})
    return missing

def main():
    species, moves, abilities, items = extract_rnb_lists()
    (py_species, py_moves, py_abilities, py_items,
     py_species_map, py_moves_map, py_items_map, py_abilities_map) = build_py_sets()

    missing_species = find_missing_and_suggest(species, py_species, py_species_map, 'species')
    missing_moves = find_missing_and_suggest(moves, py_moves, py_moves_map, 'moves')
    missing_items = find_missing_and_suggest(items, py_items, py_items_map, 'items')
    missing_abilities = find_missing_and_suggest(abilities, py_abilities, py_abilities_map, 'abilities')

    report = {
        'counts': {
            'rnb_species': len(species), 'py_species': len(py_species), 'missing_species': len(missing_species),
            'rnb_moves': len(moves), 'py_moves': len(py_moves), 'missing_moves': len(missing_moves),
            'rnb_items': len(items), 'py_items': len(py_items), 'missing_items': len(missing_items),
            'rnb_abilities': len(abilities), 'py_abilities': len(py_abilities), 'missing_abilities': len(missing_abilities),
        },
        'missing_species': missing_species,
        'missing_moves': missing_moves,
        'missing_items': missing_items,
        'missing_abilities': missing_abilities,
    }

    out = ROOT / 'tools' / 'rnb_full_diff.json'
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Wrote', out)

if __name__ == '__main__':
    main()
