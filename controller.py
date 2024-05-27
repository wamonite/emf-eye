from lpd8.lpd8 import LPD8
from lpd8.programs import Programs
from lpd8.pads import Pad, Pads
from lpd8.knobs import Knobs
import logging


log = logging.getLogger("controller")
# log.setLevel(logging.DEBUG)


# NOTE doesn't work with PGM_1 as it looks like I added 80 to the CC numbers for QLab
# NOTE had to set the pads for PGM_2 to expected values 60, 62, 64, 65, 67, 69, 71, 72
LPD8_PROGRAM = Programs.PGM_2


class Controller:
    def __init__(self):
        # get the LPD8 device
        self.lpd8 = LPD8()
        self.lpd8.start()
        self.lpd8.set_knob_limits(LPD8_PROGRAM, Knobs.ALL_KNOBS, 0, 1, is_int=False)
        self.lpd8.set_pad_mode(LPD8_PROGRAM, Pads.ALL_PADS, Pad.PUSH_MODE)

        self.knob_values = [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]

        def lpd8_knob(data):
            _, knob, value = data
            self.knob_values[knob] = value
            log.debug("knob: %s = %s", knob, value)

        def lpd8_pad(data):
            _, pad, on = data
            pad = Pads._pad_index[pad]
            on = on == 1
            print(pad, on)

        self.lpd8.subscribe(lpd8_knob, LPD8_PROGRAM, LPD8.CTRL, Knobs.ALL_KNOBS)
        self.lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_ON, Pads.ALL_PADS)
        self.lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_OFF, Pads.ALL_PADS)

    def update(self):
        self.lpd8.pad_update()

    def stop(self):
        self.lpd8.stop()
