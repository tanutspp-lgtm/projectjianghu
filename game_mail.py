"""Character mail and reward receipts on the single Hostatom game host."""
import argparse
import json
import os
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from owned_equipment_v215 import CAPACITY, CAT

PAGE = 20
SCHEMA = """
CREATE TABLE IF NOT EXISTS mail (
 id INTEGER PRIMARY KEY, recipient TEXT NOT NULL, subject TEXT NOT NULL,
 body TEXT NOT NULL, item TEXT, quantity INTEGER NOT NULL, sent INTEGER NOT NULL,
 opened INTEGER NOT NULL DEFAULT 0, claimed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS mail_recipient ON mail(recipient, id DESC);
CREATE TABLE IF NOT EXISTS reward_inventory (
 recipient TEXT PRIMARY KEY, bag TEXT NOT NULL, gear TEXT NOT NULL
);
"""


def connect():
    path = Path(os.environ.get('SW_MAIL_DB') or Path(__file__).with_name('data') / 'mail.sqlite3')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    return sqlite3.connect(path, timeout=2)


def initialize():
    with closing(connect()) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript(SCHEMA)


@contextmanager
def transaction():
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        yield db


def deliver(recipient, subject, body, item=None, quantity=1):
    recipient = str(UUID(recipient))
    if not (subject.strip() and len(subject) <= 100 and body.strip() and len(body) <= 2000):
        raise ValueError('กรอกหัวข้อ 1–100 และข้อความ 1–2000 ตัวอักษร')
    if item is not None and (item not in CAT or not 1 <= quantity <= CAPACITY):
        raise ValueError('รหัสไอเทมหรือจำนวนไม่ถูกต้อง')
    with transaction() as db:
        return db.execute('INSERT INTO mail(recipient,subject,body,item,quantity,sent) VALUES(?,?,?,?,?,?)',
                          (recipient, subject.strip(), body.strip(), item, quantity if item else 0, int(time.time()))).lastrowid


def counts(db, who):
    return db.execute('SELECT count(*), count(CASE WHEN opened=0 THEN 1 END) FROM mail WHERE recipient=?', (who,)).fetchone()


def inbox(who, offset=0, summary=False):
    with closing(connect()) as db, db:
        db.execute('BEGIN')
        total, unread = counts(db, who)
        page = {'total': total, 'unread': unread}
        if summary:
            return page
        offset = min(offset, max(0, (total-1)//PAGE)*PAGE)
        db.row_factory = sqlite3.Row
        page.update(offset=offset, rows=[dict(r) for r in db.execute(
            'SELECT id,subject,body,item,quantity,sent,opened,claimed FROM mail WHERE recipient=? ORDER BY id DESC LIMIT ? OFFSET ?',
            (who, PAGE, offset))])
        return page


def restore(p):
    with closing(connect()) as db:
        row = db.execute('SELECT bag,gear FROM reward_inventory WHERE recipient=?',(p.roster_id,)).fetchone()
    if row:
        p.inventory, p.owned_equipment215 = map(json.loads,row)
        p.inventory_revision += 1
        p.equipment_revision215 += 1
    p.has_mail_inventory = bool(row)


def save_inventory(db, who, bag, gear):
    db.execute('INSERT INTO reward_inventory VALUES(?,?,?) ON CONFLICT(recipient) DO UPDATE SET bag=excluded.bag,gear=excluded.gear',
               (who, json.dumps(bag), json.dumps(gear)))


def claim(p, mid):
    with transaction() as db:
        row = db.execute('SELECT item,quantity,claimed FROM mail WHERE recipient=? AND id=?',(p.roster_id,mid)).fetchone()
        if not row or not row[0]:
            raise ValueError('ไม่มีของแนบให้รับ')
        item, qty, claimed = row
        if claimed:
            return 'รับของไปแล้ว'
        if item not in CAT:
            raise ValueError('ไม่พบไอเทมในระบบ กรุณาติดต่อ GM')
        if len(p.inventory) + qty > CAPACITY:
            raise ValueError('ช่องกระเป๋าไม่พอ ของยังอยู่ในจดหมาย')
        bag = p.inventory + [dict(uid='mail-'+uuid4().hex, item_id=item, obtainedAt=int(time.time()*1000)) for _ in range(qty)]
        save_inventory(db, p.roster_id, bag, p.owned_equipment215)
        db.execute('UPDATE mail SET opened=1,claimed=1 WHERE id=?',(mid,))
    p.inventory = bag
    p.inventory_revision += 1
    p.has_mail_inventory = True
    return 'รับของเข้ากระเป๋าแล้ว'


def command(p, msg):
    action = msg.get('action')
    offset = msg.get('offset',0)
    if type(offset) is not int or offset < 0 or offset > 2**31:
        raise ValueError('หน้าไม่ถูกต้อง')
    mid = msg.get('id')
    if action in ('read','claim') and (type(mid) is not int or not 0 < mid < 2**63):
        raise ValueError('ไม่พบจดหมาย')
    who = p.roster_id
    message = ''
    if action == 'claim':
        message = claim(p, mid)
    elif action == 'read':
        with transaction() as db:
            db.execute('UPDATE mail SET opened=1 WHERE recipient=? AND id=?',(who,mid))
    elif action == 'delete_read':
        with transaction() as db:
            n = db.execute('DELETE FROM mail WHERE recipient=? AND opened=1 AND (item IS NULL OR claimed=1)',(who,)).rowcount
        message = f'ลบจดหมายแล้ว {n} ฉบับ'
    elif action not in ('list','count'):
        raise ValueError('คำสั่งไม่ถูกต้อง')
    return dict(inbox(who, offset, action=='count'), message=message)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description='ส่งจดหมายจาก GM ตาม UUID ตัวละคร รองรับตัวละครออฟไลน์')
    for key in ('character','subject','body'):
        cli.add_argument('--'+key,required=True)
    cli.add_argument('--item', help='item_id ตามแคตตาล็อกอาวุธและชุดเกราะ')
    cli.add_argument('--quantity', type=int, default=1)
    args = cli.parse_args()
    initialize()
    print('ส่งจดหมายหมายเลข', deliver(args.character,args.subject,args.body,args.item,args.quantity))
