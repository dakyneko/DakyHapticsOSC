#!/usr/bin/env python3

import asyncio
from config import load_config

async def main():
    manager = load_config('VRChat', 'config_sample.yaml')
    await manager.start()


print(asyncio.run(main()))
