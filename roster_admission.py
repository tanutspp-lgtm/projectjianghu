"""Resolve online character identity using the player's Supabase session and row policies."""
import http.client
import json
import os
import re
from urllib.parse import urlencode
from uuid import UUID

PROJECT_HOST = 'uxxkyptoocbswedwizct.supabase.co'
PUBLIC_KEY = 'sb_publishable_GDhK1Y-OrFCwzWRunfc-UQ_56NeDD4M'
TERMS_VERSION = 'sw-3'
WEAPONS = {'jian', 'tang', 'healer', 'flute'}
HAIR_STYLES = {'male', 'female'}
TOKEN_FORMAT = re.compile(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')

class Denied(Exception):
    pass

class Unavailable(Exception):
    pass

def canonical_id(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False

def read_json(conn, path, headers):
    conn.request('GET', path, headers=headers)
    response = conn.getresponse()
    payload = response.read(65537)
    if response.status == 401:
        raise Denied()
    if response.status != 200 or len(payload) > 65536:
        raise Unavailable()
    return json.loads(payload)

def resolve(character_id, token):
    if not canonical_id(character_id) or not isinstance(token, str) or len(token) > 12000 or not TOKEN_FORMAT.fullmatch(token):
        raise Denied()
    # HTTPSConnection never forwards an Authorization header to a redirect location.
    conn = http.client.HTTPSConnection(PROJECT_HOST, timeout=4)
    headers = {'apikey': os.environ.get('SUPABASE_PUBLISHABLE_KEY') or PUBLIC_KEY,
               'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}
    try:
        user = read_json(conn, '/auth/v1/user', headers)
        owner_id = user.get('id') if isinstance(user, dict) else None
        if not canonical_id(owner_id):
            raise Denied()
        owner = 'eq.' + owner_id
        terms = read_json(conn, '/rest/v1/sw_terms_acceptances?' + urlencode({
            'select':'version', 'owner_id':owner, 'version':'eq.' + TERMS_VERSION, 'limit':'1'}), headers)
        if terms != [{'version':TERMS_VERSION}]:
            raise Denied()
        rows = read_json(conn, '/rest/v1/sw_characters?' + urlencode({
            'select':'id,owner_id,name,weapon,hair', 'owner_id':owner, 'id':'eq.' + character_id, 'limit':'1'}), headers)
        if not isinstance(rows, list) or len(rows) != 1:
            raise Denied()
        row = rows[0]
        if (row.get('id') != character_id or row.get('owner_id') != owner_id
            or row.get('weapon') not in WEAPONS or row.get('hair') not in HAIR_STYLES
            or not isinstance(row.get('name'), str) or not row['name']):
            raise Denied()
        return {'id':character_id, 'name':row['name'], 'avatar':row['weapon']+'_'+row['hair']}
    except (OSError, http.client.HTTPException, ValueError, TypeError, AttributeError):
        raise Unavailable() from None
    finally:
        conn.close()
