"""Texture warp calculator."""

import logging
from enum import IntEnum
from math import cos, pi, sin

import numpy as np
from OpenGL import GL

from .controller import Controller
from .exceptions import ScriptError
from .shader import create_default_shader, create_warp_shader

log = logging.getLogger("warp")


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
    """Warp type enum."""

    PARAMETER = 0
    NONE = 1


class WarpRenderer:
    """Manages warp rendering with shaders."""

    def __init__(self):
        self._default_shader = None
        self._warp_shader = None
        self._quad_vertices = None
        self._quad_indices = None

    def _init_shaders(self):
        """Initialize shaders and quad mesh data."""
        if self._default_shader is None:
            self._default_shader = create_default_shader()

        if self._warp_shader is None:
            self._warp_shader = create_warp_shader()

        if self._quad_vertices is None:
            # Create a full screen quad with position and texture coordinates
            self._quad_vertices = np.array([
                # positions    # texture coords
                0.0, 0.0,      0.0, 0.0,  # bottom left
                1.0, 0.0,      1.0, 0.0,  # bottom right
                1.0, 1.0,      1.0, 1.0,  # top right
                0.0, 1.0,      0.0, 1.0,   # top left
            ], dtype=np.float32)

            self._quad_indices = np.array([
                0, 1, 2,  # first triangle
                0, 2, 3,   # second triangle
            ], dtype=np.uint32)

            # Setup the mesh for both shaders
            self._default_shader.setup_mesh(self._quad_vertices, self._quad_indices)
            self._warp_shader.setup_mesh(self._quad_vertices, self._quad_indices)

    def render(
        self,
        tx_ref: int,
        display_resolution: tuple[int, int],
        coord_array: np.ndarray,
        offset_coord: tuple[float, float],
        show_points: bool,
        invert_x: bool = False,
        mouse_pos: tuple[float, float] | None = None,
    ) -> tuple[tuple[float, float], tuple[int, int]] | None:
        """Render a warp to the display using shaders."""
        # Initialize shaders if needed
        self._init_shaders()

        # Bind texture (no need to enable GL_TEXTURE_2D in Core Profile)
        GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)

        # Choose shader based on warp type
        if coord_array.shape == (2, 2, 2):  # This is the shape for Warp.NONE
            # Use default shader for no warping
            self._default_shader.use()
            self._default_shader.set_int("texture1", 0)
            self._default_shader.set_vec2("offset", offset_coord[0], offset_coord[1])
            self._default_shader.draw_mesh(6)  # 6 indices for 2 triangles
        else:
            # Use warp shader for parameter warping
            self._warp_shader.use()
            self._warp_shader.set_int("texture1", 0)
            self._warp_shader.set_vec2("offset", offset_coord[0], offset_coord[1])
            self._warp_shader.set_float("invertX", 1.0 if invert_x else 0.0)

            # Set controller parameters
            from .controller import Controller
            controller = Controller()

            # Set shader uniforms from controller values
            self._warp_shader.set_float("xPos", controller._knobs[KNOB_X_POS])
            self._warp_shader.set_float("xFan", controller._knobs[KNOB_X_FAN])
            self._warp_shader.set_float("aspect", display_resolution[0] / display_resolution[1])
            self._warp_shader.set_float("yPos", controller._knobs[KNOB_Y_POS])
            self._warp_shader.set_float("yFan", controller._knobs[KNOB_Y_FAN])

            self._warp_shader.draw_mesh(6)  # 6 indices for 2 triangles

        # Unbind texture
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

        # If showing points is enabled, draw them using immediate mode
        # NOTE: Disabled for OpenGL Core Profile compatibility
        # TODO: Implement debug point rendering using modern OpenGL
        selected = None
        if show_points:
            # Legacy immediate mode rendering not available in Core Profile
            # Would need to implement using shaders and VAOs
            pass

        return selected

    def cleanup(self):
        """Clean up shader resources."""
        if self._default_shader:
            self._default_shader.release()
            self._default_shader = None

        if self._warp_shader:
            self._warp_shader.release()
            self._warp_shader = None


def calculate_warp(
    warp_num: Warp,
    display_resolution: tuple[int, int],
    controller: Controller,
) -> np.ndarray:
    """
    Return the warp as an array of quad-strip coordinates.
    
    Note: This function is kept for compatibility but is no longer used
    for rendering with shaders.
    """
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

    raise ScriptError(f"load_warp {warp_num} not implemented")
