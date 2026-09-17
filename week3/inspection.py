import asyncio
import math
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw
from mavsdk.telemetry import LandedState
from datetime import datetime

current_target = {'north': 0.0, 'east': 0.0} # current_target[0] = inspection_point
radius = 5.0
already_flagged = [False]
battery_state = {}
report_data = []

def make_logger(log_file, tag):

    def log(message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"{timestamp} [{tag}] {message}"
        log_file.write(line + "\n")
        log_file.flush()
    return log


async def position_logger(drone, pos_log):
    async for pos in drone.telemetry.position():
        pos_log(
            f"Lat: {pos.latitude_deg:.6f}, "
            f"Lon: {pos.longitude_deg:.6f}, "
            f"Alt: {pos.relative_altitude_m:.2f}m"
        )

async def battery_logger(drone, bat_log, battery_state):
    async for b in drone.telemetry.battery():
        battery_state["percent"] = b.remaining_percent
        battery_state["voltage"] = b.voltage_v

        bat_log(
            f"Percentage: {b.remaining_percent:.0f}, "
            f"Voltage: {b.voltage_v:.2f}V"
        )

async def print_position(drone):
    async for pos in drone.telemetry.position_velocity_ned():
        north = pos.position.north_m
        east = pos.position.east_m
        altitude = -pos.position.down_m
        dist = math.sqrt((north - current_target['north'])**2 + (east - current_target['east'])**2)

        if dist < radius:
            if not already_flagged[0]:
                print(f"Aproaching inspection point -- dist={dist:.1f}m until arrival.")
                already_flagged[0] = True
        else:
            already_flagged[0] = False

        print(f"[POS] north={north:.1f}m east={east:.1f}m altitude={altitude:.1f} dist={dist:.1f}m")


async def run():

    filename = "flight_log.txt"
    with open(filename, "w") as log_file:

        log_file.write("=" * 50 + "\n")
        log_file.write(
            f"Flight started: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        log_file.write("=" * 50 + "\n")
        log_file.flush()

        # One logger per tag, all sharing the same log_file.
        pos_log = make_logger(log_file, "POS")
        bat_log = make_logger(log_file, "BAT")

        drone = System()
        dwell_time = 1
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
        print("Starting inspection...")
        flight_start = datetime.now()
        monitor_task = asyncio.create_task(print_position(drone))
        monitor_position = asyncio.create_task(position_logger(drone, pos_log))
        monitor_battery = asyncio.create_task(battery_logger(drone, bat_log, battery_state))

        inspection_points = [
            PositionNedYaw(10,0,-10,0),
            PositionNedYaw(10,10,-10,90),
            PositionNedYaw(0,10,-10,180),
            PositionNedYaw(0,0,-10,270)
        ]

        for inspection_point in inspection_points:
            current_target['north'] = inspection_point.north_m
            current_target['east'] = inspection_point.east_m
            already_flagged[0] = False
            await drone.offboard.set_position_ned(inspection_point)
            dwell_start = datetime.now()
            await asyncio.sleep(dwell_time)
            dwell_end = datetime.now()
            arrival_battery = battery_state.get("percent")

            report_data.append({
                "point": inspection_point,
                "arrival_time": dwell_start,
                "dwell_duration": (dwell_end - dwell_start).total_seconds(),
                "battery_percent": arrival_battery
            })

            print(f"Inspecting {inspection_point}...")
            await asyncio.sleep(2)

        print("Stopping offboard mode...")
        await drone.offboard.stop()

        print("Returning to launch...")
        await drone.action.return_to_launch()

        # Wait for landing
        async for state in drone.telemetry.landed_state():
            if state == LandedState.ON_GROUND:
                break

        monitor_task.cancel()
        monitor_position.cancel()
        monitor_battery.cancel()
        for task in (monitor_task, monitor_position, monitor_battery):
            try:
                await task
            except asyncio.CancelledError:
                pass

        print("\n=== Inspection Report ===")
        for i, data in enumerate(report_data, start=1):
            print(f"Point {i}: {data['point']}")
            print(f"  Arrival time: {data['arrival_time'].strftime('%H:%M:%S')}")
            print(f"  Dwell duration: {data['dwell_duration']:.1f}s")
            print(f"  Battery at arrival: {data['battery_percent']}%")

        total_elapsed = (datetime.now() - flight_start).total_seconds()
        print(f"\nTotal flight time: {total_elapsed:.1f}s")
        
        print("Done.")

asyncio.run(run())
