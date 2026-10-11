"""Local durable character, idempotent reward, relog and restart checks."""
import asyncio
import tempfile
from pathlib import Path

from persistence import LocalSqliteStore, PersistenceError
from progression import BalanceConfig


async def suite():
    balance = BalanceConfig.from_csv_directory(Path(__file__).parent.parent / 'database')
    with tempfile.TemporaryDirectory() as temp:
        database = Path(temp) / 'characters.sqlite3'
        store = LocalSqliteStore(database, balance)
        first = await store.load_or_create_character('user-a', 'female_hair_02_red', 'หลินอิง')
        assert (first.level, first.total_exp, first.avatar) == (1, 0, 'female_hair_02_red')
        levelled = await store.award_exp('user-a', first.character_id, 'event-0001', 6960)
        assert (levelled.level, levelled.total_exp, levelled.applied) == (3, 6960, True), levelled
        duplicate = await store.award_exp('user-a', first.character_id, 'event-0001', 6960)
        assert (duplicate.level, duplicate.total_exp, duplicate.applied) == (3, 6960, False), duplicate

        restarted = LocalSqliteStore(database, balance)
        relogged = await restarted.load_or_create_character('user-a', 'male_hair_01_gold', 'เปลี่ยนไม่ได้')
        assert relogged.character_id == first.character_id
        assert (relogged.level, relogged.total_exp, relogged.avatar, relogged.name) == (
            3, 6960, 'female_hair_02_red', 'หลินอิง'
        )
        try:
            await restarted.award_exp('user-b', first.character_id, 'event-0002', 25)
        except PersistenceError:
            pass
        else:
            raise AssertionError('cross-account character award was accepted')
    print('PERSISTENCE TESTS PASSED: create/load, relog, restart, idempotency, ownership')


if __name__ == '__main__':
    asyncio.run(suite())
