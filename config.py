#!/usr/bin/env python3

from utils import *
import base
import yaml


def build_class(of_type, type: str, **kwargs):
    c = getattr(base, type)
    if not c or not of_type in c.__bases__:
        raise Exception(f"Class {type} isn't a valid {of_type}")

    return c(**kwargs)

def reify_config(config: dict):
    games = []
    for n, x in config.get('games', {}).items():
        game = build_class(base.Game, n, **x)
        games.append(game)

    if len(games) == 0:
        raise Exception("No game defined")

    setup = config['setup']
    router = base.Router(**setup['router'])
    behavior = build_class(base.Behavior, **setup['behavior'])

    controllers = []
    for c in setup['controllers']:
        protocol = build_class(base.Protocol, **c['protocol'])
        connection = build_class(base.Connection, **c['connection'])
        actuators = {}
        for address, a in c['actuators'].items():
            actuators[address] = base.Actuator(**a)
        controller = base.Controller(
                address_to_actuator=actuators,
                protocol=protocol,
                connection=connection,
                **remove_keys(c, 'protocol', 'connection', 'actuators'))
        controllers.append(controller)

    return base.Manager(game, router, behavior, controllers)


def load_config(path: str):
    with open(path, 'rt') as fd:
        return reify_config(yaml.safe_load(fd))
