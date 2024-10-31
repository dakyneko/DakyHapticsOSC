#!/usr/bin/env python3

import asyncio
from config import load_config

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


print(asyncio.run(main()))
