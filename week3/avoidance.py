import asyncio
import math

from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw

obstacle = {'north': 15.0, 'east': 0.0, 'radius': 4.0}
state = [False] # state[0] = True means currently avoiding

async def position_monitor(drone: System):
    async for pos in drone.telemetry.position_velocity_ned():
        north = pos.position.north_m
        east = pos.position.east_m
        dist = math.sqrt((north - obstacle['north'])**2 + (east - obstacle['east'])**2)

        if not state[0] and dist < obstacle['radius'] * 1.5:
            print(f"OBSTACLE DETECTED -- dist={dist:.1f}m, triggering avoidance.")
            state[0] = True
        elif state[0] and dist > obstacle['radius'] * 1.5:
            print(f"CLEAR -- dist={dist:.1f}m, resuming route.")
            state[0] = False

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    print("Waiting for connection...")
    async for s in drone.core.connection_state():
        if s.is_connected:
            print("Connected!")
            break
    print("Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("Ready!")
            break
    print("Arming...")
    await drone.action.arm()
    print("Setting intital setpoint...")
    await drone.offboard.set_position_ned(PositionNedYaw(0,0,-10,0))
    print("Starting offboard mode...")
    try:
        await drone.offboard.start()
    except OffboardError as e:
        print(f"Offboard start failed: {e}")
        await drone.action.disarm()
        return
    await asyncio.sleep(2)

    asyncio.create_task(position_monitor(drone))
    print("Flying toward obstacle zone...")
    await drone.offboard.set_position_ned(PositionNedYaw(30,0,-10,0))

    for _ in range(300): # monitor for up to 60 seconds
        await asyncio.sleep(0.2)
        if state[0]:
            await drone.offboard.set_position_ned(PositionNedYaw(15,8,-10,0))
        else:
            await drone.offboard.set_position_ned(PositionNedYaw(30,0,-10,0))
            
    print("Stopping offboard mode...")
    await drone.offboard.stop()
    print("Returning to launch...")
    await drone.action.return_to_launch()
    print("Done.")
    
asyncio.run(run())
        