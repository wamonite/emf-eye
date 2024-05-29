from lpd8.lpd8 import LPD8
from lpd8.programs import Programs
from lpd8.pads import Pad, Pads
from lpd8.knobs import Knobs
import json
from typing import Self
import logging


log = logging.getLogger("controller")
# log.setLevel(logging.DEBUG)


# NOTE doesn't work with PGM_1 as it looks like I added 80 to the CC numbers for QLab
# NOTE had to set the pads for PGM_2 to expected values 60, 62, 64, 65, 67, 69, 71, 72
LPD8_PROGRAM = Programs.PGM_2
DEFAULTS_FILE_NAME = "controller.json"


class Controller:

    def __init__(self: Self, sticky: bool = True) -> None:
        self.sticky = sticky

        # get the LPD8 device
        self.lpd8 = LPD8()
        self.lpd8.start()
        self.lpd8.set_knob_limits(LPD8_PROGRAM, Knobs.ALL_KNOBS, 0, 1, is_int=False)
        if not self.sticky:
            self.lpd8.set_not_sticky_knob(LPD8_PROGRAM, Knobs.ALL_KNOBS)
        self.lpd8.set_pad_mode(LPD8_PROGRAM, Pads.ALL_PADS, Pad.PUSH_MODE)

        self.update_flag = False

        self.load_defaults()

        def lpd8_knob(data: tuple[int, int, float]) -> None:
            _, knob, value = data
            self.knob_values[knob - 1] = value
            self.update_flag = True
            log.debug("knob: %s = %s", knob, value)

        def lpd8_pad(data: tuple[int, int, float]) -> None:
            _, pad, on = data
            pad = Pads._pad_index[pad]
            on = on == 1
            self.update_flag = True
            # TODO do something with this
            log.debug("pad: %s = %s", pad, on)

        self.lpd8.subscribe(lpd8_knob, LPD8_PROGRAM, LPD8.CTRL, Knobs.ALL_KNOBS)
        self.lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_ON, Pads.ALL_PADS)
        self.lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_OFF, Pads.ALL_PADS)

    @property
    def updated(self: Self) -> bool:
        if self.update_flag:
            self.update_flag = False
            return True

        return False

    def interpolate(
        self: Self,
        v1: float,
        v2: float,
        knob_index: int,
        invert: bool = False,
    ) -> float:
        i = self.knob_values[knob_index]
        if invert:
            i = 1.0 - i
        return ((v2 - v1) * i) + v1

    def update(self: Self) -> None:
        self.lpd8.pad_update()

    def stop(self: Self) -> None:
        self.lpd8.stop()

    def load_defaults(self: Self) -> None:
        self.knob_values = [0] * Pads.PAD_MAX

        try:
            with open(DEFAULTS_FILE_NAME) as file_object:
                data = json.load(file_object)
                if "knobs" in data:
                    self.knob_values = data["knobs"]

        except FileNotFoundError:
            pass

        for idx, value in enumerate(self.knob_values):
            self.lpd8.set_knob_value(LPD8_PROGRAM, idx + 1, value)

        self.update_flag = True

    def save_defaults(self: Self) -> dict:
        data = {"knobs": self.knob_values}

        try:
            with open(DEFAULTS_FILE_NAME, "w") as file_object:
                return json.dump(data, file_object)

        except Exception as e:
            log.error("%s: %s", e.__class__.__name__, e)
