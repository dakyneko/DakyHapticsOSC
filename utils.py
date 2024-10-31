#!/usr/bin/env python3

def remap(v, in1, in2, out1, out2, clamp=False):
    din = in2 - in1
    dout = out2 - out1
    v = dout*(v - in1)/din + out1
    if clamp: v = min(out2, max(out1, v))
    return v

def remap_clamp(v, in1, in2, out1, out2):
    return remap(v, in1, in2, out1, out2, clamp=True)

def clamp(v, min_, max_):
    return max(min_, min(max_, v))
