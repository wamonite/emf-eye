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

    def __init__(self: Self, sticky: bool = True, pad_on_release: bool = True) -> None:
        self._sticky = sticky
        self._pad_on_release = pad_on_release

        # get the LPD8 device
        # NOTE WSL2 supports audio via a Pulse audio server at PULSE_SERVER but does not support MIDI (no /dev/snd/seq)
        # https://github.com/microsoft/WSL/issues/7107
        try:
            self._lpd8 = LPD8()

        except Exception as e:
            # check the exception message as rtmidi does not export the SystemError class
            if not str(e).startswith('MidiInAlsa::initialize:'):
                raise

            self._lpd8 = None
            log.error("MIDI is not supported on WSL2")

        if self._lpd8:
            self._lpd8.start()
            self._lpd8.set_knob_limits(LPD8_PROGRAM, Knobs.ALL_KNOBS, 0, 1, is_int=False)
            if not self._sticky:
                self._lpd8.set_not_sticky_knob(LPD8_PROGRAM, Knobs.ALL_KNOBS)
            self._lpd8.set_pad_mode(LPD8_PROGRAM, Pads.ALL_PADS, Pad.PUSH_MODE)

            def lpd8_knob(data: tuple[int, int, float]) -> None:
                _, knob, value = data
                self._knobs[knob - 1] = value
                self._updated = True
                log.debug("knob: %s = %s", knob, value)

            def lpd8_pad(data: tuple[int, int, float]) -> None:
                _, pad, on = data
                pad = Pads._pad_index[pad]
                on = on == 1
                self._updated = True

                if self._pad_on_release != on:
                    self._pads.append(pad)
                log.debug("pad: %s = %s", pad, on)

            self._lpd8.subscribe(lpd8_knob, LPD8_PROGRAM, LPD8.CTRL, Knobs.ALL_KNOBS)
            self._lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_ON, Pads.ALL_PADS)
            self._lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_OFF, Pads.ALL_PADS)

        self._knobs = [0] * Pads.PAD_MAX
        self._updated = False

        self._pads = []

        self.load_defaults()

    @property
    def updated(self: Self) -> bool:
        if self._updated:
            self._updated = False
            return True

        return False

    def interpolate(
        self: Self,
        v1: float,
        v2: float,
        knob_index: int,
        invert: bool = False,
    ) -> float:
        i = self._knobs[knob_index]
        if invert:
            i = 1.0 - i
        return ((v2 - v1) * i) + v1

    def pads(self: Self) -> list[int]:
        pads = self._pads
        self._pads = []
        return pads

    def update(self: Self) -> None:
        if self._lpd8:
            self._lpd8.pad_update()

    def stop(self: Self) -> None:
        if self._lpd8:
            self._lpd8.stop()

    def load_defaults(self: Self) -> None:
        try:
            with open(DEFAULTS_FILE_NAME) as file_object:
                data = json.load(file_object)
                if "knobs" in data:
                    self._knobs = data["knobs"]

        except FileNotFoundError:
            pass

        if self._lpd8:
            for idx, value in enumerate(self._knobs):
                self._lpd8.set_knob_value(LPD8_PROGRAM, idx + 1, value)

        self._updated = True

    def save_defaults(self: Self) -> dict:
        data = {"knobs": self._knobs}

        try:
            with open(DEFAULTS_FILE_NAME, "w") as file_object:
                return json.dump(data, file_object)

        except Exception as e:
            log.error("%s: %s", e.__class__.__name__, e)
