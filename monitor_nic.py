#!/usr/bin/env python3
"""Read external NIC TX/RX byte counters; captures TLS/Caddy egress, no dependencies."""
from pathlib import Path
import argparse,time

def default_iface():
    try:
        for line in Path('/proc/net/route').read_text().splitlines()[1:]:
            v=line.split()
            if len(v)>1 and v[1]=='00000000' and (int(v[3],16)&1):return v[0]
    except (OSError,ValueError):pass
    return None

def get(iface):
    p=Path('/sys/class/net')/iface/'statistics'
    return int((p/'tx_bytes').read_text()),int((p/'rx_bytes').read_text())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Hostatom real NIC Mbps, includes Caddy TLS and SSH')
    parser.add_argument('--iface',default=None,help='NIC name (auto-detects default route)')
    parser.add_argument('--seconds',type=int,default=30)
    parser.add_argument('--interval',type=int,default=5)
    args=parser.parse_args()
    iface=args.iface or default_iface()
    if not iface:raise SystemExit('Cannot detect NIC. Specify --iface after checking: ip route')
    if args.seconds<1 or args.interval<1:raise SystemExit('seconds and interval must be positive')
    print(f'External NIC: {iface} | measuring {args.seconds}s | sample interval {args.interval}s',flush=True)
    tx,rx=get(iface); t=time.monotonic(); remaining=args.seconds; total_tx=0; total_rx=0
    while remaining:
        time.sleep(min(args.interval,remaining))
        t2=time.monotonic();tx2,rx2=get(iface)
        secs=max(.001,t2-t); dx=max(0,tx2-tx); dr=max(0,rx2-rx)
        total_tx+=dx;total_rx+=dr
        print(f'TX {dx*8/1e6/secs:.2f} Mbps ({dx/1024**2/secs:.2f} MiB/s) | RX {dr*8/1e6/secs:.2f} Mbps',flush=True)
        tx,rx,t=tx2,rx2,t2;remaining=max(0,remaining-args.interval)
    print(f'TOTAL TX {total_tx/1024**2:.1f} MiB | RX {total_rx/1024**2:.1f} MiB',flush=True)
