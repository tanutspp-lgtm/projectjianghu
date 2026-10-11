"""Durable character stores for local tests and Supabase production wiring."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from progression import BalanceConfig


class PersistenceError(Exception):
    pass


@dataclass(frozen=True)
class CharacterRecord:
    character_id: str
    user_id: str
    name: str
    avatar: str
    level: int
    total_exp: int
    balance_version: str
    applied: bool = True


class LocalSqliteStore:
    """Small durable adapter used for local development and restart tests."""

    def __init__(self, path, balance: BalanceConfig):
        self.path = str(Path(path))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.balance = balance
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute('pragma foreign_keys = on')
        return connection

    def _initialize(self):
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                create table if not exists characters (
                    id text primary key,
                    user_id text not null unique,
                    name text not null,
                    avatar text not null,
                    level integer not null,
                    total_exp integer not null,
                    balance_version text not null,
                    updated_at text not null default current_timestamp
                );
                create table if not exists character_exp_ledger (
                    reward_event_id text not null,
                    character_id text not null references characters(id) on delete cascade,
                    amount integer not null check (amount >= 0),
                    created_at text not null default current_timestamp,
                    primary key (reward_event_id, character_id)
                );
                """
            )
            connection.commit()

    @staticmethod
    def _record(row, applied=True):
        return CharacterRecord(
            character_id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            avatar=row['avatar'],
            level=int(row['level']),
            total_exp=int(row['total_exp']),
            balance_version=row['balance_version'],
            applied=applied,
        )

    async def load_or_create_character(self, user_id, avatar, name):
        return await asyncio.to_thread(self._load_or_create_sync, user_id, avatar, name)

    def _load_or_create_sync(self, user_id, avatar, name):
        with self._lock, closing(self._connect()) as connection:
            connection.execute('begin immediate')
            row = connection.execute('select * from characters where user_id = ?', (user_id,)).fetchone()
            if row is None:
                character_id = str(uuid.uuid4())
                connection.execute(
                    'insert into characters(id,user_id,name,avatar,level,total_exp,balance_version) values (?,?,?,?,1,0,?)',
                    (character_id, user_id, name, avatar, self.balance.version),
                )
                row = connection.execute('select * from characters where id = ?', (character_id,)).fetchone()
            connection.commit()
            return self._record(row)

    async def award_exp(self, user_id, character_id, reward_event_id, amount):
        return await asyncio.to_thread(
            self._award_exp_sync, user_id, character_id, reward_event_id, int(amount)
        )

    def _award_exp_sync(self, user_id, character_id, reward_event_id, amount):
        if amount < 0:
            raise PersistenceError('Negative EXP is not allowed')
        with self._lock, closing(self._connect()) as connection:
            connection.execute('begin immediate')
            row = connection.execute(
                'select * from characters where id = ? and user_id = ?',
                (character_id, user_id),
            ).fetchone()
            if row is None:
                raise PersistenceError('Character ownership mismatch')
            inserted = connection.execute(
                'insert or ignore into character_exp_ledger(reward_event_id,character_id,amount) values (?,?,?)',
                (reward_event_id, character_id, amount),
            ).rowcount == 1
            if inserted and amount:
                view = self.balance.apply_award(row['total_exp'], amount)
                connection.execute(
                    'update characters set level=?, total_exp=?, updated_at=current_timestamp where id=? and user_id=?',
                    (view.level, view.total_exp, character_id, user_id),
                )
            row = connection.execute('select * from characters where id = ?', (character_id,)).fetchone()
            connection.commit()
            return self._record(row, applied=inserted)


class SupabaseRestStore:
    """Server-only PostgREST adapter.  The secret key never reaches the browser."""

    def __init__(self, url, secret_key, balance: BalanceConfig, timeout=10):
        self.url = url.rstrip('/')
        self.secret_key = secret_key
        self.balance = balance
        self.timeout = timeout

    def _request_sync(self, method, path, body=None, prefer=None):
        data = None if body is None else json.dumps(body).encode('utf-8')
        headers = {
            'apikey': self.secret_key,
            'Authorization': 'Bearer ' + self.secret_key,
            'Accept': 'application/json',
        }
        if data is not None:
            headers['Content-Type'] = 'application/json'
        if prefer:
            headers['Prefer'] = prefer
        request = urllib.request.Request(self.url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise PersistenceError('Supabase persistence request failed') from exc

    async def load_or_create_character(self, user_id, avatar, name):
        return await asyncio.to_thread(self._load_or_create_sync, user_id, avatar, name)

    def _load_or_create_sync(self, user_id, avatar, name):
        query = urllib.parse.urlencode({
            'user_id': 'eq.' + user_id,
            'select': 'id,user_id,name,avatar,level,total_exp,balance_version',
            'limit': '1',
        })
        rows = self._request_sync('GET', '/rest/v1/characters?' + query)
        if not rows:
            rows = self._request_sync(
                'POST',
                '/rest/v1/characters?on_conflict=user_id&select=id,user_id,name,avatar,level,total_exp,balance_version',
                {'user_id': user_id, 'name': name, 'avatar': avatar, 'balance_version': self.balance.version},
                'resolution=ignore-duplicates,return=representation',
            )
        if not rows:
            rows = self._request_sync('GET', '/rest/v1/characters?' + query)
        if not rows:
            raise PersistenceError('Supabase did not return a character')
        return self._record(rows[0])

    async def award_exp(self, user_id, character_id, reward_event_id, amount):
        return await asyncio.to_thread(
            self._award_exp_sync, user_id, character_id, reward_event_id, int(amount)
        )

    def _award_exp_sync(self, user_id, character_id, reward_event_id, amount):
        rows = self._request_sync(
            'POST',
            '/rest/v1/rpc/award_character_exp',
            {
                'p_user_id': user_id,
                'p_character_id': character_id,
                'p_reward_event_id': reward_event_id,
                'p_amount': amount,
                'p_balance_version': self.balance.version,
            },
        )
        if isinstance(rows, dict):
            row = rows
        elif isinstance(rows, list) and rows:
            row = rows[0]
        else:
            raise PersistenceError('Supabase EXP transaction returned no character')
        return self._record(row, applied=bool(row.get('applied', True)))

    @staticmethod
    def _record(row, applied=True):
        return CharacterRecord(
            character_id=str(row['id']),
            user_id=str(row['user_id']),
            name=str(row['name']),
            avatar=str(row['avatar']),
            level=int(row['level']),
            total_exp=int(row['total_exp']),
            balance_version=str(row['balance_version']),
            applied=applied,
        )


def build_store_from_environment(environment, balance):
    url = environment.get('SUPABASE_URL', '').strip()
    secret = (
        environment.get('SUPABASE_SECRET_KEY', '').strip()
        or environment.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    )
    if url and secret:
        return SupabaseRestStore(url, secret, balance)
    local_path = environment.get('LOCAL_DATABASE_PATH', '').strip()
    if local_path:
        return LocalSqliteStore(local_path, balance)
    return None
