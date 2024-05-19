"""
EMF 2024 eye renderer
"""

import argparse
import pygame
from OpenGL import GL


FPS_TARGET = 60


class QuitException(Exception):
    pass


class GameException(Exception):
    pass


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

    tx_ref = GL.glGenTextures(1)
    tx_surface = pygame.image.load("test_card.jpg")

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

    mx, my = None, None
    tx_x, tx_y = 0.0, 0.0
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        raise QuitException()

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

            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)

            GL.glBegin(GL.GL_QUADS)
            GL.glTexCoord2f(tx_x + 0.0, tx_y + 0.0)
            GL.glVertex3f(0.0, 0.0, 0.0)
            GL.glTexCoord2f(tx_x + 1.0, tx_y + 0.0)
            GL.glVertex3f(1.0, 0.0, 0.0)
            GL.glTexCoord2f(tx_x + 1.0, tx_y + 1.0)
            GL.glVertex3f(1.0, 1.0, 0.0)
            GL.glTexCoord2f(tx_x + 0.0, tx_y + 1.0)
            GL.glVertex3f(0.0, 1.0, 0.0)
            GL.glEnd()

            pygame.display.flip()

            clock.tick(FPS_TARGET)

    except (QuitException, KeyboardInterrupt):
        pass

    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
