import asyncio
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

async def main():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("Health OK")
            break

    # make_item(lat, lon, alt, speed, fly_through, loiter)
    #   lat, lon    - waypoint position in degrees
    #   alt         - height above takeoff point in meters
    #   speed       - m/s to fly to this waypoint; -1 keeps the current speed
    #   fly_through - True: curve through without stopping
    #               - False: stop at the waypoint before moving on
    #   loiter      - seconds to hover once stopped; -1 means don't wait

    mission_items = [
        make_item(47.398, 8.546, 10, -1, True),                # climb to 10 meters, keep going
        make_item(47.3981, 8.546, 15, -1, True),               # north to 15 meters, keep going
        make_item(47.3981, 8.5461, 20, -1, False, loiter=5),   # east to 20 meters, stop and hover 5 seconds 
    ]

    plan = MissionPlan(mission_items=mission_items)
    await drone.mission.upload_mission(plan)
    print("Mission uploaded")

    await asyncio.sleep(3)
    await drone.action.arm()
    await drone.mission.start_mission()
    print("Mission started")

    async for mp in drone.mission.mission_progress():
        print(f"Waypoint {mp.current} of {mp.total}")
        if mp.total > 0 and mp.current == mp.total:
            break

    await drone.action.return_to_launch()
    print("Returning to launch")

    async for state in drone.telemetry.landed_state():
        if state == LandedState.ON_GROUND:
            break
        
    print("Landed")

asyncio.run(main())