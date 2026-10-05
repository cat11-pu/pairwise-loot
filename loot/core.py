"""Weighted loot tables with rarity tags, distinct draws and a pity rule.

Every random decision is taken from the random source injected at
construction time, so a seeded source produces a reproducible sequence.
"""

import random

__all__ = ["LootError", "LootTable", "RARE_RARITIES"]

#: Rarities that count as a rare hit for the pity rule.
RARE_RARITIES = ("rare", "epic", "legendary")


class LootError(ValueError):
    """Raised when a table is misconfigured or a draw request is invalid."""


class LootTable:
    """An ordered weighted loot table.

    ``rng`` is the random source used for every pick; it must provide a
    ``randrange(stop)`` method.  ``pity`` is an optional
    ``(item_id, threshold)`` pair: once ``threshold`` consecutive draws
    have passed without a rare entry, the next draw is the pity item and
    the streak starts over.
    """

    def __init__(self, rng=None, pity=None):
        self._rng = rng if rng is not None else random.Random()
        self._ids = []
        self._weights = []
        self._rarities = []
        self._index = {}
        self._misses = 0
        if pity is None:
            self._pity_item = None
            self._pity_threshold = None
        else:
            self._pity_item, self._pity_threshold = pity

    # -- table building -------------------------------------------------
    def add(self, item_id, weight, rarity="common"):
        """Register an entry.

        ``weight`` is an integer; a zero weight keeps the entry in the
        table without giving it a share of any roll.  Ids are unique.
        """
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise LootError("weight must be an integer")
        if item_id in self._index:
            raise LootError("duplicate item id: %r" % (item_id,))
        self._index[item_id] = len(self._ids)
        self._ids.append(item_id)
        self._weights.append(weight)
        self._rarities.append(rarity)

    def ids(self):
        """Registered ids in registration order."""
        return list(self._ids)

    def rarity_of(self, item_id):
        """Rarity tag of a registered entry."""
        return self._rarities[self._index[item_id]]

    def pool(self, rarity=None):
        """Ids that take part in a roll for ``rarity`` (all when None)."""
        if rarity is None:
            return list(self._ids)
        return [item_id for item_id in self._ids if self.rarity_of(item_id) == rarity]

    # -- accounting -----------------------------------------------------
    def total_weight(self, rarity=None):
        """Weight of the pool."""
        return sum(self._weights)

    def prefix_sums(self, rarity=None):
        """Running total of the pool, entry by entry."""
        running = []
        acc = 0
        for weight in self._weights:
            acc += weight
            running.append(acc)
        return running

    def probabilities(self, rarity=None):
        """Normalized share of every entry of the pool."""
        total = self.total_weight(rarity)
        if total == 0:
            raise LootError("the pool carries no weight")
        shares = {}
        for item_id in self.pool(rarity):
            shares[item_id] = self._weights[self._index[item_id]] * 100 // total / 100.0
        return shares

    # -- drawing --------------------------------------------------------
    def draw(self, n=1, rarity=None):
        """Draw ``n`` entries with replacement, in sequence."""
        return [self._pick(rarity) for _ in range(n)]

    def draw_unique(self, n, rarity=None):
        """Draw ``n`` distinct entries, in sequence."""
        size = len(self.pool(rarity))
        if n > size:
            raise LootError("cannot draw %d distinct entries out of %d" % (n, size))
        picked = []
        for _ in range(n):
            item_id = self._pick(rarity)
            picked.append(item_id)
            self._weights[self._index[item_id]] = 0
        return picked

    def _pick(self, rarity=None):
        """One weighted pick, or the pity item when its streak is due."""
        if self._pity_item is not None and self._misses >= self._pity_threshold:
            return self._pity_item
        ids = self.pool(rarity)
        roll = self._rng.randrange(self.total_weight(rarity))
        item_id = ids[-1]
        for position, bound in enumerate(self.prefix_sums(rarity)):
            if roll <= bound:
                item_id = ids[position]
                break
        self._account(item_id)
        return item_id

    def _account(self, item_id):
        """Update the pity streak after a weighted pick."""
        if self._pity_item is None:
            return
        if self.rarity_of(item_id) in RARE_RARITIES:
            self._misses = 0
        else:
            self._misses += 1
