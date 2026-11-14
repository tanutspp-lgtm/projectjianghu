"""Server-owned character progression. Serialize writes and resolve lost HTTP replies."""
import asyncio
import http.client
import json
import os
from urllib.parse import urlencode

from roster_admission import PROJECT_HOST

DETAIL_FIELDS = ('stat_points', 'skill_points', 'total_kills', 'stats', 'skill_ranks')
SELECT = 'level,exp,progress_details,progress_revision'
pending = {}
jobs = {}
locks = {}


class ProgressUnavailable(Exception):
    pass


class ProgressConflict(ProgressUnavailable):
    pass


def request(method, filters, payload=None):
    key = os.environ.get('SW_PROGRESS_API_KEY')
    if not key:
        raise ProgressUnavailable('missing SW_PROGRESS_API_KEY')
    headers = {'apikey': key, 'Accept': 'application/json'}
    if not key.startswith('sb_secret_'):
        headers['Authorization'] = 'Bearer ' + key
    if payload is not None:
        headers.update({'Content-Type': 'application/json', 'Prefer': 'return=representation'})
    conn = http.client.HTTPSConnection(PROJECT_HOST, timeout=5)
    try:
        conn.request(method, '/rest/v1/sw_characters?' + urlencode(dict(filters, select=SELECT)),
                     None if payload is None else json.dumps(payload), headers)
        response = conn.getresponse()
        data = response.read(16385)
        if response.status != 200 or len(data) > 16384:
            raise ProgressUnavailable('progress store status ' + str(response.status))
        rows = json.loads(data)
        if not isinstance(rows, list) or len(rows) > 1:
            raise ProgressUnavailable('invalid progress response')
        return rows
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise ProgressUnavailable('progress store unavailable') from exc
    finally:
        conn.close()


def read(character):
    rows = request('GET', {'id': 'eq.' + character})
    if not rows:
        raise ProgressUnavailable('character unavailable')
    return rows[0]


def write(character, revision, state):
    payload = dict(state, progress_revision=revision + 1)
    rows = request('PATCH', {'id': 'eq.' + character, 'progress_revision': 'eq.' + str(revision)}, payload)
    if not rows:
        # A committed PATCH may have lost its response. Accept only that exact snapshot.
        if read(character) != payload:
            raise ProgressConflict('progress changed in another session')


def snapshot(p):
    return {'level': p.level, 'exp': p.exp, 'progress_details': {
        name: getattr(p, name).copy() if isinstance(getattr(p, name), dict) else getattr(p, name)
        for name in DETAIL_FIELDS} | {'taels': p.taels} | ({'location': p.saved_location} if getattr(p, 'saved_location', None) else {})}


def restore(p, row):
    p.level = row['level']
    p.exp = row['exp']
    details = row['progress_details']
    p.taels = (details or {}).get('taels', 0)
    if details:
        for field in DETAIL_FIELDS:
            setattr(p, field, details[field])
    else:
        # Existing roster rows may already have levels but no allocation history.
        p.stat_points = 3 * (p.level - 1)
        p.skill_points = p.level - 1
    p.progress_revision = row['progress_revision']
    p.saved_progress = snapshot(p)


async def flush(character):
    lock = locks.setdefault(character, asyncio.Lock())
    async with lock:
        while character in pending:
            p = pending[character]
            state = snapshot(p)
            if state != p.saved_progress:
                try:
                    await asyncio.to_thread(write, character, p.progress_revision, state)
                except ProgressConflict:
                    # The newer DB revision owns the character. End this stale session.
                    pending.pop(character, None)
                    p.progress_conflict = True
                    await p.ws.close(code=1013, reason='Character progress changed')
                    raise
                p.progress_revision += 1
                p.saved_progress = state
            if state == snapshot(p):
                pending.pop(character, None)


async def drain(character):
    delay = 0.25
    try:
        while character in pending:
            await asyncio.sleep(delay)
            try:
                await flush(character)
            except ProgressConflict:
                return
            except ProgressUnavailable as exc:
                print('Character progress retry:', str(exc), flush=True)
                delay = min(20, max(1, delay * 2))
    finally:
        jobs.pop(character, None)
        if character not in pending:
            locks.pop(character, None)


def changed(p):
    character = getattr(p, 'roster_id', None)
    if character and not getattr(p, 'progress_conflict', False):
        pending[character] = p
        if character not in jobs:
            jobs[character] = asyncio.create_task(drain(character))


async def load(character):
    if character in pending:
        await flush(character)
    return await asyncio.to_thread(read, character)
