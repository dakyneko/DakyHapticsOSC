#!/usr/bin/env python3

from utils import *
import socket, logging as log, re, asyncio, serial_asyncio, zeroconf
from struct import unpack, pack
from time import time
from collections import defaultdict
from math import sqrt
from pythonosc.dispatcher import Dispatcher as OSCDispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient as OSCSimpleUDPClient
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.utility import get_open_udp_port, get_open_tcp_port
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from types import SimpleNamespace as N
from serial import Serial
from serial.tools.list_ports import comports as serial_ports
from random import random
from dataclasses import dataclass, field
from typing import Any, Awaitable
D = dict


# TODO: replace with proper class
def log(*args, **kwargs):
    print(*args, **kwargs)


class Game:
    async def start(self): pass
    async def stop(self): pass
    async def disconnect(self) -> None: pass
    async def is_connected(self) -> bool: pass
    def listen(self, path): pass
    def listen_distance(self, path): pass
    async def send(self, path, value): pass

@dataclass
class VRChat(Game):
    hostname: str = '127.0.0.1'
    sending_port: int = 9000
    receiving_port: int = None # if None use OSC Query
    osc_server_name: str = "DakyHaptics"

    async def start(self) -> None:
        self.client = OSCSimpleUDPClient(self.hostname, self.sending_port)
        self.dispatcher = OSCDispatcher()
        self.event_loop = asyncio.get_event_loop()
        self.use_osc_query = self.receiving_port == None
        if self.use_osc_query:
            self.receiving_port = get_open_udp_port()
            log(f"VRChat using OSC Query {self.receiving_port=}")

        self.server = AsyncIOOSCUDPServer((self.hostname, self.receiving_port),
                                          self.dispatcher, self.event_loop)
        self.transport, _ = await self.server.create_serve_endpoint()

        if self.use_osc_query:
            log(f"VRChat using OSC Query part 2")
            self.osc_query_client = await self.wait_vrc_osc()
            #self.osc_query_client = None # TODO
            log(f"VRChat using OSC Query part 2 OSCQueryService")
            osc_query_port = get_open_tcp_port()
            self.osc_query_service = OSCQueryService(self.osc_server_name, osc_query_port, self.receiving_port)
            await self.osc_query_service.start()
            # TODO: if stopping should remove from OSC Query
            log(f"VRChat OSC Query done {self.receiving_port=} {self.osc_query_client=} {self.osc_query_service=} {osc_query_port=}")

    async def stop(self) -> None:
        if self.use_osc_query:
            await self.osc_query_service.stop()
        await self.disconnect()

    async def disconnect(self) -> None:
        self.transport.close()

    async def is_connected(self) -> bool:
        return not self.transport.is_closing()

    def listen(self, path: str, callback: Awaitable, wildcard_prefix=False):
        if wildcard_prefix: path += '*' # wildcard listen
        # workaround because asyncio DatagramProtocol doesn't support Awaitable callback
        def f(path: str, value: Any):
            self.event_loop.create_task(callback(path, value))
        self.dispatcher.map(path, f)
        if self.use_osc_query:
            log(f"VRChat OSC Query advertise {path=}") # TODO
            self.osc_query_service.advertise_endpoint(path)

    def listen_distance(self, path: str, callback: Awaitable, wildcard_prefix=False):
        async def f(path: str, proximity: float):
            await callback(path, 1 - proximity) # convert from vrc proximity to distance
        self.listen(path, f, wildcard_prefix)

    async def send(self, path: str, value: float):
        self.client.send_message(path, value)

    # adapted from https://github.com/Hackebein/Object-Tracking-App
    def find_vrc_osc(self, browser: OSCQueryBrowser) -> zeroconf.ServiceInfo | None:
        for s in browser.get_discovered_oscquery():
            client = OSCQueryClient(s)
            host_info = client.get_host_info()
            if host_info is None:
                continue
            if re.match(r"VRChat-Client-[A-F0-9]{6}", host_info.name):
                return s
        return None

    async def wait_vrc_osc(self) -> OSCQueryClient:
        log(f"VRChat wait_vrc_osc start")
        browser = OSCQueryBrowser()
        service_info = None
        while True:
            service_info = self.find_vrc_osc(browser)
            log(f"VRChat wait_vrc_osc {service_info=}")
            if service_info:
                break
            await asyncio.sleep(1) # Wait for discovery
        client = OSCQueryClient(service_info)
        log(f"VRChat found {client=}")
        return client


#class ChilloutVR(Game): pass


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
                log(f"UDP.datagram_received {data=} {addr=}") # TODO
                loop.create_task(on_receive(data))
            def error_received(self, exc):
                log(f"UDP.error_received {exc=}") # TODO
                loop.create_task(on_error(exc))
        self.transport, self.receiver = await loop.create_datagram_endpoint(
                Receiver,
                remote_addr=(self.hostname, self.port))
    async def disconnect(self) -> None:
        self.transport.close()
    async def is_connected(self) -> bool:
        return not self.transport.is_closing() # TODO: can't know, UDP is stateless
    async def send(self, data: bytes) -> None:
        log(f"UDP.send {data=}") # TODO
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
    min_sensitivity: float = 0.0
    # handlded by behaviors
    collider_scaler: float = 5 # velocity only
    throttle: Any = None

    def map(self, value: float) -> float:
        if value < self.min_sensitivity:
            return 0.
        return remap_clamp(value, self.min_sensitivity, 1, self.min, self.max)


@dataclass
class Controller:
    name: str # must be unique
    address_to_actuator: dict[Any, Actuator]
    protocol: Protocol
    connection: Connection
    # TODO: not handled yet
    on_battery: bool = False
    inverted_values: bool = False
    max_concurrent: int = None

    def __post_init__(self):
        self.name_to_address: dict[str, Any] = {}
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
        log(f"Controller.actuate {address=} {value=}")

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
        self.name_to_controller = {}

    def add_controller(self, controller: Controller) -> None:
        for a in controller.actuators():
            if (c := self.name_to_controller.get(a.name)) and c != controller:
                raise Exception(f"Conflict {a.name} already registered by {c.name}")
            self.name_to_controller[a.name] = controller

    def controllers(self) -> list[Controller]:
        return list(self.name_to_controller.values())

    def resolve_name(self, name: str) -> (Controller, Any):
        controller = self.name_to_controller.get(name)
        if controller == None:
            return None
        address = controller.actuator_address(name)
        return (controller, address)

    def resolve_path(self, path: str) -> (Controller, Any):
        if not path.startswith(self.prefix):
            return None
        name = path[len(self.prefix):] # remove prefix
        return self.resolve_name(name)


@dataclass
class BehaviorState:
    timeout_at: float = 0 # absolute timestamp
    timeout_task: asyncio.Task = None

@dataclass
class Behavior:
    timeout: float = 0.25 # turn off after no update
    # must be defined by subclasses
    #states: (Controller, address) -> BehaviorState

    async def start(self) -> None: pass
    async def stop(self) -> None: pass
    async def on_update(self, Controller: Controller, address: Any, distance: float) -> None: pass

    def get_state(self, controller: Controller, address: Any) -> BehaviorState:
        return self.states[(controller.name, address)]

    async def on_timeout(self, state: BehaviorState, controller: Controller, address: Any, actuator: Actuator):
        log(f'{controller.name}/{actuator.name} on_timeout') # debug
        await controller.actuate(address, 0) # TODO: should register the stop?
        state.timeout_task = None
        state.timeout_at = None

    async def ensure_timeout(self, now: float, state: BehaviorState, controller: Controller, address: Any, actuator: Actuator):
        loop = asyncio.get_event_loop()
        if state.timeout_task:
            state.timeout_task.cancel() # reschedule
        f = self.on_timeout(state, controller, address, actuator)
        state.timeout_task = loop.create_task(delayed_async(self.timeout, f))
        state.timeout_at = now + self.timeout


@dataclass
class ProximityBased(Behavior):
    def __post_init__(self):
        self.states = defaultdict(BehaviorState)

    async def on_update(self, controller: Controller, address: Any, distance: float) -> None:
        log(f"ProximityBased.on_update {controller.name}#{address} -> {distance=}")
        now = time()
        state = self.get_state(controller, address)
        actuator = controller.resolve(address)

        intensity = 1 - distance # yeah like proximity
        await controller.actuate(address, intensity)
        await self.ensure_timeout(now, state, controller, address, actuator)
        # TODO: handle throttle?


@dataclass
class VelocityState(BehaviorState):
    next_at: float = 0 # absolute timestamp
    last_distance: float = 0
    last_time: float = 0
    samples: list[float] = field(default_factory=list)
    throttled_task: asyncio.Task = None

@dataclass
class VelocityBased(Behavior):
    stall_time: float = 0.5 # max sample time

    def __post_init__(self):
        self.states = defaultdict(VelocityState)

    async def on_update(self, controller: Controller, address: Any, distance: float) -> None:
        state = self.get_state(controller, address)
        actuator = controller.resolve(address)
        # TODO: can get actuator extra attributes

        now = time()
        dt = now - state.last_time

        if dt > self.stall_time:
            state.samples = []
            log(f"{controller.name}/{actuator.name} samples stall") # debug
        else:
            ddist = abs(state.last_distance - distance)
            v = clamp(ddist / dt / actuator.collider_scaler, 0, 1) # normalized 0-1
            state.samples.append(v)

        state.last_time = now
        state.last_distance = distance

        await self.on_sample(now, state, controller, address, actuator)

    async def on_sample(self, now: float, state: VelocityState, controller: Controller, address: Any, actuator: Actuator):
        if state.throttled_task != None:
            return # throttled

        await self.handle_samples(now, state, controller, address, actuator)

    # TODO: consider doing a continuous moving average (smoother)
    async def handle_samples(self, now: float, state: VelocityState, controller: Controller, address: Any, actuator: Actuator):
        loop = asyncio.get_event_loop()

        if len(state.samples) == 0:
            return # nothing to do

        v_avg = sum(state.samples) / len(state.samples)
        await controller.actuate(address, v_avg)
        log(f'{controller.name}/{actuator.name} -> actuate {v_avg*100=:3.2f}% samples={len(state.samples)} ') # debug
        state.samples = [] # flush data

        # will actuate for a bit until timeout
        await self.ensure_timeout(now, state, controller, address, actuator)

        throttle_time: float = None
        if (throttle := actuator.throttle):
            if (w := throttle.get('constant')):
                throttle_time = w
            elif (w := throttle.get('random')):
                # inverse proportional to intensity
                throttle_time = random() * remap_clamp(v_avg, 1, 0, 0, w)

        # don't spam actuator + allows to collect more samples
        if throttle_time:
            if state.throttled_task != None:
                log(f"Warning {controller.name}/{actuator.name} trying to schedule throttle task but one is already set!") # TODO: debug
            else:
                f = self.on_throttle_over(state, controller, address, actuator)
                state.throttled_task = loop.create_task(delayed_async(throttle_time, f))
                state.next_at = now + throttle_time
                log(f"{controller.name}/{actuator.name} schedule throttle {throttle_time=:.1f}") # TODO: debug

    async def on_throttle_over(self, state: VelocityState, controller: Controller, address: Any, actuator: Actuator):
        log(f'{controller.name}/{actuator.name} on_throttle_over ({len(state.samples)} samples)') # debug
        now = time()
        state.throttled_task = None
        state.next_at = None
        await self.handle_samples(now, state, controller, address, actuator)


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
                log(f"on_receive: {data=}", c.protocol.parse_incoming(data))
            async def on_error(data):
                log(f"on_error: {data=}") # TODO:
            await c.connection.connect(loop, on_receive, on_error)

        await self.behavior.start()
        await self.game.start()
        self.game.listen_distance(path=self.router.prefix,
                                  callback=self.on_update,
                                  wildcard_prefix=True)
        self.run = True

    async def on_update(self, path: str, *args) -> None:
        x = self.router.resolve_path(path)
        if x == None:
            log(f"Warning: received unregistered {path=} {args}")
            return # ignore
        else:
            log(f"Manager.on_update {path=} {args=}")

        controller, address = x
        await self.behavior.on_update(controller, address, *args)

    async def stop(self) -> None:
        self.run = False
        await self.game.stop()
