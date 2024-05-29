import numpy as np
from enum import IntEnum
from OpenGL import GL
from math import sin, cos, pi
from .exceptions import ScriptException
from .controller import Controller
from typing import Optional
import logging


log = logging.getLogger("warp")
# log.setLevel(logging.DEBUG)


WARP_PARAMETER_STEPS = 20
Y_FAN_SCALE = 3
KNOB_X_POS = 0
KNOB_X_FAN = 1
KNOB_ASPECT = 2
KNOB_Y_POS = 4
KNOB_Y_FAN = 5
POINT_OFFSET = 0.002
LINE_WIDTH_NORMAL = 2
LINE_WIDTH_SELECTED = 8


class Warp(IntEnum):
    PARAMETER = 0
    NONE = 1


def calculate_warp(
    warp_num: Warp,
    display_resolution: tuple[int, int],
    controller: Controller,
) -> np.ndarray:
    display_aspect = display_resolution[0] / display_resolution[1]
    display_scale = controller.interpolate(display_aspect, 1.0, KNOB_ASPECT, True)

    def cos_curve(v: float, knob_index: int, invert: bool) -> float:
        t = v * pi
        c = (1.0 - cos(t)) / 2.0
        return controller.interpolate(c, v, knob_index, invert)

    def sin_curve(v: float, knob_index: int, invert: bool) -> float:
        t = v * pi
        c = sin(t)
        return controller.interpolate(c, 1.0, knob_index, invert)

    match warp_num:
        case Warp.NONE:
            return np.array(
                [
                    [[0.0, 0.0], [1.0, 0.0]],
                    [[0.0, 1.0], [1.0, 1.0]],
                ],
                np.float32,
            )

        case Warp.PARAMETER:
            coord_array = []
            for y in [
                v / WARP_PARAMETER_STEPS for v in range(WARP_PARAMETER_STEPS + 1)
            ]:
                y_scale = sin_curve(y, KNOB_X_FAN, True)

                row = []
                for x in [
                    v / WARP_PARAMETER_STEPS for v in range(WARP_PARAMETER_STEPS + 1)
                ]:
                    x_pos = cos_curve(x, KNOB_X_POS, True)
                    x_pos -= 0.5
                    x_pos *= y_scale
                    x_pos /= display_scale
                    x_pos += 0.5

                    y_fan = 1.0 - sin_curve(x, KNOB_Y_FAN, True)
                    y_fan *= Y_FAN_SCALE
                    y_fan += 1.0

                    y_pos = cos_curve(y, KNOB_Y_POS, True)
                    y_pos -= 0.5
                    y_pos *= y_fan
                    y_pos += 0.5

                    row.append(
                        [x_pos, y_pos],
                    )
                coord_array.append(row)

            return np.array(
                coord_array,
                np.float32,
            )

        case _:
            raise ScriptException(f"load_warp {warp_num} not implemented")


def render_warp(
    tx_ref: int,
    display_resolution: tuple[int, int],
    coord_array: np.ndarray,
    offset_coord: tuple[float, float],
    show_points: bool,
    invert_x: bool = False,
    mouse_pos: Optional[tuple[float, float]] = None,
) -> None:
    GL.glEnable(GL.GL_TEXTURE_2D)
    GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)
    GL.glColor3f(1.0, 1.0, 1.0)

    d_y_size, d_x_size, _ = coord_array.shape

    points = set()

    for s_y_idx in range(d_y_size - 1):
        s_y_pos_0 = s_y_idx / (d_y_size - 1)
        s_y_pos_0 += offset_coord[1]
        s_y_pos_1 = (s_y_idx + 1) / (d_y_size - 1)
        s_y_pos_1 += offset_coord[1]

        GL.glBegin(GL.GL_QUAD_STRIP)
        log.debug("----")

        for s_x_idx in range(d_x_size):
            s_x_pos = s_x_idx / (d_x_size - 1)
            if invert_x:
                s_x_pos = 1.0 - s_x_pos
            s_x_pos += offset_coord[0]

            d_pos_0 = coord_array[s_y_idx, s_x_idx]
            d_pos_1 = coord_array[s_y_idx + 1, s_x_idx]

            GL.glTexCoord2f(s_x_pos, s_y_pos_0)
            GL.glVertex3f(d_pos_0[0], d_pos_0[1], 0.0)

            GL.glTexCoord2f(s_x_pos, s_y_pos_1)
            GL.glVertex3f(d_pos_1[0], d_pos_1[1], 0.0)

            points.add(((d_pos_0[0], d_pos_0[1]), (s_x_idx, s_y_idx)))
            points.add(((d_pos_1[0], d_pos_1[1]), (s_x_idx, s_y_idx + 1)))

            log.debug("s %s %s", s_x_pos, s_y_pos_0)
            log.debug("s %s %s", s_x_pos, s_y_pos_1)
            log.debug("d %s %s", d_pos_0[0], d_pos_0[1])
            log.debug("d %s %s", d_pos_1[0], d_pos_1[1])

        GL.glEnd()

    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    selected = None
    if show_points:
        display_aspect = display_resolution[0] / display_resolution[1]
        point_offset_x = POINT_OFFSET
        point_offset_y = point_offset_x * display_aspect
        for point in points:
            GL.glLineWidth(LINE_WIDTH_NORMAL)
            GL.glColor3f(1.0, 0.0, 0.0)

            if (
                mouse_pos
                and mouse_pos[0] >= point[0][0] - point_offset_x
                and mouse_pos[0] < point[0][0] + point_offset_x
                and mouse_pos[1] >= point[0][1] - point_offset_y
                and mouse_pos[1] < point[0][1] + point_offset_y
            ):
                GL.glLineWidth(LINE_WIDTH_SELECTED)
                GL.glColor3f(1.0, 0.0, 1.0)
                selected = point

            GL.glBegin(GL.GL_LINE_LOOP)
            GL.glVertex2f(point[0][0] - point_offset_x, point[0][1] - point_offset_y)
            GL.glVertex2f(point[0][0] - point_offset_x, point[0][1] + point_offset_y)
            GL.glVertex2f(point[0][0] + point_offset_x, point[0][1] + point_offset_y)
            GL.glVertex2f(point[0][0] + point_offset_x, point[0][1] - point_offset_y)
            GL.glEnd()

    return selected
