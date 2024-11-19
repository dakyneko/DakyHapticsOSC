#!/usr/bin/env python3

import asyncio, sys, traceback
from config import load_config
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('config', type=str)
args = parser.parse_args()

async def main(manager):
    router = manager.router
    print("controllers:", list(router.name_to_controller.keys()))

    await manager.start()

    async def echo_callback(path, value):
        print(f"echo_callback {path=} {value=}")
    manager.game.listen(path='/avatar/parameters/Triggers',
                        callback=echo_callback)
    try:
        while manager.run:
            await asyncio.sleep(5) # let everything run
    except asyncio.exceptions.CancelledError:
        print("normal shutdown")


def handle_exception(loop, context):
    print(f"main handle_exception {loop=} {context=}") # TODO
    if (exc := context.get("exception")):
        print(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)), file=sys.stderr)
    else:
        message = context.get("message", "Unknown error")
        print(f"Exception with message: {message}", file=sys.stderr)

loop = asyncio.new_event_loop()
loop.set_exception_handler(handle_exception)

try:
    manager = load_config('VRChat', args.config)
    loop.run_until_complete(main(manager))
except KeyboardInterrupt:
    print("main KeyboardInterrupt")
    loop.run_until_complete(manager.stop())
finally:
    loop.close()
