"""Texture warp calculator."""

import logging
from enum import IntEnum
from math import cos, pi, sin

import numpy as np
from OpenGL import GL

from .controller import Controller
from .exceptions import ScriptError
from .shader import create_warp_shader, create_point_shader

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
        self._warp_shader = None
        self._point_shader = None
        self._coord_array_changed = True

    def _init_shaders(self):
        """Initialize shaders and quad mesh data."""
        if self._warp_shader is None:
            self._warp_shader = create_warp_shader()

        if self._point_shader is None:
            self._point_shader = create_point_shader()

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

        # Bind texture
        GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)

        # Convert coord_array to vertex data for shader rendering
        self._setup_warp_mesh(coord_array, offset_coord, invert_x)
        self._coord_array_changed = True
        
        self._warp_shader.use()
        self._warp_shader.set_int("texture1", 0)
        self._warp_shader.set_vec2("offset", offset_coord[0], offset_coord[1])
        
        # Draw the warp mesh
        self._draw_warp_mesh()

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        
        # Render points if enabled
        selected = None
        if show_points:
            selected = self._render_points(coord_array, display_resolution, mouse_pos, offset_coord)
        
        return selected

    def _setup_warp_mesh(self, coord_array: np.ndarray, offset_coord: tuple[float, float], invert_x: bool):
        """Convert coord_array to mesh data matching original render_warp behavior."""
        d_y_size, d_x_size, _ = coord_array.shape
        
        vertices = []
        indices = []
        vertex_count = 0
        
        for s_y_idx in range(d_y_size - 1):
            s_y_pos_0 = s_y_idx / (d_y_size - 1)
            s_y_pos_1 = (s_y_idx + 1) / (d_y_size - 1)
            
            for s_x_idx in range(d_x_size):
                s_x_pos = s_x_idx / (d_x_size - 1)
                if invert_x:
                    s_x_pos = 1.0 - s_x_pos
                
                d_pos_0 = coord_array[s_y_idx, s_x_idx]
                d_pos_1 = coord_array[s_y_idx + 1, s_x_idx]
                
                # Add vertices (position, texcoord)
                vertices.extend([
                    d_pos_0[0], d_pos_0[1], s_x_pos, s_y_pos_0,
                    d_pos_1[0], d_pos_1[1], s_x_pos, s_y_pos_1
                ])
                
                if s_x_idx < d_x_size - 1:
                    # Create quad with two triangles
                    indices.extend([
                        vertex_count, vertex_count + 2, vertex_count + 1,
                        vertex_count + 1, vertex_count + 2, vertex_count + 3
                    ])
                
                vertex_count += 2
        
        self._warp_vertices = np.array(vertices, dtype=np.float32)
        self._warp_indices = np.array(indices, dtype=np.uint32)
        
        # Update mesh
        self._warp_shader.setup_mesh(self._warp_vertices, self._warp_indices)

    def _draw_warp_mesh(self):
        """Draw the warp mesh."""
        if hasattr(self, '_warp_indices'):
            self._warp_shader.draw_mesh(len(self._warp_indices))

    def _render_points(self, coord_array: np.ndarray, display_resolution: tuple[int, int], mouse_pos: tuple[float, float] | None, offset_coord: tuple[float, float]):
        """Render debug points using shaders."""
        display_aspect = display_resolution[0] / display_resolution[1]
        
        if not hasattr(self, '_point_vertices') or self._coord_array_changed:
            self._update_warp_points(coord_array, display_aspect)
            self._coord_array_changed = False
        
        # Setup buffers
        vao = GL.glGenVertexArrays(1)
        vbo_pos = GL.glGenBuffers(1)
        vbo_type = GL.glGenBuffers(1)
        
        GL.glBindVertexArray(vao)
        
        # Position buffer
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_pos)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._point_vertices.nbytes, self._point_vertices, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 8, None)
        GL.glEnableVertexAttribArray(0)
        
        # Type buffer
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_type)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._point_types.nbytes, self._point_types, GL.GL_STATIC_DRAW)
        GL.glVertexAttribIPointer(1, 1, GL.GL_INT, 4, None)
        GL.glEnableVertexAttribArray(1)
        
        self._point_shader.use()
        self._point_shader.set_vec2("textureOffset", offset_coord[0] * 2.0, -offset_coord[1] * 2.0)
        
        # Draw each box as a line loop (4 vertices per box)
        for i in range(self._num_boxes):
            GL.glDrawArrays(GL.GL_LINE_LOOP, i * 4, 4)
        
        GL.glDeleteBuffers(1, [vbo_pos])
        GL.glDeleteBuffers(1, [vbo_type])
        GL.glDeleteVertexArrays(1, [vao])
        
        return None

    def _update_warp_points(self, coord_array: np.ndarray, display_aspect: float):
        """Update warp and texture point lists when coord_array changes."""
        d_y_size, d_x_size, _ = coord_array.shape
        
        # Create box template
        offset_x = POINT_OFFSET * 2.0
        offset_y = POINT_OFFSET * 2.0 * display_aspect
        box_template = np.array([
            -offset_x, -offset_y,
            offset_x, -offset_y,
            offset_x, offset_y,
            -offset_x, offset_y,
        ], dtype=np.float32)
        
        all_vertices = []
        all_types = []
        
        for s_y_idx in range(d_y_size - 1):
            for s_x_idx in range(d_x_size):
                # Warp points (from coord_array)
                for warp_pos in [coord_array[s_y_idx, s_x_idx], coord_array[s_y_idx + 1, s_x_idx]]:
                    ndc_x = warp_pos[0] * 2.0 - 1.0
                    ndc_y = (1.0 - warp_pos[1]) * 2.0 - 1.0
                    
                    for j in range(0, 8, 2):
                        all_vertices.extend([ndc_x + box_template[j], ndc_y + box_template[j+1]])
                        all_types.append(0)
                
                # Texture points (original grid)
                s_x_pos = s_x_idx / (d_x_size - 1)
                s_y_pos = s_y_idx / (d_y_size - 1)
                
                ndc_x = s_x_pos * 2.0 - 1.0
                ndc_y = (1.0 - s_y_pos) * 2.0 - 1.0
                
                for j in range(0, 8, 2):
                    all_vertices.extend([ndc_x + box_template[j], ndc_y + box_template[j+1]])
                    all_types.append(1)
        
        self._point_vertices = np.array(all_vertices, dtype=np.float32)
        self._point_types = np.array(all_types, dtype=np.int32)
        self._num_boxes = len(all_types) // 4



    def _render_point_square(self, x: float, y: float, offset_x: float, offset_y: float, color: list[float]):
        """Render a single point square using line loop."""
        # Convert from [0,1] screen coordinates to [-1,1] NDC coordinates
        ndc_x = x * 2.0 - 1.0
        ndc_y = (1.0 - y) * 2.0 - 1.0  # Flip Y
        ndc_offset_x = offset_x * 2.0
        ndc_offset_y = offset_y * 2.0
        
        # Create temporary VAO for this point
        vao = GL.glGenVertexArrays(1)
        vbo = GL.glGenBuffers(1)
        
        vertices = np.array([
            ndc_x - ndc_offset_x, ndc_y - ndc_offset_y,  # 0: bottom left
            ndc_x + ndc_offset_x, ndc_y - ndc_offset_y,  # 1: bottom right  
            ndc_x + ndc_offset_x, ndc_y + ndc_offset_y,  # 2: top right
            ndc_x - ndc_offset_x, ndc_y + ndc_offset_y,  # 3: top left
        ], dtype=np.float32)
        
        GL.glBindVertexArray(vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 2 * 4, None)
        GL.glEnableVertexAttribArray(0)
        
        self._point_shader.use()
        self._point_shader.set_vec3("color", color[0], color[1], color[2])
        
        # Draw as line strip to form a box
        GL.glDrawArrays(GL.GL_LINE_LOOP, 0, 4)
        
        GL.glBindVertexArray(0)
        GL.glDeleteBuffers(1, [vbo])
        GL.glDeleteVertexArrays(1, [vao])

    def cleanup(self):
        """Clean up shader resources."""
        if self._warp_shader:
            self._warp_shader.release()
            self._warp_shader = None

        if self._point_shader:
            self._point_shader.release()
            self._point_shader = None


def calculate_warp(
    warp_num: Warp,
    display_resolution: tuple[int, int],
    controller: Controller,
) -> np.ndarray:
    """
    Return the warp as an array of quad-strip coordinates.
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
