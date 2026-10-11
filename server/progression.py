"""Server-owned EXP math for the locked exp_v1 balance tables."""
from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path


MAX_CHARACTER_LEVEL = 60
BALANCE_VERSION = 'exp_v1'


@dataclass(frozen=True)
class LevelRow:
    level: int
    exp_to_next: int
    cumulative: int


@dataclass(frozen=True)
class GapRule:
    min_delta: int
    max_delta: int
    multiplier: Decimal


@dataclass(frozen=True)
class ExpView:
    level: int
    total_exp: int
    current_exp: int
    exp_to_next: int
    at_cap: bool


@dataclass
class Contribution:
    damage: int = 0
    last_hit_at: float = 0.0


class BalanceConfig:
    def __init__(self, levels, monster_base, gap_rules, version=BALANCE_VERSION):
        self.version = version
        self.levels = {row.level: row for row in levels}
        self.monster_base = dict(monster_base)
        self.gap_rules = tuple(gap_rules)
        if sorted(self.levels) != list(range(1, MAX_CHARACTER_LEVEL + 1)):
            raise ValueError('EXP balance must contain character levels 1 through 60')
        if sorted(self.monster_base) != list(range(1, MAX_CHARACTER_LEVEL + 1)):
            raise ValueError('EXP balance must contain monster levels 1 through 60')
        if self.levels[MAX_CHARACTER_LEVEL].exp_to_next != 0:
            raise ValueError('Level 60 must be capped')

    @classmethod
    def from_csv_directory(cls, directory):
        root = Path(directory)
        with (root / 'exp_v1_character_levels.csv').open(encoding='utf-8', newline='') as handle:
            level_rows = [
                LevelRow(
                    level=int(row['level']),
                    exp_to_next=int(row['exp_to_next_level']),
                    cumulative=int(row['cumulative_exp_to_reach_level']),
                )
                for row in csv.DictReader(handle)
                if row['balance_version'] == BALANCE_VERSION
            ]
        with (root / 'exp_v1_monster_base.csv').open(encoding='utf-8', newline='') as handle:
            monster_base = {
                int(row['monster_level']): int(row['base_exp'])
                for row in csv.DictReader(handle)
                if row['balance_version'] == BALANCE_VERSION
            }
        with (root / 'exp_v1_gap_rules.csv').open(encoding='utf-8', newline='') as handle:
            gap_rules = [
                GapRule(
                    min_delta=int(row['min_delta']),
                    max_delta=int(row['max_delta']),
                    multiplier=Decimal(row['exp_multiplier']),
                )
                for row in csv.DictReader(handle)
                if row['balance_version'] == BALANCE_VERSION
            ]
        return cls(level_rows, monster_base, gap_rules)

    @classmethod
    def from_supabase(cls, url, server_key, timeout=10):
        """Load the active read-only EXP tables through server-authenticated REST."""
        base = url.rstrip('/') + '/rest/v1/'
        headers = {
            'apikey': server_key,
            'Authorization': 'Bearer ' + server_key,
            'Accept': 'application/json',
        }

        def rows(table, columns, order):
            query = urllib.parse.urlencode({
                'balance_version': 'eq.' + BALANCE_VERSION,
                'select': columns,
                'order': order,
            })
            request = urllib.request.Request(base + table + '?' + query, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())

        levels = [
            LevelRow(int(row['level']), int(row['exp_to_next_level']), int(row['cumulative_exp_to_reach_level']))
            for row in rows('character_level_exp', 'level,exp_to_next_level,cumulative_exp_to_reach_level', 'level.asc')
        ]
        monster_base = {
            int(row['monster_level']): int(row['base_exp'])
            for row in rows('monster_level_base_exp', 'monster_level,base_exp', 'monster_level.asc')
        }
        gap_rules = [
            GapRule(int(row['min_delta']), int(row['max_delta']), Decimal(str(row['exp_multiplier'])))
            for row in rows('exp_level_gap_rules', 'min_delta,max_delta,exp_multiplier', 'min_delta.asc')
        ]
        return cls(levels, monster_base, gap_rules)

    @property
    def max_total_exp(self):
        return self.levels[MAX_CHARACTER_LEVEL].cumulative

    def clamp_total_exp(self, value):
        return max(0, min(int(value), self.max_total_exp))

    def view(self, total_exp):
        total = self.clamp_total_exp(total_exp)
        level = max(level for level, row in self.levels.items() if row.cumulative <= total)
        row = self.levels[level]
        if level >= MAX_CHARACTER_LEVEL:
            return ExpView(level, total, 0, 0, True)
        return ExpView(level, total, total - row.cumulative, row.exp_to_next, False)

    def kill_award(self, character_level, monster_level):
        character_level = max(1, min(MAX_CHARACTER_LEVEL, int(character_level)))
        monster_level = max(1, min(MAX_CHARACTER_LEVEL, int(monster_level)))
        if character_level >= MAX_CHARACTER_LEVEL:
            return 0
        delta = monster_level - character_level
        rule = next((rule for rule in self.gap_rules if rule.min_delta <= delta <= rule.max_delta), None)
        if rule is None:
            return 0
        raw = Decimal(self.monster_base[monster_level]) * rule.multiplier
        same_level_cap = Decimal(self.monster_base[character_level] * 2)
        return int(min(raw, same_level_cap).to_integral_value(rounding=ROUND_FLOOR))

    def apply_award(self, total_exp, award):
        return self.view(self.clamp_total_exp(int(total_exp) + max(0, int(award))))


def contribution_shares(contributions, monster_max_hp, now, minimum_fraction=Decimal('0.10'), recent_seconds=15.0):
    """Return bounded reward shares without multiplying a kill across helpers.

    Damage from every attacker remains in the denominator.  Only a player who did
    at least 10% of the monster's HP recently is eligible for a share.
    """
    total_damage = sum(max(0, int(item.damage)) for item in contributions.values())
    if total_damage <= 0:
        return {}
    minimum_damage = int((Decimal(monster_max_hp) * minimum_fraction).to_integral_value(rounding=ROUND_FLOOR))
    minimum_damage = max(1, minimum_damage)
    return {
        actor_id: Decimal(item.damage) / Decimal(total_damage)
        for actor_id, item in contributions.items()
        if item.damage >= minimum_damage and now - item.last_hit_at <= recent_seconds
    }


def scaled_award(base_award, share):
    return max(0, int((Decimal(base_award) * share).to_integral_value(rounding=ROUND_FLOOR)))
