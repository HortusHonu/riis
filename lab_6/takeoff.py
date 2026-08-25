import asyncio
from mavsdk import System

async def main():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("Health OK")
            break
    await asyncio.sleep(3) # give the system (QGC and PX4) time to stablize the flight data in sim
    await drone.action.arm()
    await drone.action.takeoff()
    await asyncio.sleep(30) # Hover for 10 seconds and prevent auto-disarm in sim
    await drone.action.land()

asyncio.run(main())

