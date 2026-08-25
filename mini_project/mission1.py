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


def write_log(log_file, tag, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"{timestamp} [{tag}] {message}"
    log_file.write(line + "\n")
    log_file.flush()


async def position_logger(drone, log_file):
    async for pos in drone.telemetry.position():
        write_log(
            log_file,
            "POS",
            f"Lat: {pos.latitude_deg:.6f}, "
            f"Lon: {pos.longitude_deg:.6f}, "
            f"Alt: {pos.relative_altitude_m:.2f}m"
        )


async def battery_logger(drone, log_file, battery_state):
    async for b in drone.telemetry.battery():
        battery_state["percent"] = b.remaining_percent
        battery_state["voltage"] = b.voltage_v

        write_log(
            log_file,
            "BAT",
            f"Percentage: {b.remaining_percent:.0f}, "
            f"Voltage: {b.voltage_v:.2f}V"
        )


async def main():

    # Create a unique log file for this flight
    filename = datetime.now().strftime(
        "flight_%Y%m%d_%H%M%S.log"
    )

    with open(filename, "w") as log_file:

        log_file.write("=" * 50 + "\n")
        log_file.write(
            f"Flight started: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        log_file.write("=" * 50 + "\n")
        log_file.flush()

        drone = System()

        await drone.connect(
            system_address="udpin://0.0.0.0:14540"
        )

        # Start telemetry logging tasks
        position_task = asyncio.create_task(
            position_logger(drone, log_file)
        )

        battery_state = {
            "percent": None,
            "voltage": None
        }

        battery_task = asyncio.create_task(
            battery_logger(drone, log_file, battery_state)
        )

        # Wait for GPS and home position
        async for health in drone.telemetry.health():
            if (
                health.is_global_position_ok
                and health.is_home_position_ok
            ):
                write_log(
                    log_file,
                    "PROG",
                    "Health OK"
                )
                break

        mission_items = [
            make_item(
                47.3976099,
                8.546518,
                10,
                -1,
                True
            ),

            make_item(
                47.3977725,
                8.5444628,
                15,
                -1,
                False,
                loiter=5
            ),

            make_item(
                47.3990611,
                8.545965,
                20,
                -1,
                True
            ),

            make_item(
                47.3988042,
                8.5465878,
                30,
                -1,
                False,
                loiter=5
            )
        ]

        plan = MissionPlan(
            mission_items=mission_items
        )

        await drone.mission.upload_mission(plan)

        write_log(
            log_file,
            "PROG",
            "Mission uploaded"
        )

        await asyncio.sleep(3)

        await drone.action.arm()

        write_log(
            log_file,
            "PROG",
            "Armed"
        )

        await drone.mission.start_mission()

        write_log(
            log_file,
            "PROG",
            "Mission started"
        )

        # Monitor mission progress
        last_waypoint = 0

        async for mp in drone.mission.mission_progress():
            if mp.current != last_waypoint:
                message = f"Waypoint {mp.current} of {mp.total}"

                print(message)
                write_log(
                    log_file,
                    "PROG",
                    message
                )

                last_waypoint = mp.current

            if mp.total > 0 and mp.current == mp.total:
                break

        await drone.action.return_to_launch()

        write_log(
            log_file,
            "PROG",
            "Returning to launch"
        )

        # Wait for landing
        async for state in drone.telemetry.landed_state():
            if state == LandedState.ON_GROUND:
                break

        write_log(
            log_file,
            "PROG",
            "Landed"
        )

        if battery_state is not None:
            write_log(
                log_file,
                "BAT",
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

        write_log(
            log_file,
            "PROG",
            "Flight logging stopped"
        )


asyncio.run(main())