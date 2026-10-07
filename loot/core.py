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

        ``weight`` is a non-negative integer; a zero weight keeps the
        entry in the table without giving it a share of any roll.
        Ids are unique.
        """
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise LootError("weight must be an integer")
        if weight < 0:
            raise LootError("weight must not be negative: %r" % (weight,))
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
        return sum(self._weights[self._index[item_id]] for item_id in self.pool(rarity))

    def prefix_sums(self, rarity=None):
        """Running total of the pool, entry by entry."""
        running = []
        acc = 0
        for item_id in self.pool(rarity):
            acc += self._weights[self._index[item_id]]
            running.append(acc)
        return running

    def probabilities(self, rarity=None):
        """Normalized share of every entry of the pool."""
        total = self.total_weight(rarity)
        if total == 0:
            raise LootError("the pool carries no weight")
        shares = {}
        for item_id in self.pool(rarity):
            shares[item_id] = self._weights[self._index[item_id]] / total
        return shares

    # -- drawing --------------------------------------------------------
    def draw(self, n=1, rarity=None):
        """Draw ``n`` entries with replacement, in sequence."""
        self._validate_count(n)
        return [self._pick(rarity) for _ in range(n)]

    def draw_unique(self, n, rarity=None):
        """Draw ``n`` distinct entries, in sequence.

        The table itself is left untouched; the exclusion of already
        picked entries happens on a private copy of the weights.
        """
        self._validate_count(n)
        ids = self.pool(rarity)
        if n > len(ids):
            raise LootError("cannot draw %d distinct entries out of %d" % (n, len(ids)))
        weights = [self._weights[self._index[item_id]] for item_id in ids]
        picked = []
        for _ in range(n):
            position = self._weighted_index(weights)
            picked.append(ids[position])
            weights[position] = 0
            self._account(ids[position])
        return picked

    @staticmethod
    def _validate_count(n):
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise LootError("draw count must be a positive integer")

    def _pick(self, rarity=None):
        """One weighted pick, or the pity item when its streak is due."""
        if self._pity_item is not None and self._misses >= self._pity_threshold:
            self._misses = 0
            return self._pity_item
        ids = self.pool(rarity)
        weights = [self._weights[self._index[item_id]] for item_id in ids]
        item_id = ids[self._weighted_index(weights)]
        self._account(item_id)
        return item_id

    def _weighted_index(self, weights):
        """Index of one weighted pick over ``weights`` (one rng call)."""
        total = sum(weights)
        if total <= 0:
            raise LootError("the pool carries no weight")
        roll = self._rng.randrange(total)
        acc = 0
        for position, weight in enumerate(weights):
            acc += weight
            if roll < acc:
                return position
        raise LootError("weighted pick fell through the prefix sums")

    def _account(self, item_id):
        """Update the pity streak after a weighted pick."""
        if self._pity_item is None:
            return
        if self.rarity_of(item_id) in RARE_RARITIES:
            self._misses = 0
        else:
            self._misses += 1
