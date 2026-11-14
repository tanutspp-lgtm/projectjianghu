"""Medicine stacks and server-authoritative HP/SP use for roster characters."""
import math
import time

RECOVERY = {f'{resource}_{tier}': (resource, percent)
            for resource in ('hp', 'sp')
            for tier, percent in enumerate((20, 35, 50), start=1)}
ITEMS = set(RECOVERY) | {'cleanse_1', 'cleanse_2', 'cleanse_3', 'protect_a',
                         'protect_b', 'protect_c', 'attack', 'defense'}


def add_stack(bag, item, qty, capacity):
    result = list(bag)
    for index, row in enumerate(result):
        if row['item_id'] == item:
            result[index] = dict(row, count=row.get('count', 1) + qty)
            return result
    if len(result) >= capacity:
        raise ValueError('ช่องกระเป๋าไม่พอ ของยังอยู่ในจดหมาย')
    result.append(dict(uid='medicine-' + item, item_id=item, count=qty))
    return result


def consume(player, item, save):
    if not isinstance(item, str) or item not in RECOVERY:
        raise ValueError('ยังใช้ยาชนิดนี้ไม่ได้')
    resource, percent = RECOVERY[item]
    if player.dead or player.hp <= 0:
        raise ValueError('ตัวละครยังใช้ยาไม่ได้')
    now = time.monotonic()
    if now < player.medicine_ready.get(resource, 0):
        raise ValueError('รอสักครู่ก่อนใช้ยาซ้ำ')
    maximum = getattr(player, 'max_' + resource)
    before = getattr(player, resource)
    if before >= maximum:
        raise ValueError(resource.upper() + ' เต็มแล้ว')
    bag = list(player.inventory)
    for index, row in enumerate(bag):
        if row['item_id'] == item and row.get('count', 1) > 0:
            if row.get('count', 1) == 1:
                bag.pop(index)
            else:
                bag[index] = dict(row, count=row['count'] - 1)
            break
    else:
        raise ValueError('ยาหมดแล้ว')
    after = min(maximum, before + math.ceil(maximum * percent / 100))
    save(bag)
    player.inventory = bag
    player.inventory_revision += 1
    player.medicine_ready[resource] = now + 1.5
    setattr(player, resource, after)
    return dict(resource=resource, gained=max(1, round(after - before)))
