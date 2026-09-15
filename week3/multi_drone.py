import asyncio
from mavsdk import System

async def connect_drone(system_address, index):
    drone = System(port=50051 + index)
    await drone.connect(system_address=system_address)
    print(f"[{system_address}] Waiting for connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"[{system_address}] Connected!")
            break

    print(f"[{system_address}] Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print(f"[{system_address}] Ready!")
            break
    return drone

async def fly_drone(drone,system_address, altitude, hover_time):
    print(f"[{system_address}] Arming...")
    await asyncio.sleep(3)
    await drone.action.arm()
    print(f"[{system_address}] Taking off to {altitude}m...")
    await drone.action.set_takeoff_altitude(altitude)
    await drone.action.takeoff()
    await asyncio.sleep(hover_time)
    print(f"[{system_address}] Landing...")
    await drone.action.land()

async def main():
    drone0, drone1 = await asyncio.gather(
        connect_drone("udpin://0.0.0.0:14540",0),
        connect_drone("udpin://0.0.0.0:14541",1)
    )
    await asyncio.gather(
        fly_drone(drone0, "udpin//:0.0.0.0:14540",10,15),
        fly_drone(drone1, "udpin://0.0.0.0:14541",15,25)
    )

asyncio.run(main())