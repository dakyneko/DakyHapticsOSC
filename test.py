#!/usr/bin/env python3

from base import *

async def main():
    vrc = VRChat()
    router = Router(prefix='/avatar/parameters/haptX-')
    behavior = ProximityBased(router)

    manager = Manager(vrc, router, behavior, [
        Controller('headset',
                   {0: Actuator('headCheekR', min=0.0275, max=0.0392),
                    1: Actuator('headCheekL', min=0.0275, max=0.0392),
                    2: Actuator('headTop', min=0.0325, max=0.0588)},
                   protocol=DakyProtocol(),
                   connection=UDP('localhost', 1337),
                   on_battery=False),
        ])

    print("controllers:", list(router.name_to_controler.keys()))

    async def go():
        await asyncio.sleep(1)
        await behavior.on_update(router.prefix + 'headCheekR', 0.5) # TODO: test
    asyncio.create_task(go())

    await manager.start()


print(asyncio.run(main()))
