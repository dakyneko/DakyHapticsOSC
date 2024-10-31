#!/usr/bin/env python3

from utils import *
import base
import yaml


def build_class(of_type, type: str, **kwargs):
    c = getattr(base, type)
    if not c or not of_type in c.__bases__:
        raise Exception(f"Class {type} isn't a valid {of_type}")

    return c(**kwargs)

def reify_config(game_name: str, config: dict): # WARN: config is mutated
    games = []
    c_game = config.get('games', {}).get(game_name)
    if c_game is None:
        raise Exception(f"Game {game_name} never defined")
    game = build_class(base.Game, game_name, **c_game)

    setup = config['setup']
    router = base.Router(**setup['router'])
    behavior = build_class(base.Behavior, **setup['behavior'])

    controllers = []
    for c in setup['controllers']:
        protocol = build_class(base.Protocol, **c.pop('protocol'))
        connection = build_class(base.Connection, **c.pop('connection'))
        actuators = {}
        for address, a in c.pop('actuators').items():
            actuators[address] = base.Actuator(**a)

        controller = base.Controller(
                address_to_actuator=actuators,
                protocol=protocol,
                connection=connection,
                **c)
        controllers.append(controller)

    return base.Manager(game, router, behavior, controllers)


def load_config(game_name: str, path: str):
    with open(path, 'rt') as fd:
        return reify_config(game_name, yaml.safe_load(fd))
