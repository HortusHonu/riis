import asyncio
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mavsdk.telemetry import LandedState

async def main():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("Health OK")
            break

    mission_items = [
        MissionItem(47.398, 8.546, 10, -1, True, float('nan'), float('nan'), MissionItem.CameraAction.NONE, -1, 0, 1, float('nan'), 0, MissionItem.VehicleAction.NONE),
        MissionItem(47.3981, 8.546, 15, -1, True, float('nan'), float('nan'), MissionItem.CameraAction.NONE, -1, 0, 1, float('nan'), 0, MissionItem.VehicleAction.NONE),
        MissionItem(47.3981, 8.5461, 20, -1, False, float('nan'), float('nan'), MissionItem.CameraAction.NONE, 5, 0, 1, float('nan'), 0, MissionItem.VehicleAction.NONE),
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