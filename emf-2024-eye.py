"""
EMF 2024 eye renderer
"""

import argparse
import pygame
from OpenGL import GL
import numpy as np
from enum import IntEnum
from math import sin, cos, pi
import json
from lpd8.lpd8 import LPD8
from lpd8.programs import Programs
from lpd8.pads import Pad, Pads
from lpd8.knobs import Knobs
import logging


log = logging.getLogger()
log_handler = logging.StreamHandler()
log.addHandler(log_handler)
# log.setLevel(logging.DEBUG)


RESOLUTION_TARGET = (1920, 1080)
FPS_TARGET = 60
POINT_OFFSET = 0.002
SPHERE_STEPS = 25
CUSTOM_STEPS = 20
# NOTE doesn't work with PGM_1 as it looks like I added 80 to the CC numbers for QLab
# NOTE had to set the pads for PGM_2 to expected values 60, 62, 64, 65, 67, 69, 71, 72
LPD8_PROGRAM = Programs.PGM_2


class Warp(IntEnum):
    NONE = 1
    SPHERE = 2


class QuitException(Exception):
    pass


class GameException(Exception):
    pass


def load_texture(file_name):
    tx_ref = GL.glGenTextures(1)
    tx_surface = pygame.image.load(file_name)

    tx_w = tx_surface.get_width()
    tx_h = tx_surface.get_height()
    tx_data = pygame.image.tostring(tx_surface, "RGB", True)
    GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)
    GL.glTexImage2D(
        GL.GL_TEXTURE_2D,
        0,
        GL.GL_RGB,
        tx_w,
        tx_h,
        0,
        GL.GL_RGB,
        GL.GL_UNSIGNED_BYTE,
        tx_data,
    )
    GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(
        GL.GL_TEXTURE_2D,
        GL.GL_TEXTURE_MIN_FILTER,
        GL.GL_LINEAR_MIPMAP_LINEAR,
    )
    # GL_REPEAT is going to make life a lot easier
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)

    return tx_ref


def render_texture(
    tx_ref,
    display_resolution,
    coord_array,
    offset_coord,
    show_points,
    mouse_pos = None,
):
    GL.glEnable(GL.GL_TEXTURE_2D)
    GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)

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
            GL.glColor3f(1.0, 1.0, 1.0)

            if (
                mouse_pos
                and mouse_pos[0] >= point[0][0] - point_offset_x
                and mouse_pos[0] < point[0][0] + point_offset_x
                and mouse_pos[1] >= point[0][1] - point_offset_y
                and mouse_pos[1] < point[0][1] + point_offset_y
            ):
                GL.glColor3f(1.0, 0.0, 1.0)
                selected = point

            GL.glBegin(GL.GL_LINE_LOOP)
            GL.glVertex2f(point[0][0] - point_offset_x, point[0][1] - point_offset_y)
            GL.glVertex2f(point[0][0] - point_offset_x, point[0][1] + point_offset_y)
            GL.glVertex2f(point[0][0] + point_offset_x, point[0][1] + point_offset_y)
            GL.glVertex2f(point[0][0] + point_offset_x, point[0][1] - point_offset_y)
            GL.glEnd()

    return selected


def sphere_x(v):
    t = v * pi
    return (1.0 - cos(t)) / 2.0


def sphere_y(v):
    t = v * pi
    return sin(t)


def get_warp(warp_num, display_resolution):
    display_aspect = display_resolution[0] / display_resolution[1]

    match warp_num:
        case Warp.NONE:
            return np.array(
                [
                    [[0.0, 0.0], [1.0, 0.0]],
                    [[0.0, 1.0], [1.0, 1.0]],
                ],
                np.float32,
            )

        case Warp.SPHERE:
            coord_array = []
            for y in [v / SPHERE_STEPS for v in range(SPHERE_STEPS + 1)]:
                row = []
                y_scale = sphere_y(y)
                for x in [sphere_x(v / SPHERE_STEPS) for v in range(SPHERE_STEPS + 1)]:
                    row.append(
                        [(((x - 0.5) * y_scale) / display_aspect) + 0.5, sphere_x(y)],
                    )
                coord_array.append(row)

            return np.array(
                coord_array,
                np.float32,
            )

        case _:
            raise GameException(f"load_warp {warp_num} not implemented")


def lpd8_knob(data):
    _, knob, value = data
    print(knob, value)


def lpd8_pad(data):
    _, pad, on = data
    pad = Pads._pad_index[pad]
    on = on == 1
    print(pad, on)


def run():
    # args
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-f", "--fullscreen", action="store_true")
    args = parser.parse_args()

    # get the LPD8 device
    lpd8 = LPD8()
    lpd8.start()
    lpd8.set_knob_limits(LPD8_PROGRAM, Knobs.ALL_KNOBS, 0, 1, is_int=False)
    lpd8.set_pad_mode(LPD8_PROGRAM, Pads.ALL_PADS, Pad.PUSH_MODE)
    lpd8.subscribe(lpd8_knob, LPD8_PROGRAM, LPD8.CTRL, Knobs.ALL_KNOBS)
    lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_ON, Pads.ALL_PADS)
    lpd8.subscribe(lpd8_pad, LPD8_PROGRAM, LPD8.NOTE_OFF, Pads.ALL_PADS)

    # initialise the display
    pygame.init()

    display_resolution = RESOLUTION_TARGET
    display_flags = pygame.OPENGL | pygame.DOUBLEBUF
    if args.fullscreen:
        display_flags |= pygame.FULLSCREEN
    display = pygame.display.set_mode(display_resolution, display_flags, vsync=1)
    if args.fullscreen:
        display_resolution = display.get_size()

    clock = pygame.time.Clock()

    # orthographic projection - (0, 0) bottom left, (1, 1) top right
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadIdentity()

    GL.glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)

    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()

    tx_ref = load_texture("test_card.jpg")

    mx, my = None, None
    tx_x, tx_y = 0.0, 0.0
    show_points = False
    warp_num = next(iter(Warp))
    coord_array = None
    mouse_move = False
    point_move = False
    selected_point = None
    edit_point = None

    pygame.mouse.set_visible(show_points)

    try:
        while True:
            nmx, nmy = pygame.mouse.get_pos()
            ntx, nty = nmx / display_resolution[0], 1.0 - (nmy / display_resolution[1])

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        raise QuitException()

                    if event.key == pygame.K_p:
                        show_points = not show_points

                    if event.key == pygame.K_w:
                        warp_num += 1
                        if warp_num not in Warp:
                            warp_num = next(iter(Warp))

                        # reset to ensure it is reread
                        coord_array = None

                    if event.key == pygame.K_m:
                        mouse_move = not mouse_move

                        # reset texture offset
                        if not mouse_move:
                            tx_x, tx_y = 0.0, 0.0

                elif event.type == pygame.QUIT:
                    raise QuitException()

            if coord_array is None:
                coord_array = get_warp(warp_num, display_resolution)

            if point_move:
                coord_array[edit_point[1]][edit_point[0]] = [ntx, nty]

            # get texture offset from mouse move
            dmx, dmy = 0.0, 0.0
            if mouse_move and (mx != nmx or my != nmy):
                if mx is not None:
                    dmx = (nmx - mx) / display_resolution[0]
                    dmy = (nmy - my) / display_resolution[1]
                    tx_x += dmx
                    tx_y -= dmy

                mx, my = nmx, nmy

            GL.glClear(GL.GL_COLOR_BUFFER_BIT)

            selected_point = render_texture(
                tx_ref,
                display_resolution,
                coord_array,
                (tx_x, tx_y),
                show_points,
            )

            pygame.display.flip()

            lpd8.pad_update()

            clock.tick(FPS_TARGET)

    except (QuitException, KeyboardInterrupt):
        pass

    finally:
        pygame.quit()
        lpd8.stop()


if __name__ == "__main__":
    run()
