"""Behaviour tests for the loot table kernel."""

import random
import unittest

from loot.core import LootError, LootTable

# The table used below registers apple(weight 1, common), pear(weight 1,
# common) and ruby(weight 2, rare); this is the exact item sequence a
# table of that shape has to produce for this seed.
SEED = 20260929
SEED_SEQUENCE = [
    "ruby",
    "ruby",
    "ruby",
    "pear",
    "ruby",
    "pear",
    "ruby",
    "ruby",
    "apple",
    "apple",
    "ruby",
    "ruby",
    "ruby",
    "ruby",
    "ruby",
    "pear",
    "apple",
    "pear",
    "ruby",
    "ruby",
]


class ScriptedRandom:
    """Single-use random source returning a fixed sequence of rolls."""

    def __init__(self, rolls):
        self._rolls = list(rolls)

    def randrange(self, stop):
        if not self._rolls:
            raise AssertionError("scripted random source exhausted")
        return self._rolls.pop(0)


def weighted_table(rng):
    """apple 1, pear 1, ruby 2, in that registration order."""
    table = LootTable(rng=rng)
    table.add("apple", 1, rarity="common")
    table.add("pear", 1, rarity="common")
    table.add("ruby", 2, rarity="rare")
    return table


class LootTableTests(unittest.TestCase):
    def test_seeded_draws_are_reproducible(self):
        first = weighted_table(random.Random(SEED)).draw(20)
        second = weighted_table(random.Random(SEED)).draw(20)
        self.assertEqual(first, second)
        self.assertEqual(first, SEED_SEQUENCE)

    def test_negative_weight_is_rejected(self):
        table = LootTable(rng=random.Random(1))
        table.add("apple", 1)
        with self.assertRaises(LootError):
            table.add("cursed", -3)
        self.assertEqual(table.ids(), ["apple"])
        self.assertEqual(table.total_weight(), 1)

    def test_draw_rejects_bad_count_and_empty_table(self):
        table = weighted_table(random.Random(2))
        with self.assertRaises(LootError):
            table.draw(0)
        with self.assertRaises(LootError):
            table.draw(-2)
        with self.assertRaises(LootError):
            LootTable(rng=random.Random(3)).draw()

    def test_probabilities_match_weight_shares(self):
        table = LootTable(rng=random.Random(4))
        table.add("apple", 1)
        table.add("pear", 1)
        table.add("ruby", 7)
        shares = table.probabilities()
        self.assertEqual(sorted(shares), ["apple", "pear", "ruby"])
        self.assertAlmostEqual(sum(shares.values()), 1.0, places=9)
        self.assertAlmostEqual(shares["apple"], 1 / 9, places=9)
        self.assertAlmostEqual(shares["pear"], 1 / 9, places=9)
        self.assertAlmostEqual(shares["ruby"], 7 / 9, places=9)

    def test_draw_frequencies_follow_weights(self):
        table = weighted_table(random.Random(12345))
        draws = table.draw(600)
        for item_id, expected in (("apple", 0.25), ("pear", 0.25), ("ruby", 0.5)):
            observed = draws.count(item_id) / 600.0
            self.assertAlmostEqual(
                observed,
                expected,
                delta=0.08,
                msg="%s drawn %.3f of the time" % (item_id, observed),
            )

    def test_zero_weight_entry_is_never_drawn(self):
        table = LootTable(rng=random.Random(6))
        table.add("placeholder", 0)
        table.add("apple", 1)
        table.add("pear", 1)
        draws = table.draw(200)
        self.assertNotIn("placeholder", draws)
        self.assertEqual(set(draws), {"apple", "pear"})

    def test_draw_unique_returns_distinct_items_and_keeps_table_intact(self):
        table = LootTable(rng=random.Random(7))
        for item_id in ("apple", "pear", "ruby"):
            table.add(item_id, 1)
        before = table.total_weight()
        picked = table.draw_unique(3)
        self.assertEqual(sorted(picked), ["apple", "pear", "ruby"])
        self.assertEqual(table.total_weight(), before)
        self.assertEqual(len(table.draw(5)), 5)

    def test_rarity_filter_accounts_only_for_filtered_entries(self):
        table = LootTable(rng=random.Random(8))
        table.add("apple", 1, rarity="common")
        table.add("pear", 1, rarity="common")
        table.add("ruby", 1, rarity="rare")
        table.add("opal", 3, rarity="rare")
        self.assertEqual(table.total_weight("rare"), 4)
        self.assertEqual(table.prefix_sums("rare"), [1, 4])
        shares = table.probabilities("rare")
        self.assertEqual(sorted(shares), ["opal", "ruby"])
        self.assertAlmostEqual(shares["ruby"], 0.25, places=9)
        self.assertAlmostEqual(shares["opal"], 0.75, places=9)
        self.assertTrue(set(table.draw(12, rarity="rare")) <= {"ruby", "opal"})

    def test_pity_streak_restarts_after_a_forced_draw(self):
        table = LootTable(rng=ScriptedRandom([0, 0, 0, 0, 0, 0]), pity=("ruby", 2))
        table.add("stone", 1, rarity="common")
        table.add("ruby", 3, rarity="rare")
        self.assertEqual(
            table.draw(6),
            ["stone", "stone", "ruby", "stone", "stone", "ruby"],
        )


if __name__ == "__main__":
    unittest.main()
