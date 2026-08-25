import asyncio
import math
from datetime import datetime
from mavsdk import System

async def position_logger(drone):
    async for pos in drone.telemetry.position():
        print(
            f"{datetime.now().strftime('%H:%M:%S')} [POS] "
            f"Lat: {pos.latitude_deg:.6f}, "
            f"Lon: {pos.longitude_deg:.6f}, "
            f"Alt: {pos.relative_altitude_m:.2f}m"
        )

async def attitude_logger(drone):
    async for att in drone.telemetry.euler():
        print(f"{datetime.now().strftime('%H:%M:%S')} [ATT] "
             f"Roll: {att.roll_deg:.2f}, "
             f"Pitch: {att.pitch_deg:.2f}, "
             f"Yaw: {att.yaw_deg:.2f}"
        )

async def battery_logger(drone):
    async for b in drone.telemetry.battery():
        print(f"{datetime.now().strftime('%H:%M:%S')} [BAT] "
             f"Percentage: {b.remaining_percent:.0f}, "
             f"Voltage: {b.voltage_v}"
        )

async def speed_logger(drone):
    async for s in drone.telemetry.velocity_ned():
        speed = math.sqrt(s.north_m_s**2 + s.east_m_s**2)
        print(f"{datetime.now().strftime('%H:%M:%S')} [SPD] "
              f"Speed: {speed:.2f} m/s"
        )

async def main():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    asyncio.create_task(position_logger(drone))
    asyncio.create_task(attitude_logger(drone))
    asyncio.create_task(battery_logger(drone))
    asyncio.create_task(speed_logger(drone))

    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            break
            print("Health OK")

    await drone.action.arm()
    await drone.action.takeoff()
    await asyncio.sleep(15)
    await drone.action.land()
    await asyncio.sleep(15)

asyncio.run(main())