"""Server-side Supabase access-token verification.

The token is sent in the first encrypted WebSocket message (never the URL).  The
Auth `/user` endpoint verifies both legacy HS256 and modern asymmetric projects,
so the game server never needs the JWT signing secret.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class AuthenticationError(Exception):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    user_id: str
    email: str
    expires_at: int


def _unverified_exp(access_token):
    """Read exp only after Auth has verified this same token."""
    try:
        payload = access_token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))['exp'])
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return 0


class SupabaseAuthVerifier:
    def __init__(self, url, publishable_key, timeout=8):
        self.url = url.rstrip('/')
        self.publishable_key = publishable_key
        self.timeout = timeout

    async def verify(self, access_token):
        return await asyncio.to_thread(self._verify_sync, access_token)

    def _verify_sync(self, access_token):
        request = urllib.request.Request(
            self.url + '/auth/v1/user',
            headers={
                'apikey': self.publishable_key,
                'Authorization': 'Bearer ' + access_token,
                'Accept': 'application/json',
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AuthenticationError('Supabase rejected or could not verify the access token') from exc
        user_id = payload.get('id')
        if not isinstance(user_id, str) or not user_id:
            raise AuthenticationError('Verified token did not contain a user id')
        expires_at = _unverified_exp(access_token)
        if expires_at <= int(time.time()):
            raise AuthenticationError('Access token expired')
        return VerifiedIdentity(user_id=user_id, email=str(payload.get('email') or ''), expires_at=expires_at)
