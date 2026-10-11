"""Protocol boundary tests for account joins and client-side reward injection."""
from protocol import parse_auth_refresh, parse_input, parse_join


def run():
    token = 'x' * 64
    join = parse_join({
        't': 'join',
        'avatar': 'male_hair_01_black',
        'auth': {'access_token': token},
        'character_name': 'เมฆา',
    })
    assert join and join.authenticated and join.access_token == token
    assert parse_join({'t': 'join', 'avatar': 'male_hair_01_black', 'exp': 999999}) is None
    assert parse_join({'t': 'join', 'avatar': 'male_hair_01_black', 'auth': {'access_token': token, 'role': 'admin'}}) is None
    assert parse_input({'t': 'input', 'seq': 1, 'buttons': 0, 'pressed': [], 'level': 60}, -1) is None
    assert parse_auth_refresh({'t': 'auth_refresh', 'access_token': token}) == token
    assert parse_auth_refresh({'t': 'auth_refresh', 'access_token': token, 'user_id': 'other'}) is None
    print('PROTOCOL TESTS PASSED: exact account shapes and progression injection rejection')


if __name__ == '__main__':
    run()
