#!/usr/bin/env python3

import asyncio, sys, traceback
from config import load_config
from signal import SIGINT

async def main():
    manager = load_config('VRChat', 'config_sample.yaml')

    router = manager.router
    print("controllers:", list(router.name_to_controller.keys()))

    # TODO: test
    async def go():
        await asyncio.sleep(1)
        await manager.on_update(router.prefix + 'headCheekR', 0.5)
    asyncio.create_task(go())

    await manager.start()


def handle_exception(loop, context):
   if (exc := context.get("exception")):
       print(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)), file=sys.stderr)
   else:
       message = context.get("message", "Unknown error")
       print(f"Exception with message: {message}", file=sys.stderr)

loop = asyncio.new_event_loop()
loop.set_exception_handler(handle_exception)
loop.set_debug(True) # TODO
def signal_handler():
    for task in asyncio.all_tasks():
        task.cancel()
# TODO: not implemented on windows
#loop.add_signal_handler(SIGINT, signal_handler)
try:
   loop.run_until_complete(main())
finally:
   loop.close()
