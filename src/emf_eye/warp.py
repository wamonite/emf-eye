"""Texture warp calculator."""

import logging
from enum import IntEnum
from math import cos, pi, sin

import numpy as np
from OpenGL import GL

from .controller import Controller
from .exceptions import ScriptError
from .shader import create_default_shader, create_warp_shader, create_point_shader

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
        self._point_shader = None
        self._quad_vertices = None
        self._quad_indices = None

    def _init_shaders(self):
        """Initialize shaders and quad mesh data."""
        if self._default_shader is None:
            self._default_shader = create_default_shader()

        if self._warp_shader is None:
            self._warp_shader = create_warp_shader()

        if self._point_shader is None:
            self._point_shader = create_point_shader()

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

        # Bind texture
        GL.glBindTexture(GL.GL_TEXTURE_2D, tx_ref)

        # Choose shader based on warp type
        if coord_array.shape == (2, 2, 2):  # This is the shape for Warp.NONE
            # Use default shader for no warping
            self._default_shader.use()
            self._default_shader.set_int("texture1", 0)
            self._default_shader.set_vec2("offset", offset_coord[0], offset_coord[1])
            self._default_shader.draw_mesh(6)
        else:
            # Convert coord_array to vertex data for shader rendering
            self._setup_warp_mesh(coord_array, offset_coord, invert_x)
            
            self._warp_shader.use()
            self._warp_shader.set_int("texture1", 0)
            self._warp_shader.set_vec2("offset", offset_coord[0], offset_coord[1])
            self._warp_shader.set_float("invertX", 1.0 if invert_x else 0.0)
            
            # Draw the warp mesh
            self._draw_warp_mesh()

        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        
        # Render points if enabled
        selected = None
        if show_points:
            selected = self._render_points(coord_array, display_resolution, mouse_pos)
        
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

    def _render_points(self, coord_array: np.ndarray, display_resolution: tuple[int, int], mouse_pos: tuple[float, float] | None):
        """Render debug points using shaders."""
        if coord_array.shape == (2, 2, 2):  # No points for simple warp
            return None
            
        display_aspect = display_resolution[0] / display_resolution[1]
        point_offset_x = POINT_OFFSET
        point_offset_y = point_offset_x * display_aspect
        
        d_y_size, d_x_size, _ = coord_array.shape
        all_vertices = []
        all_colors = []
        selected = None
        
        # Collect all point data
        for s_y_idx in range(d_y_size - 1):
            s_y_pos_0 = s_y_idx / (d_y_size - 1)
            s_y_pos_1 = (s_y_idx + 1) / (d_y_size - 1)
            
            for s_x_idx in range(d_x_size):
                s_x_pos = s_x_idx / (d_x_size - 1)
                
                d_pos_0 = coord_array[s_y_idx, s_x_idx]
                d_pos_1 = coord_array[s_y_idx + 1, s_x_idx]
                
                # Warped points (green/magenta)
                for pos in [d_pos_0, d_pos_1]:
                    color = [0.0, 1.0, 0.0]  # Green
                    if (mouse_pos and 
                        pos[0] - point_offset_x <= mouse_pos[0] < pos[0] + point_offset_x and
                        pos[1] - point_offset_y <= mouse_pos[1] < pos[1] + point_offset_y):
                        color = [1.0, 0.0, 1.0]  # Magenta
                        selected = ((pos[0], pos[1]), (s_x_idx, s_y_idx))
                    
                    self._add_point_vertices(all_vertices, all_colors, pos[0], pos[1], point_offset_x, point_offset_y, color)
                
                # Original points (red)
                self._add_point_vertices(all_vertices, all_colors, s_x_pos, s_y_pos_0, point_offset_x, point_offset_y, [1.0, 0.0, 0.0])
        
        # Render all points in one batch
        if all_vertices:
            self._render_point_batch(all_vertices, all_colors)
        
        return selected

    def _add_point_vertices(self, vertices: list, colors: list, x: float, y: float, offset_x: float, offset_y: float, color: list[float]):
        """Add vertices for a single point box to the batch."""
        ndc_x = x * 2.0 - 1.0
        ndc_y = (1.0 - y) * 2.0 - 1.0
        ndc_offset_x = offset_x * 2.0
        ndc_offset_y = offset_y * 2.0
        
        # Add 4 vertices for the box corners
        box_vertices = [
            ndc_x - ndc_offset_x, ndc_y - ndc_offset_y,  # bottom left
            ndc_x + ndc_offset_x, ndc_y - ndc_offset_y,  # bottom right  
            ndc_x + ndc_offset_x, ndc_y + ndc_offset_y,  # top right
            ndc_x - ndc_offset_x, ndc_y + ndc_offset_y,  # top left
        ]
        vertices.extend(box_vertices)
        
        # Add color for each vertex
        for _ in range(4):
            colors.extend(color)

    def _render_point_batch(self, vertices: list, colors: list):
        """Render all points in a single batch."""
        vertex_array = np.array(vertices, dtype=np.float32)
        color_array = np.array(colors, dtype=np.float32)
        
        vao = GL.glGenVertexArrays(1)
        vbo_pos = GL.glGenBuffers(1)
        vbo_color = GL.glGenBuffers(1)
        
        GL.glBindVertexArray(vao)
        
        # Position buffer
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_pos)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertex_array.nbytes, vertex_array, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, 2 * 4, None)
        GL.glEnableVertexAttribArray(0)
        
        # Color buffer
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_color)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, color_array.nbytes, color_array, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 3 * 4, None)
        GL.glEnableVertexAttribArray(1)
        
        self._point_shader.use()
        
        # Draw each box as a line loop (4 vertices per box)
        num_boxes = len(vertices) // 8  # 8 floats per box (4 vertices * 2 coords)
        for i in range(num_boxes):
            GL.glDrawArrays(GL.GL_LINE_LOOP, i * 4, 4)
        
        GL.glBindVertexArray(0)
        GL.glDeleteBuffers(1, [vbo_pos])
        GL.glDeleteBuffers(1, [vbo_color])
        GL.glDeleteVertexArrays(1, [vao])

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
        if self._default_shader:
            self._default_shader.release()
            self._default_shader = None

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
