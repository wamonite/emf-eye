from radariq import RadarIQ, MODE_OBJECT_TRACKING, MODE_POINT_CLOUD
import time

# Uses modules: six, pyserial
#
# Example object tracking data:
# [{'tracking_id': 0,
#   'x_pos': 0.409, 'y_pos': 0.975, 'z_pos': -0.061,
#   'x_vel': 0.323, 'y_vel': 0.771, 'z_vel': -0.048,
#   'x_acc': 0.996, 'y_acc': 0.32, 'z_acc': 0.0}]


rig = None
last_x = 0.0
last_y = 0.0
last_z = 0.0
last_v = 0.0
last_id = 0


class TrackPoint:
    def __init__(self, x, y, z, id):
        self.x = x
        self.y = y
        self.z = z
        self.id = id

    def __str__(self):
        return f"TrackPoint: x={self.x}, y={self.y}, v={self.v}, id={self.id}"


def init():
    """ Call to setup radar, before calling this poll() will return None """
    try:
        riq = RadarIQ()
        riq.set_mode(MODE_OBJECT_TRACKING)
        riq.set_units('m', 'm/s')
        riq.set_frame_rate(5)
        riq.set_distance_filter(0, 10)
        riq.set_angle_filter(-45, 45)
        riq.start()
    except Exception as e:
        print(e)
        return False
    global rig
    rig = riq
    return True


def poll():
    """ Poll the radar for the most recent object position
    :returns: x, y, list of TrackPoint objects.  x is None if no object is found, list is None if no objects are found

    """
    # If we're not initialized, do nothing
    if rig is None:
        return None, None, None
    global last_x
    global last_y
    global last_id
    frame = rig.get_frame()
    track_points = []
    if frame is None or len(frame) == 0:
        return last_x, last_y, None
    # Find the fastest object
    index = 0
    max_v = 0
    target_obj = None
    for obj in frame:
        # Compute velocity magnitude
        vx = obj['x_vel']
        vy = obj['y_vel']
        vz = obj['z_vel']
        v = (vx ** 2 + vy ** 2 + vz ** 2) ** 0.5
        if v > max_v:
            max_v = v
            last_id = obj['tracking_id']
            target_obj = obj
        track_points += [TrackPoint(obj['x_pos'], obj['y_pos'], obj['z_pos'], obj['tracking_id'])]

    if target_obj is not None:
        last_z = target_obj['z_pos']
        last_x = target_obj['x_pos'] / 2.0
        last_y = target_obj['y_pos'] / 2.0
        last_v = max_v
    return last_x, last_y, track_points


if __name__ == '__main__':
    init()
    while True:
        x, y, pnts = poll()
        if x is not None:
            print(f"x: {x}, y: {y} ")
            if pnts is not None:
                for p in pnts:
                    print(f"  {p}")
        time.sleep(0.05)
