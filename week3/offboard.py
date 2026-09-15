import asyncio
import math
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw, VelocityNedYaw

async def print_position(drone):
    async for pos in drone.telemetry.position_velocity_ned():
        north = pos.position.north_m
        east = pos.position.east_m
        print(f"[POS] north={north:.1f}m east={east:.1f}m")

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    print("Waiting for connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected")
            break

    print("Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("Ready")
            break

    print("Arming...")
    await drone.action.arm()
    print("Setting initial setpoint...")
    await drone.offboard.set_position_ned(PositionNedYaw(0,0,-10,0))

    print("Starting offboard mode...")
    try:
        await drone.offboard.start()
    except OffboardError as e:
        print(f"Offboard start failed {e}")
        await drone.action.disarm()
        return

    await asyncio.sleep(2)
    print("Fyling sqaure...")
    asyncio.create_task(print_position(drone))

    corners = [
        PositionNedYaw(10,0,-10,0),
        PositionNedYaw(10,10,-10,90),
        PositionNedYaw(0,10,-10,180),
        PositionNedYaw(0,0,-10,270)
    ]

    for corner in corners:
        await drone.offboard.set_position_ned(corner)
        await asyncio.sleep(6)
        print("Square complete.")
        await asyncio.sleep(2)

    print("Flying circle...")
    speed = 2.0
    angle = 0.0
    for _ in range(63):
        vN = speed * math.cos(angle)
        vE = speed * math.sin(angle)
        await drone.offboard.set_velocity_ned(VelocityNedYaw(vN,vE,0.0,0.0))
        angle += 0.1
        await asyncio.sleep(0.1)
    print("Circle complete. Stopping.")
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0,0.0,0.0,0.0))
    await asyncio.sleep(2)

    print("Stopping offboard mode...")
    await drone.offboard.stop()

    print("Returning to launch...")
    await drone.action.return_to_launch()
    print("Done.")

asyncio.run(run())
