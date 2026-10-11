"""Shared wire-contract validation for the v7.9N browser/server protocol.

The browser is untrusted.  Keep accepted messages deliberately small and exact so
new UI fields can never become accidental gameplay authority.
"""
from dataclasses import dataclass
from typing import Optional


COLORS = frozenset({'black', 'white', 'brown', 'red', 'gold'})
ACTION_NAMES = frozenset({'jump', 'dash', 'attack', 'aoe', 'break', 'lock'})
ALLOWED_BUTTONS = 1 | 2 | 4 | 8 | 16
MAX_ACCESS_TOKEN_LENGTH = 12_000


def valid_avatar(value):
    if not isinstance(value, str) or len(value) > 24:
        return False
    bits = value.split('_')
    return (
        len(bits) == 4
        and bits[0] in ('male', 'female')
        and bits[1] == 'hair'
        and bits[2] in ('01', '02', '03')
        and bits[3] in COLORS
    )


def valid_character_name(value):
    if not isinstance(value, str):
        return False
    clean = value.strip()
    return 2 <= len(clean) <= 24 and all(ord(ch) >= 32 for ch in clean)


@dataclass(frozen=True)
class JoinRequest:
    avatar: str
    resume: Optional[str]
    access_token: Optional[str]
    character_name: Optional[str]

    @property
    def authenticated(self):
        return self.access_token is not None


def parse_join(message):
    """Return a normalized join request or ``None`` for any unknown shape."""
    if not isinstance(message, dict) or message.get('t') != 'join':
        return None
    allowed = {'t', 'avatar', 'resume', 'auth', 'character_name'}
    if set(message) - allowed or not valid_avatar(message.get('avatar')):
        return None

    resume = message.get('resume')
    if resume is not None and (
        not isinstance(resume, str) or not 20 <= len(resume) <= 128
    ):
        return None

    auth = message.get('auth')
    access_token = None
    character_name = message.get('character_name')
    if auth is not None:
        if set(message) - allowed or not isinstance(auth, dict) or set(auth) != {'access_token'}:
            return None
        access_token = auth.get('access_token')
        if (
            not isinstance(access_token, str)
            or not 20 <= len(access_token) <= MAX_ACCESS_TOKEN_LENGTH
        ):
            return None
        if character_name is not None and not valid_character_name(character_name):
            return None
    elif character_name is not None:
        return None

    return JoinRequest(
        avatar=message['avatar'],
        resume=resume,
        access_token=access_token,
        character_name=character_name.strip() if character_name else None,
    )


def parse_auth_refresh(message):
    if not isinstance(message, dict) or set(message) != {'t', 'access_token'}:
        return None
    if message.get('t') != 'auth_refresh':
        return None
    token = message.get('access_token')
    if not isinstance(token, str) or not 20 <= len(token) <= MAX_ACCESS_TOKEN_LENGTH:
        return None
    return token


def parse_input(message, last_seq):
    if not isinstance(message, dict) or set(message) != {'t', 'seq', 'buttons', 'pressed'}:
        return None
    if message.get('t') != 'input':
        return None
    seq, buttons, pressed = message.get('seq'), message.get('buttons'), message.get('pressed')
    if (
        type(seq) is not int
        or seq <= last_seq
        or seq < 0
        or seq > 2**53
        or type(buttons) is not int
        or buttons < 0
        or buttons & ~ALLOWED_BUTTONS
    ):
        return None
    if (
        not isinstance(pressed, list)
        or len(pressed) > 4
        or any(action not in ACTION_NAMES for action in pressed)
        or len(set(pressed)) != len(pressed)
    ):
        return None
    return seq, buttons, pressed
