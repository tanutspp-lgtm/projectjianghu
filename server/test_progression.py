"""Exact exp_v1 boundaries, gap rules, assistance and large-integer checks."""
import time
from decimal import Decimal
from pathlib import Path

from progression import BalanceConfig, Contribution, contribution_shares, scaled_award


BALANCE = BalanceConfig.from_csv_directory(Path(__file__).parent.parent / 'database')


def run():
    assert BALANCE.view(0).level == 1
    assert BALANCE.view(2999).level == 1
    assert BALANCE.view(3000).level == 2
    assert BALANCE.apply_award(2999, 1).level == 2
    multi = BALANCE.apply_award(2999, 9040)
    assert (multi.level, multi.total_exp) == (4, 12039), multi
    capped = BALANCE.apply_award(237308584, 10**30)
    assert (capped.level, capped.total_exp, capped.at_cap) == (60, 237308585, True), capped
    assert BALANCE.kill_award(1, 17) == 0
    assert BALANCE.kill_award(1, 11) == 50  # +10 raw reward is capped at 2x same-level base.
    assert BALANCE.kill_award(22, 1) == 2   # 25 * 10%, floored.

    now = time.monotonic()
    shares = contribution_shares(
        {
            'main': Contribution(405, now),
            'tap': Contribution(45, now),
        },
        450,
        now,
    )
    assert shares == {'main': Decimal('0.9'), 'tap': Decimal('0.1')}, shares
    assert scaled_award(25, shares['main']) == 22
    stale = contribution_shares({'old': Contribution(450, now - 16)}, 450, now)
    assert stale == {}
    print('PROGRESSION TESTS PASSED: exact boundaries, cap, gap rules, contribution shares')


if __name__ == '__main__':
    run()
