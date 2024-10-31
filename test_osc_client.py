#!/usr/bin/env python3

from pythonosc.udp_client import SimpleUDPClient


ip = "127.0.0.1"
port = 9001
prefix = '/avatar/parameters/haptX-'

client = SimpleUDPClient(ip, port)  # Create client

def send(name, value):
    client.send_message(prefix + name, value)
