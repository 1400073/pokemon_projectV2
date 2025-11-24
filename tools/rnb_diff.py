import json
import re
from pathlib import Path

root = Path(r"c:/Users/mw742/pokemon_projectV2")

# helper normalization
def norm(s: str) -> str:
    if s is None:
        return ""
    s = s.lower()
    # normalize some unicode punctuation
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”','"')
    # remove non-alphanumeric
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

# Load python-side data
data_dir = root / 'pokemon-python' / 'data'
with open(data_dir / 'pokedex.json', encoding='utf-8') as f:
    pokedex = json.load(f)
with open(data_dir / 'old_moves.json', encoding='utf-8') as f:
    old_moves = json.load(f)
with open(data_dir / 'abilities.json', encoding='utf-8') as f:
    abilities = json.load(f)
with open(data_dir / 'items.json', encoding='utf-8') as f:
    items = json.load(f)
with open(root / 'moves_base.json', encoding='utf-8') as f:
    moves_base = json.load(f)

# Collect python-side sets
py_species = set()
for k, v in pokedex.items():
    # some keys might be forms; include species and name fields
    py_species.add(norm(k))
    if isinstance(v, dict):
        name = v.get('species') or v.get('name')
        if name:
            py_species.add(norm(name))

py_moves = set()
for k, v in old_moves.items():
    if isinstance(v, dict):
        name = v.get('name')
        if name:
            py_moves.add(norm(name))
# also moves_base
for name in moves_base.keys():
    py_moves.add(norm(name))

py_abilities = set()
for k, v in abilities.items():
    if isinstance(v, dict):
        name = v.get('name')
        if name:
            py_abilities.add(norm(name))
        else:
            py_abilities.add(norm(k))

py_items = set()
for k, v in items.items():
    if isinstance(v, dict):
        name = v.get('name')
        if name:
            py_items.add(norm(name))
        else:
            py_items.add(norm(k))

# Parse runandbun.lua
rnb_file = root / 'runandbun.lua'
txt = rnb_file.read_text(encoding='utf-8')

# extract move = { ... }
move_block = ''
m = re.search(r"move\s*=\s*\{(.*?)\}\s*\n", txt, re.S)
if m:
    move_block = m.group(1)
# extract quoted strings
rnb_moves = set(re.findall(r'"([^\"]+)"|\'([^\']+)' , move_block))
# re.findall returned tuples for our alternation; flatten
rnb_moves = {norm(x[0] or x[1]) for x in rnb_moves}

# extract mons = { ... }
mons_block = ''
m = re.search(r"mons\s*=\s*\{(.*?)\}\s*\n", txt, re.S)
rnb_mons = set()
if m:
    mons_block = m.group(1)
    # find quoted names
    found = re.findall(r'"([^\"]+)"|\'([^\']+)' , mons_block)
    rnb_mons = {norm(x[0] or x[1]) for x in found}

# Parse gen8.js top-level keys (species names)
gen8 = (root / 'gen8.js').read_text(encoding='utf-8')
# find keys in SETDEX_SS = {...}
# crude approach: find all keys that look like "Name":{ or 'Name':{
rnb_gen8_species = set(re.findall(r'\"([^\"]+)\"\s*:\s*\{', gen8))
rnb_gen8_species = {norm(s) for s in rnb_gen8_species}

# Parse trainer_data.json species
trainer = json.load(open(root / 'trainer_data.json', encoding='utf-8'))
rnb_trainer_species = set()
for t in trainer.get('trainers', []):
    for p in t.get('team', []):
        s = p.get('species')
        if s:
            rnb_trainer_species.add(norm(s))

# combine RnB species
rnb_species = set()
rnb_species.update(rnb_mons)
rnb_species.update(rnb_gen8_species)
rnb_species.update(rnb_trainer_species)

# Moves from gen8.js and trainer teams (moves in sets)
rnb_moves_from_gen8 = set(re.findall(r'\[\"([A-Za-z0-9 \-\'\!.?&]+)\"\]', gen8))
# also extract moves listed in JS as "moves":[".."]," by regex
rnb_moves_in_sets = set(re.findall(r'"moves"\s*:\s*\[([^\]]+)\]', gen8))
moves_from_sets = set()
for block in rnb_moves_in_sets:
    names = re.findall(r'"([^\"]+)"', block)
    for n in names:
        moves_from_sets.add(norm(n))

rnb_moves.update(moves_from_sets)

# Abilities and items referenced in gen8.js sets
rnb_abilities = set(re.findall(r'"ability"\s*:\s*\"([^\"]+)\"', gen8))
rnb_items = set(re.findall(r'"item"\s*:\s*\"([^\"]+)\"', gen8))
rnb_abilities = {norm(s) for s in rnb_abilities}
rnb_items = {norm(s) for s in rnb_items}

# Also scan trainer_data.json moves/abilities/items
for t in trainer.get('trainers', []):
    for p in t.get('team', []):
        if p.get('ability'):
            rnb_abilities.add(norm(p.get('ability')))
        if p.get('item'):
            rnb_items.add(norm(p.get('item')))
        for mv in p.get('moves', []):
            rnb_moves.add(norm(mv))

# Diffing
missing_species = sorted([s for s in rnb_species if s and s not in py_species])
extra_species = sorted([s for s in py_species if s and s not in rnb_species])
missing_moves = sorted([s for s in rnb_moves if s and s not in py_moves])
extra_moves = sorted([s for s in py_moves if s and s not in rnb_moves])
missing_abilities = sorted([s for s in rnb_abilities if s and s not in py_abilities])
extra_abilities = sorted([s for s in py_abilities if s and s not in rnb_abilities])
missing_items = sorted([s for s in rnb_items if s and s not in py_items])
extra_items = sorted([s for s in py_items if s and s not in rnb_items])

report = {
    'counts': {
        'rnb_species': len(rnb_species),
        'py_species': len(py_species),
        'rnb_moves': len(rnb_moves),
        'py_moves': len(py_moves),
        'rnb_abilities': len(rnb_abilities),
        'py_abilities': len(py_abilities),
        'rnb_items': len(rnb_items),
        'py_items': len(py_items),
    },
    'missing_species_sample': missing_species[:50],
    'missing_moves_sample': missing_moves[:50],
    'missing_abilities_sample': missing_abilities[:50],
    'missing_items_sample': missing_items[:50],
    'missing_species_count': len(missing_species),
    'missing_moves_count': len(missing_moves),
    'missing_abilities_count': len(missing_abilities),
    'missing_items_count': len(missing_items),
}

outp = root / 'tools' / 'rnb_diff_report.json'
outp.write_text(json.dumps(report, indent=2), encoding='utf-8')

print(json.dumps(report, indent=2))
print('Full missing species:', len(missing_species))
print('Full missing moves:', len(missing_moves))
print('Saved report to', outp)
