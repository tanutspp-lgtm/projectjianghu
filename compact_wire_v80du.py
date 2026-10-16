"""Jianghu v8.0DU opt-in lossless-for-current-wire AOI compact binary snapshots.

Game authority, AOI selection, snapshot cadence and delta baselines live in server.py.
This module ONLY changes the transport representation of an already-built snapshot.
No dependencies beyond stdlib. IDs and fixed-point values decode to the SAME JS
numbers / strings / booleans exposed by the legacy JSON snapshot.
"""
import json
import re
import struct
from functools import lru_cache

MAGIC = b'JHB1'
KINDS = ('players', 'mobs', 'shots', 'loot')
# Order is protocol-versioned. A single bit indicates that an attr is present.
BASE = (
    ('level','i'),('x','q2'),('y','q2'),('vx','q2'),('vy','q2'),
    ('face','i'),('hp','i'),('max','i'),('ground','b'),('guard','b'),
    ('down','q2'),('dead','q2'),('stun','q2'),('inv','q2'),
    ('climb','b'),('frame','i'),('action','s'),
)
SCHEMAS = {
    'players': BASE + (('lastAppliedSeq','i'),('avatar','s')),
    'mobs': BASE + (('defense','i'),('name','s'),('hum','b'),('species','s'),('biteAge','q3'),('spawnId','s')),
    'shots': (('kind','s'),('x','q1'),('y','q1'),('dir','i')),
    'loot': (('item_id','s'),('x','q2'),('y','q2'),('ownerId','s'),('privateFor','q1'),('expiresIn','q1')),
}
LOOKUPS = {k:{name:(i,typ) for i,(name,typ) in enumerate(fields)} for k,fields in SCHEMAS.items()}
HEX_ID = re.compile(r'^g-([0-9a-f]{16})$')
JSON = json.JSONEncoder(separators=(',',':'))


def uvar(number):
    n = int(number)
    if n < 0: raise ValueError('uvar cannot be negative')
    out = bytearray()
    while n >= 128:
        out.append((n & 127) | 128)
        n >>= 7
    out.append(n)
    return bytes(out)


def svar(n):
    n=int(n)
    return uvar(2*n if n>=0 else -2*n-1)


@lru_cache(maxsize=8192)
def text_bytes(s):
    data=s.encode('utf-8')
    return uvar(len(data))+data


def eid_bytes(value):
    value=str(value)
    m=HEX_ID.fullmatch(value)
    if m:
        return b'\x01'+bytes.fromhex(m.group(1))
    return b'\x00'+text_bytes(value)


def entity_bytes(kind, entry, cache=None):
    # Keys are (kind, dict identity), and value pins the referenced dict for
    # the lifetime of this one SharedSnapshot: no accidental reused-ID hits.
    key=(kind,id(entry))
    if cache is not None:
        hit=cache.get(key)
        if hit is not None and hit[0] is entry:return hit[1]
    schema=SCHEMAS[kind]
    allowed=LOOKUPS[kind]
    if any(key!='id' and key not in allowed for key in entry):
        raise ValueError('Unknown v80DU entity field in '+kind)
    mask=0
    payload=bytearray()
    for i,(name,typ) in enumerate(schema):
        if name not in entry:continue
        value=entry[name]
        mask|=1<<i
        if typ=='b':payload.append(1 if value else 0)
        elif typ=='i':payload.extend(svar(value))
        elif typ=='s':payload.extend(text_bytes(str(value)))
        elif typ[0]=='q':
            precision=10**int(typ[1:])
            scaled=round(float(value)*precision)
            # These are already rounded by actor_json/snapshot(). Quantization
            # never discards additional position precision beyond legacy wire.
            if abs(float(value)-scaled/precision)>1e-7:
                raise ValueError('Unexpected precision in '+name)
            payload.extend(svar(scaled))
        else:raise AssertionError(typ)
    packed=eid_bytes(entry['id']) + uvar(mask) + payload
    if cache is not None:cache[key]=(entry,packed)
    return packed


def encode_snapshot(packet, cache=None):
    if packet.get('t')!='snapshot':raise ValueError('Only snapshots are packed')
    # Meta remains standard JSON to preserve nested event/self/inventory wire
    # without changing game semantics, combat or mutable private progression.
    meta={k:v for k,v in packet.items() if k not in KINDS}
    mb=JSON.encode(meta).encode('utf-8')
    out=bytearray(MAGIC)
    out.extend(struct.pack('<I',len(mb)))
    out.extend(mb)
    for kind in KINDS:
        entries=packet.get(kind,())
        out.extend(uvar(len(entries)))
        for entry in entries:
            out.extend(entity_bytes(kind,entry,cache))
    return bytes(out)
