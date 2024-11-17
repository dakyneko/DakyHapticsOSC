#!/usr/bin/env python3

from utils import *
import time, zeroconf, logging, re, random, string
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_server import ThreadingOSCUDPServer
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.utility import get_open_udp_port, get_open_tcp_port
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from threading import Thread

# inspired by https://github.com/Hackebein/Object-Tracking-App


def find_service_by_regex(browser: OSCQueryBrowser, regex) -> zeroconf.ServiceInfo | None:
    svcs = browser.get_discovered_oscquery()
    print(f"find_service_by_regex {svcs=}")
    for svc in svcs:
        client = OSCQueryClient(svc)
        host_info = client.get_host_info()
        if host_info is None:
            continue
        if re.match(regex, host_info.name):
            logging.debug(f"Found service by regex: {host_info.name}")
            return svc
    logging.debug(f"Service not found by regex: {regex}")
    return None


def wait_get_oscquery_client() -> OSCQueryClient:
    """
    Waits for VRChat to be discovered and ready and returns the OSCQueryClient.
    Returns:
        OSCQueryClient: OSCQueryClient for VRChat
    """
    logging.info("Waiting for VRChat Client to be discovered ...")
    service_info = None
    browser = OSCQueryBrowser()
    while True:
        # TODO: check if multiple VRChat clients are found
        service_info = find_service_by_regex(browser, r"VRChat-Client-[A-F0-9]{6}")
        print(f"wait_get_oscquery_client {service_info=}")
        if service_info:
            break
        time.sleep(2)  # Wait for discovery
    logging.info(f"Connecting to VRChat Client ({service_info.name}) ...")
    client = OSCQueryClient(service_info)
    logging.info("Waiting for VRChat Client to be ready ...")
    #while client.query_node("/avatar/change") is None:
    #    time.sleep(1)
    logging.info("VRChat Client is ready!")
    return client

def osc_message_handler(path: str, value) -> None:
    print(f"osc_message_handler {path=} {value=}")
    # TODO

def wait_get_oscquery_server() -> ThreadingOSCUDPServer:
    logging.info("Starting OSCquery Server ...")
    disp = Dispatcher()
    disp.set_default_handler(osc_message_handler)
    server_port = get_open_udp_port()
    hostname: str = '127.0.0.1'
    oscQueryServer = ThreadingOSCUDPServer((hostname, server_port), disp)
    Thread(target=oscQueryServer.serve_forever, daemon=True).start()
    # Announce Server
    oscServiceName = "ObjectTracking-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    logging.info(f"Announcing Server as {oscServiceName} ...")
    http_port = get_open_tcp_port()
    oscQueryService = OSCQueryService(oscServiceName, http_port, server_port)
    oscQueryService.advertise_endpoint("/avatar/change")
    # TODO: add all endpoints

    return oscQueryServer


#logging.info("Waiting for VRChat Client to start ...")
#while not is_vrchat_running():  # TODO: check consistently for this
#    time.sleep(1)
osc_ip = 'localhost'
osc_port = 9000
logging.info(f"Waiting for OSCClient to connect to {osc_ip}:{osc_port} ...")
oscClient = SimpleUDPClient(osc_ip, osc_port)
#if AV3EMULATOR_PORT is not None:
#    oscClientUnity = SimpleUDPClient(AV3EMULATOR_IP, AV3EMULATOR_PORT)

logging.info("Waiting for OSCQueryClient to connect to VRChat Client ...")
oscQueryClient = wait_get_oscquery_client()

logging.info("Waiting for OSCQueryServer to start ...")
oscQueryServer = wait_get_oscquery_server()
