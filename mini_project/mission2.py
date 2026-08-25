import asyncio

from datetime import datetime

from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mavsdk.telemetry import LandedState


def make_item(lat, lon, alt, speed, fly_through, loiter=-1):
    return MissionItem(
        lat,                           # latitude_deg
        lon,                           # longitude_deg
        alt,                           # relative_altitude_m
        speed,                         # speed_m_s
        fly_through,                   # is_fly_through
        float('nan'),                  # gimbal_pitch_deg
        float('nan'),                  # gimbal_yaw_deg
        MissionItem.CameraAction.NONE, # camera_action
        loiter,                         # loiter_time_s
        0,                              # camera_photo_interval_s
        1,                              # acceptance_radius_m
        float('nan'),                   # yaw_deg
        0,                              # camera_photo_distance_m
        MissionItem.VehicleAction.NONE  # vehicle_action
    )


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

async def main():

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
        prog_log = make_logger(log_file, "PROG")

        drone = System()

        await drone.connect(
            system_address="udpin://0.0.0.0:14540"
        )

        # Start telemetry logging tasks
        position_task = asyncio.create_task(
            position_logger(drone, pos_log)
        )

        battery_state = {
            "percent": None,
            "voltage": None
        }

        battery_task = asyncio.create_task(
            battery_logger(drone, bat_log, battery_state)
        )

        # Wait for GPS and home position
        async for health in drone.telemetry.health():
            if (
                health.is_global_position_ok
                and health.is_home_position_ok
            ):
                prog_log("Health OK")
                break

        mission_items = [
            make_item(47.3978543, 8.5462243, 10, -1, True),
            make_item(47.3984310, 8.5465929, 15, -1, False),
            make_item(47.3985919, 8.5460451, 20, -1, True),
            make_item(47.3980288, 8.5457309, 30, -1, False, loiter=5)
        ]

        plan = MissionPlan(
            mission_items=mission_items
        )

        # Arm and start mission
        await drone.mission.upload_mission(plan)

        prog_log("Mission uploaded")

        await asyncio.sleep(3)

        await drone.action.arm()

        prog_log("Armed")

        await drone.mission.start_mission()

        prog_log("Mission started")

        # Monitor mission progress
        last_waypoint = 0

        async for mp in drone.mission.mission_progress():
            if mp.current != last_waypoint:
                message = f"Waypoint {mp.current} of {mp.total}"

                print(message)
                prog_log(message)

                last_waypoint = mp.current

            if mp.total > 0 and mp.current == mp.total:
                break

        await drone.action.return_to_launch()

        prog_log("Returning to launch")

        # Wait for landing
        async for state in drone.telemetry.landed_state():
            if state == LandedState.ON_GROUND:
                break

        prog_log("Landed")

        if (
            battery_state["percent"] is not None
            and battery_state["voltage"] is not None
        ):
            bat_log(
                f"Final battery "
                f"{battery_state['percent']:.2f}%, "
                f"{battery_state['voltage']:.2f}V"
            )

        # Stop telemetry logging tasks
        position_task.cancel()
        battery_task.cancel()

        await asyncio.gather(
            position_task,
            battery_task,
            return_exceptions=True
        )

        prog_log("Flight logging stopped")


asyncio.run(main())