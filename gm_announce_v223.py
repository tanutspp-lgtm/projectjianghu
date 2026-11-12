"""Local GM announcements. Run the CLI as the user that owns the game service."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
import time


def announcement(text):
    if not isinstance(text,str) or not 1 <= len(text.strip()) <= 240 or any(ord(c)<32 for c in text):
        raise ValueError('ใช้ข้อความบรรทัดเดียว ความยาว 1–240 ตัวอักษร')
    return text.strip()


def directory(port):
    override = os.environ.get('JIANGHU_GM_DIR')
    path = Path(override) if override else Path('/var/tmp' if os.name=='posix' else tempfile.gettempdir()) / f'jianghu-gm-{getattr(os,"getuid",lambda:0)()}-{port}'
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or (os.name=='posix' and (info.st_uid!=os.getuid() or info.st_mode&0o077)):
        raise PermissionError('โฟลเดอร์ประกาศต้องเป็นของผู้ใช้บริการเกมและมีสิทธิ์ 0700')
    return path


def enqueue(port,text):
    text=announcement(text)
    path=directory(port)
    final=path/f'{time.time_ns()}-{secrets.token_hex(6)}.json'
    with tempfile.NamedTemporaryFile(dir=path,mode='w',encoding='utf-8',delete=False) as file:
        tmp=Path(file.name)
        try:
            json.dump({'text':text,'until':time.time()+60},file,ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp,final)
    finally:
        tmp.unlink(missing_ok=True)


async def drain(path,publish):
    for item in sorted(path.glob('*.json'))[:32]:
        try:
            packet=json.loads(item.read_text(encoding='utf-8'))
            if packet['until']>time.time():
                await publish(announcement(packet['text']))
        except (ValueError,KeyError,TypeError,FileNotFoundError):
            pass
        item.unlink(missing_ok=True)


async def listen(port,publish):
    path=directory(port)
    while True:
        await drain(path,publish)
        await asyncio.sleep(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='ประกาศถึงผู้เล่นออนไลน์ทุกแมพและทุกแชนแนล')
    parser.add_argument('text')
    parser.add_argument('--port',type=int,default=int(os.getenv('PORT',8765)))
    args=parser.parse_args()
    try:
        enqueue(args.port,args.text)
    except (OSError,ValueError) as error:
        parser.exit(1,f'ส่งไม่สำเร็จ ({error})\n')
    print('เข้าคิวประกาศแล้ว')
