import asyncio
from datetime import datetime
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mavsdk.telemetry import LandedState

def make_item(lat, lon, alt, speed, fly_through, loiter=-1):
    return MissionItem(
        lat,                            # latitude_deg
        lon,                            # longitude_deg
        alt,                            # relative_altitude_m
        speed,                          # speed_m_s
        fly_through,                    # is_fly_through    
        float('nan'),                   # gimbal_pitch_deg
        float('nan'),                   # gimbal_yaw_deg
        MissionItem.CameraAction.NONE,  # camera_action
        loiter,                         # loiter_time_s
        0,                              # camera_photo_interval_s,
        1,                              # acceptance_radius_m
        float('nan'),                   # yaw_deg
        0,                              # camera_photo_distance_m
        MissionItem.VehicleAction.NONE  # vehicle_action
    )

async def position_logger(drone, log_file):
    async for pos in drone.telemetry.position():
        message = (
            f"{datetime.now().strftime('%H:%M:%S')} [POS] "
            f"Lat: {pos.latitude_deg:.6f}, "
            f"Lon: {pos.longitude_deg:.6f}, "
            f"Alt: {pos.relative_altitude_m:.2f}m"
        )

        print(message)
        log_file.write(message + "\n")
        log_file.flush()

async def battery_logger(drone, log_file):
    async for b in drone.telemetry.battery():
        message = (
            f"{datetime.now().strftime('%H:%M:%S')} [BAT] "
            f"Percentage: {b.remaining_percent:.0f}, "
            f"Voltage: {b.voltage_v}V"
        )

        print(message)
        log_file.write(message + "\n")
        log_file.flush()

async def main():

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
        await drone.connect(system_address="udpin://0.0.0.0:14540")

        asyncio.create_task(position_logger(drone, log_file))
        asyncio.create_task(battery_logger(drone, log_file))

        async for health in drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("Health OK")
                log_file.write(
                    f"{datetime.now().strftime('%H:%M:%S')} [PROG] Health OK\n"
                )
                log_file.flush()
                break

        # make_item(lat, lon, alt, speed, fly_through, loiter)
        #   lat, lon    - waypoint position in degrees
        #   alt         - height above takeoff point in meters
        #   speed       - m/s to fly to this waypoint; -1 keeps the current speed
        #   fly_through - True: curve through without stopping
        #               - False: stop at the waypoint before moving on
        #   loiter      - seconds to hover once stopped; -1 means don't wait

        mission_items = [
            make_item(47.3976099, 8.546518  , 10, -1, True),                # climb to 10 meters, keep going
            make_item(47.3977725, 8.5444628, 15, -1, False,  loiter=5),      # north to 15 meters, stop and hover 5 seconds
            make_item(47.3990611, 8.545965, 20, -1, True),                  # east to 20 meters, keep going 
            make_item(47.3988042, 8.5465878, 30, -1, False, loiter=5)       # east to 30 meters, stop and hover 5 seconds 
        ]

        plan = MissionPlan(mission_items=mission_items)
        await drone.mission.upload_mission(plan)
        message = (
            f"{datetime.now().strftime('%H:%M:%S')} [PROG] Mission uploaded"
        )
        print(message)
        log_file.write(message + "\n")
        log_file.flush()

        await asyncio.sleep(3)
        await drone.action.arm()
        await drone.mission.start_mission()
        print("Mission started")
        log_file.write(
            f"{datetime.now().strftime('%H:%M:%S')} [PROG] Mission started\n"
        )
        log_file.flush()

        async for mp in drone.mission.mission_progress():
            message = (
                f"{datetime.now().strftime('%H:%M:%S')} [PROG] "
                f"Waypoint {mp.current} of {mp.total}"
            )

            print(message)
            log_file.write(message + "\n")
            log_file.flush()

            if mp.total > 0 and mp.current == mp.total:
                break

        await drone.action.return_to_launch()
        print("Returning to launch")
        log_file.write(
            f"{datetime.now().strftime('%H:%M:%S')} [PROG] Returning to launch\n"
        )
        log_file.flush()

        async for state in drone.telemetry.landed_state():
            if state == LandedState.ON_GROUND:
                break
            
        print("Landed")
        log_file.write(
            f"{datetime.now().strftime('%H:%M:%S')} [PROG] Landed\n"
        )
        log_file.flush()

asyncio.run(main())