from mic_array import Tuning
import usb.core
import usb.util
import time

dev = None
mic_tuning = None

def init():
    """ Call to setup microphone array, before calling this poll() will return None """
    global dev
    global mic_tuning
    dev = usb.core.find(idVendor=0x2886, idProduct=0x0018)
    mic_tuning = Tuning(dev)

def poll():
    """ Poll the microphone array for the most recent object position
    :returns: x, y, list of TrackPoint objects.  x is None if no object is found, list is None if no objects are found

    """
    if mic_tuning is None:
        return None, None, None
    y = 0.5
    x = mic_tuning.direction / 360.0
    return x, y, None

