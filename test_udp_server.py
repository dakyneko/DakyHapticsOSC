#!/usr/bin/env python3
import socket
from struct import unpack
from collections import defaultdict
from types import SimpleNamespace as N

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('localhost', 1337))
print(f"listening: {sock}")

infos = defaultdict(lambda: N(last=0, max=0))

def v_str_scale(v): return round(v / 5)
def str_sub(s, idx, c):
    assert len(s) > idx
    return s[:idx] + str(c) + s[idx+1:]
strength_str_len = 51

while True:
    data, addr = sock.recvfrom(4096)

    if data.startswith(b'B'):
        _, addr, v = unpack('<cBB', data)
        i = infos[addr]
        i.max = max(v, i.max)
        v_str_scaled = v_str_scale(v)
        strength_str = ('*'*v_str_scaled) + (' '*(strength_str_len - v_str_scaled + 1))
        strength_str = str_sub(strength_str, v_str_scale(i.max), '>')
        print(f"actuate #{addr: 2d}: {v: 3d} |{strength_str}|")
        i.last = v

    else:
        print(f"Received message from {addr}: {data}")
