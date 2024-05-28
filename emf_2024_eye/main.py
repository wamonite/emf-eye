"""
EMF 2024 eye renderer
"""

import argparse
import pygame
from OpenGL import GL
from .controller import Controller
from .scene import Scene
from .exceptions import QuitException
from .warp import Warp, calculate_warp, render_warp
import logging


log = logging.getLogger()
log_handler = logging.StreamHandler()
log.addHandler(log_handler)
# log.setLevel(logging.DEBUG)


RESOLUTION_TARGET = (1920, 1080)
FPS_DEFAULT = 25


def run() -> None:
    # args
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-f", "--fullscreen", action="store_true")
    parser.add_argument("-i", "--invert", action="store_true")
    args = parser.parse_args()

    # initialise controller
    controller = Controller()

    # initialise the display
    pygame.init()

    display_resolution = RESOLUTION_TARGET
    display_flags = pygame.OPENGL | pygame.DOUBLEBUF
    if args.fullscreen:
        display_flags |= pygame.FULLSCREEN
    display = pygame.display.set_mode(display_resolution, display_flags, vsync=1)
    if args.fullscreen:
        display_resolution = display.get_size()

    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()

    # orthographic projection - (0, 0) bottom left, (1, 1) top right
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glLoadIdentity()

    GL.glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)

    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()

    # initliase scenes
    scenes = Scene.load_scenes()
    scene_idx = 0
    scene = scenes[scene_idx]
    scene.start()

    show_points = False
    warp_num = next(iter(Warp))
    coord_array = None
    mouse_move = False

    try:
        while True:
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

                    if event.key == pygame.K_l:
                        controller.load_defaults()

                    if event.key == pygame.K_s:
                        controller.save_defaults()

                    if event.key == pygame.K_RIGHT:
                        scene_idx += 1
                        if scene_idx == len(scenes):
                            scene_idx = 0

                        scene.stop()
                        scene = scenes[scene_idx]
                        scene.start()

                    if event.key == pygame.K_LEFT:
                        scene_idx -= 1
                        if scene_idx < 0:
                            scene_idx = len(scenes) - 1

                        scene.stop()
                        scene = scenes[scene_idx]
                        scene.start()

                elif event.type == pygame.QUIT:
                    raise QuitException()

            if controller.updated:
                coord_array = None

            if coord_array is None:
                coord_array = calculate_warp(warp_num, display_resolution, controller)

            GL.glClear(GL.GL_COLOR_BUFFER_BIT)

            # get texture offset from mouse move
            if mouse_move:
                mx, my = pygame.mouse.get_pos()

                tx_x = 0.5 - (mx / display_resolution[0])
                tx_y = 0.5 + (my / display_resolution[1])

            else:
                tx_x, tx_y = 0.0, 0.0

            tx_ref = scene.update_texture()

            render_warp(
                tx_ref,
                display_resolution,
                coord_array,
                (tx_x, tx_y),
                show_points,
                args.invert,
            )

            pygame.display.flip()

            controller.update()

            clock.tick(scene.fps or FPS_DEFAULT)

    except (QuitException, KeyboardInterrupt):
        pass

    finally:
        scene.stop()
        pygame.quit()
        controller.stop()
