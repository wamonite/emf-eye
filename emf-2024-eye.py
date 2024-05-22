"""
EMF 2024 eye renderer
"""

import argparse
import pygame
from OpenGL import GL
import numpy as np
from enum import IntEnum
import logging


log = logging.getLogger()
log_handler = logging.StreamHandler()
log.addHandler(log_handler)
# log.setLevel(logging.DEBUG)


FPS_TARGET = 60


class Warp(IntEnum):
    WARP_NONE = 0
    WARP_SPHERE = 1
    # WARP_CUSTOM = 2


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


def render_texture(tx_ref, display_resolution, coord_array, offset_coord, show_points):
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

            points.add((d_pos_0[0], d_pos_0[1]))
            points.add((d_pos_1[0], d_pos_1[1]))

            log.debug("s %s %s", s_x_pos, s_y_pos_0)
            log.debug("s %s %s", s_x_pos, s_y_pos_1)
            log.debug("d %s %s", d_pos_0[0], d_pos_0[1])
            log.debug("d %s %s", d_pos_1[0], d_pos_1[1])

        GL.glEnd()

    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

    if show_points:
        display_aspect = display_resolution[0] / display_resolution[1]
        point_offset_x = 0.0025
        point_offset_y = point_offset_x * display_aspect
        GL.glColor3f(1.0, 1.0, 1.0)
        for point in points:
            GL.glBegin(GL.GL_LINE_LOOP)
            GL.glVertex2f(point[0] - point_offset_x, point[1] - point_offset_y)
            GL.glVertex2f(point[0] - point_offset_x, point[1] + point_offset_y)
            GL.glVertex2f(point[0] + point_offset_x, point[1] + point_offset_y)
            GL.glVertex2f(point[0] + point_offset_x, point[1] - point_offset_y)
            GL.glEnd()


def load_warp(warp_num):
    match warp_num:
        case 0:
            return np.array(
                [
                    [[0.0, 0.0], [1.0, 0.0]],
                    [[0.0, 1.0], [1.0, 1.0]],
                ],
                np.float32,
            )

        case 1:
            return np.array(
                [
                    [[0.1, 0.1], [0.5, 0.0], [0.9, 0.1]],
                    [[0.0, 0.5], [0.5, 0.5], [1.0, 0.5]],
                    [[0.1, 0.9], [0.5, 1.0], [0.9, 0.9]],
                ],
                np.float32,
            )

        case _:
            raise GameException(f"load_warp {warp_num} not implemented")


def run():
    # args
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-f", "--fullscreen", action="store_true")
    args = parser.parse_args()

    # initialise the display
    pygame.init()
    display_resolution = (1920, 1200)
    display_flags = pygame.OPENGL | pygame.DOUBLEBUF
    if args.fullscreen:
        display_flags |= pygame.FULLSCREEN
    pygame.display.set_mode(display_resolution, display_flags, vsync=1)
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
    coord_array = load_warp(warp_num)
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        show_points = not show_points

                    if event.key == pygame.K_q:
                        raise QuitException()

                    if event.key == pygame.K_w:
                        warp_num += 1
                        if warp_num not in Warp:
                            warp_num = next(iter(Warp))

                        coord_array = load_warp(warp_num)

                elif event.type == pygame.QUIT:
                    raise QuitException()

            nmx, nmy = pygame.mouse.get_pos()
            dmx, dmy = 0.0, 0.0
            if mx != nmx or my != nmy:
                if mx is not None:
                    dmx = (nmx - mx) / display_resolution[0]
                    dmy = (nmy - my) / display_resolution[1]
                    tx_x += dmx
                    tx_y -= dmy

                mx, my = nmx, nmy

            GL.glClear(GL.GL_COLOR_BUFFER_BIT)

            render_texture(
                tx_ref,
                display_resolution,
                coord_array,
                (tx_x, tx_y),
                show_points,
            )

            pygame.display.flip()

            clock.tick(FPS_TARGET)

    except (QuitException, KeyboardInterrupt):
        pass

    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
