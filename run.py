#!/usr/bin/env python3

import asyncio, sys, traceback
from config import load_config
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('config', type=str)
args = parser.parse_args()

async def main():
    manager = load_config('VRChat', args.config)

    router = manager.router
    print("controllers:", list(router.name_to_controller.keys()))

    await manager.start()


def handle_exception(loop, context):
   if (exc := context.get("exception")):
       print(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)), file=sys.stderr)
   else:
       message = context.get("message", "Unknown error")
       print(f"Exception with message: {message}", file=sys.stderr)

loop = asyncio.new_event_loop()
loop.set_exception_handler(handle_exception)

try:
   loop.run_until_complete(main())
finally:
   loop.close()
