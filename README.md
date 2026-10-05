# loot

A small, dependency-free weighted loot table used by the reward pipeline.

## What it does

- An ordered table of entries, each with an integer weight and a rarity tag.
- `draw(n)` picks `n` entries with replacement; `draw_unique(n)` picks `n`
  distinct entries.
- `total_weight(rarity)`, `prefix_sums(rarity)` and `probabilities(rarity)`
  describe the pool, optionally restricted to a single rarity tag.
- An optional pity rule: once a number of consecutive draws passed without a
  rare entry, the next draw is a configured pity item.
- All randomness comes from the random source injected at construction time
  (the source must provide `randrange(stop)`), so a seeded source gives a
  reproducible item sequence.

## API

```python
from loot.core import LootTable, LootError

table = LootTable(rng=random.Random(7), pity=("ruby", 10))
table.add("apple", 4, rarity="common")
table.add("ruby", 1, rarity="rare")

table.draw(3)                 # three items, with replacement
table.draw_unique(2)          # two distinct items
table.probabilities()         # {item_id: share}
```

## Requirements

Python 3 and the standard library only. No third-party packages.

## Running the tests

From the project root:

```
python3 -m unittest discover -s tests -v
```
