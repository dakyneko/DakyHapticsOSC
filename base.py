#!/usr/bin/env python3
from utils import *
import socket, logging as log, asyncio, serial_asyncio
from struct import unpack, pack
from time import time
from collections import defaultdict
from math import sqrt
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
from types import SimpleNamespace as N
from serial import Serial
from serial.tools.list_ports import comports as serial_ports
from random import random
from dataclasses import dataclass, field
from typing import Any, Awaitable
D = dict


class Game:
    async def start(self): pass
    async def disconnect(self) -> None: pass
    async def is_connected(self) -> bool: pass
    def listen(self, path): pass
    def listen_distance(self, path): pass
    async def send(self, path, value): pass

# TODO: try OSC query
@dataclass
class VRChat(Game):
    hostname: str = '127.0.0.1'
    sending_port: int = 9000
    receiving_port: int = 9001

    async def start(self):
        self.client = SimpleUDPClient(self.hostname, self.sending_port)
        self.dispatcher = Dispatcher()
        self.event_loop = asyncio.get_event_loop()
        self.server = AsyncIOOSCUDPServer((self.hostname, self.receiving_port),
                                          self.dispatcher, self.event_loop)
        self.transport, _ = await self.server.create_serve_endpoint()

    async def disconnect(self) -> None:
        self.transport.close()

    async def is_connected(self) -> bool:
        return not self.transport.is_closing()

    def listen(self, path: str, callback: Awaitable, wildcard_prefix=False):
        if wildcard_prefix: path += '*' # wildcard listen
        # workaround because asyncio DatagramProtocol doesn't support Awaitable callback
        def f(path: str, value: float):
            self.event_loop.create_task(callback(path, value))
        self.dispatcher.map(path, f)

    def listen_distance(self, path: str, callback: Awaitable, wildcard_prefix=False):
        async def f(path: str, proximity: float):
            await callback(path, 1 - proximity) # convert from vrc proximity to distance
        self.listen(path, f, wildcard_prefix)

    async def send(self, path: str, value: float):
        self.client.send_message(path, value)


class ChilloutVR(Game): pass


@dataclass
class Protocol:
    def actuation(self, address, value) -> bytes: pass
    def query_battery(self) -> bytes: pass
    def parse_incoming(self, data: bytes) -> dict: pass


@dataclass
class DakyProtocol(Protocol):
    def actuation(self, address, value: float) -> bytes:
        value = int(remap_clamp(value, 0, 1, 0, 255))
        return b"B" + pack("<BB", address, value)
    def query_battery(self) -> bytes:
        return b"%"
    def parse_incoming(self, data: bytes) -> dict:
        if len(data) < 1:
            raise Exception("Empty packet")
        match data[0:1]:
            case b'%':
                cmd, value = unpack('<cH', data)
                return D(type='battery_value', value=value)
            case _:
                raise Exception(f"Unsupported: {data=}")


class SenseShiftProtocol(Protocol): pass


class Connection:
    async def connect(self, loop, on_receive: Awaitable, on_error: Awaitable) -> None: pass
    async def disconnect(self) -> None: pass
    async def is_connected(self) -> bool: pass
    async def send(self, data: bytes) -> None: pass


@dataclass
class UDP(Connection):
    address: str
    port: int

    async def connect(self, loop, on_receive, on_error) -> None:
        self.hostname = socket.gethostbyname(self.address)
        if not self.hostname:
            raise Exception(f"Couldn't resolve hostname: {self.address}")

        class Receiver(asyncio.DatagramProtocol):
            def datagram_received(self, data, addr):
                print(f"UDP.datagram_received {data=} {addr=}") # TODO
                loop.create_task(on_receive(data))
            def error_received(self, exc):
                print(f"UDP.error_received {exc=}") # TODO
                loop.create_task(on_error(exc))
        self.transport, self.receiver = await loop.create_datagram_endpoint(
                Receiver,
                remote_addr=(self.hostname, self.port))
    async def disconnect(self) -> None:
        self.transport.close()
    async def is_connected(self) -> bool:
        return not self.transport.is_closing() # TODO: can't know, UDP is stateless
    async def send(self, data: bytes) -> None:
        print(f"UDP.send {data=}") # TODO
        self.transport.sendto(data)


@dataclass
class SerialUSB(Connection):
    product: str
    serial_number: str
    baudrate: int = 115200
    timeout: float = 5

    def search_device(self):
        return next(( s
                     for s in serial_ports()
                     if s.product == s.product
                     if s.serial_number == s.serial_number ), None)

    # TODO: unused on_error
    async def connect(self, loop, on_receive, on_error) -> None:
        s = self.search_device()
        if s == None:
            raise Exception(f"Couldn't connect to {self.product} {self.serial_number}")

        class Receiver(asyncio.Protocol):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.buffer = b''
                self.bytes_to_read = 0
            def data_received(self, data):
                # expected format made of packets: size: uint8 + data
                # split into packets and only send when complete
                self.buffer += data
                while True:
                    if self.bytes_to_read:
                        if len(self.buffer) >= self.bytes_to_read:
                            loop.create_task(on_receive(self.buffer[:self.bytes_to_read]))
                            self.buffer = self.buffer[self.bytes_to_read:]
                            self.bytes_to_read = 0

                    if not self.bytes_to_read and len(self.buffer) > 0:
                        (self.bytes_to_read,) = unpack('<B', self.buffer[0:1])
                        self.buffer = self.buffer[1:]
                    else:
                        break
        self.transport, self.receiver = await serial_asyncio.create_serial_connection(
                loop,
                Receiver,
                s.device,
                baudrate = self.baudrate,
                timeout = self.timeout,
                write_timeout = self.timeout,
                xonxoff = 0, rtscts = 0
                )

    async def disconnect(self) -> None:
        self.transport.close()

    async def is_connected(self) -> bool:
        return not self.transport.is_closing()

    async def send(self, data: bytes) -> None:
        # add size prefix of the packet for serial
        self.transport.write(pack('<B', len(data)) + data)


#class Bluetooth(Connection): pass


@dataclass
class Actuator:
    name: str
    min: float = 0.0
    max: float = 1.0

    def map(self, value: float) -> float:
        return remap_clamp(value, 0, 1, self.min, self.max)


@dataclass
class Controller:
    name: str
    address_to_actuator: dict[Any, Actuator]
    protocol: Protocol
    connection: Connection
    on_battery: bool = False

    def __post_init__(self):
        self.name_to_address: dict[str, Any] = D()
        for address, actuator in self.address_to_actuator.items():
            self.add_actuator(address, actuator)

    def actuators(self) -> list[Actuator]:
        return list(self.address_to_actuator.values())

    def add_actuator(self, address: Any, actuator: Actuator) -> None:
        self.name_to_address[actuator.name] = address

    def actuator_address(self, name: str) -> int:
        return self.name_to_address.get(name)

    def resolve(self, address: Any) -> Actuator:
        return self.address_to_actuator.get(address)

    def info(self) -> dict: pass # TODO

    async def actuate(self, address: Any, value: float):
        print(f"Controller.actuate {address=} {value=}")
        actuator = self.address_to_actuator.get(address)
        if actuator == None:
            raise Exception(f"Actuator {address=} not found")
        value = actuator.map(value)
        data = self.protocol.actuation(address, value)
        await self.connection.send(data)


@dataclass
class Router():
    prefix: str

    def __post_init__(self):
        self.name_to_controler = D()

    def add_controller(self, controller: Controller) -> None:
        for a in controller.actuators():
            if (c := self.name_to_controler.get(a.name )):
                raise Exception(f"Conflict {a.name} already registered by {c.name}")
            self.name_to_controler[a.name] = controller

    def controllers(self) -> list[Controller]:
        return list(self.name_to_controler.values())

    def resolve_path(self, path: str) -> (Controller, Any):
        if not path.startswith(self.prefix):
            return None
        name = path[len(self.prefix):] # remove prefix
        return self.resolve_name(name)

    def resolve_name(self, name: str) -> (Controller, Any):
        controller = self.name_to_controler.get(name)
        if controller == None:
            return None
        address = controller.actuator_address(name)
        return (controller, address)


@dataclass
class Behavior:
    router: Router
    min_sensitivity: float = 0.0
    collider_scaler: float = 5

    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def on_update(self, name: str, distance: float) -> None: pass


@dataclass
class ProximityBased(Behavior):
    async def on_update(self, path: str, distance: float) -> None:
        print(f"ProximityBased.on_update {path=} -> {distance=}")
        x = self.router.resolve_path(path)
        if x == None:
            print(f"Warning: received unregistered {path=}")
            return # ignore
        controller, address = x
        await controller.actuate(address, distance)


@dataclass
class VelocityBased(Behavior):
    loop_time: float = 0.1
    stall_time: float = 0.5

    def __post_init__(self):
        self.run = False
        # self.state = D()

    async def start(self) -> None:
        asyncio.create_task(self.periodic_task)
        self.run = True

    async def periodic_task(self) -> None:
        while self.run:
            self.loop()
            await asyncio.sleep(self.loop_time)

    async def loop(self) -> None:
        print("VelocityBased loop: pretend work") # TODO

    async def stop(self) -> None:
        self.run = False

    async def on_update(self, name: str, distance: float) -> None: pass


@dataclass
class Manager:
    game: Game
    router: Router
    behavior: Behavior
    controllers: list[Controller]

    def __post_init__(self):
        for c in self.controllers:
            self.router.add_controller(c)

    async def start(self) -> None:
        loop = asyncio.get_event_loop()

        for c in self.controllers:
            async def on_receive(data):
                print(f"on_receive: {data=}", c.protocol.parse_incoming(data))
            async def on_error(data):
                print(f"on_error: {data=}") # TODO:
            await c.connection.connect(loop, on_receive, on_error)

        await self.behavior.start()
        await self.game.start()
        self.game.listen_distance(path=self.router.prefix,
                                  callback=self.behavior.on_update,
                                  wildcard_prefix=True)
        self.run = True

        while self.run:
            await asyncio.sleep(5) # let everything run

    async def stop(self) -> None:
        self.run = False
