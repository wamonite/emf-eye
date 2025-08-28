"""Shader implementation for EMF Eye."""

import logging
from typing import Self

import numpy as np
from OpenGL import GL
from OpenGL.GL import shaders

from .exceptions import ScriptError

log = logging.getLogger("shader")


class Shader:
    """Shader program wrapper."""

    def __init__(self: Self, vertex_source: str, fragment_source: str, geometry_source: str = None) -> None:
        """
        Create a shader program from vertex and fragment shader sources.

        Args:
            vertex_source (str): Vertex shader source code
            fragment_source (str): Fragment shader source code
            geometry_source (str): Optional geometry shader source code

        """
        self._program = None
        self._vao = None
        self._vbo = None
        self._ebo = None

        # Compile shaders
        vertex_shader = shaders.compileShader(vertex_source, GL.GL_VERTEX_SHADER)
        fragment_shader = shaders.compileShader(fragment_source, GL.GL_FRAGMENT_SHADER)

        geometry_shader = None
        if geometry_source:
            geometry_shader = shaders.compileShader(geometry_source, GL.GL_GEOMETRY_SHADER)

        # Create program
        self._program = GL.glCreateProgram()
        GL.glAttachShader(self._program, vertex_shader)
        GL.glAttachShader(self._program, fragment_shader)
        if geometry_shader:
            GL.glAttachShader(self._program, geometry_shader)
        GL.glLinkProgram(self._program)

        # Check for linking errors
        if not GL.glGetProgramiv(self._program, GL.GL_LINK_STATUS):
            error = GL.glGetProgramInfoLog(self._program)
            raise ScriptError(f"Shader program linking failed: {error}")

        # Clean up individual shaders
        GL.glDeleteShader(vertex_shader)
        GL.glDeleteShader(fragment_shader)
        if geometry_shader:
            GL.glDeleteShader(geometry_shader)

        # Create VAO, VBO, EBO
        self._vao = GL.glGenVertexArrays(1)
        self._vbo = GL.glGenBuffers(1)
        self._ebo = GL.glGenBuffers(1)

        self._num_indices = 0

    def use(self: Self) -> None:
        """Use this shader program."""
        GL.glUseProgram(self._program)

    def set_bool(self: Self, name: str, value: bool) -> None:
        """Set a bool uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform1i(location, 1 if value else 0)

    def set_float1(self: Self, name: str, value: float) -> None:
        """Set a float uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform1f(location, value)

    def set_float2(self: Self, name: str, x: float, y: float) -> None:
        """Set a vec2 uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform2f(location, x, y)

    def set_int(self: Self, name: str, value: int) -> None:
        """Set an int uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform1i(location, value)

    def setup_mesh(self: Self, vertices: np.ndarray, indices: np.ndarray) -> None:
        """
        Setup mesh data for rendering.
        
        Args:
            vertices (np.ndarray): Vertex data (position, texcoord)
            indices (np.ndarray): Index data for drawing

        """
        self._num_indices = len(indices)

        GL.glBindVertexArray(self._vao)

        # Load vertex data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)

        # Load index data
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL.GL_STATIC_DRAW)

        # Position + texcoord (4 floats per vertex)
        coord_size = 2 * 4
        stride = 2 * coord_size
        # Position attribute
        GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, None)
        GL.glEnableVertexAttribArray(0)
        # Texture coordinate attribute
        GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(coord_size))
        GL.glEnableVertexAttribArray(1)

        GL.glBindVertexArray(0)

    def draw_mesh(self: Self) -> None:
        """
        Draw the mesh using the current shader.
        """
        if not self._num_indices:
            return

        GL.glBindVertexArray(self._vao)
        GL.glDrawElements(GL.GL_TRIANGLES, self._num_indices, GL.GL_UNSIGNED_INT, None)
        GL.glBindVertexArray(0)

    def release(self: Self) -> None:
        """Release shader resources."""
        if self._vao:
            GL.glDeleteVertexArrays(1, [self._vao])
            self._vao = None

        if self._vbo:
            GL.glDeleteBuffers(1, [self._vbo])
            self._vbo = None

        if self._ebo:
            GL.glDeleteBuffers(1, [self._ebo])
            self._ebo = None

        if self._program:
            GL.glDeleteProgram(self._program)
            self._program = None


WARP_VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec2 aTexCoord;

out vec2 TexCoord;

void main()
{
    gl_Position = vec4(aPos.x * 2.0 - 1.0, aPos.y * 2.0 - 1.0, 0.0, 1.0);
    TexCoord = aTexCoord;
}
"""

WARP_FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

in vec2 TexCoord;

uniform sampler2D texture1;
uniform vec2 offset;

void main()
{
    vec2 tc = TexCoord + offset;
    FragColor = texture(texture1, tc);
}
"""

def create_warp_shader() -> Shader:
    """Create the warp shader."""
    return Shader(WARP_VERTEX_SHADER, WARP_FRAGMENT_SHADER)

POINT_VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in int aIsTexture;

out int isTexture;
out vec2 position;

uniform vec2 textureOffset;

void main()
{
    position = aPos;
    
    // Apply offset for texture points
    if (aIsTexture == 1) {
        position += textureOffset;
    }
    
    isTexture = aIsTexture;
}
"""

POINT_GEOMETRY_SHADER = """
#version 330 core
layout (points) in;
layout (line_strip, max_vertices = 5) out;

in int isTexture[];
in vec2 position[];

out vec3 vertexColor;

uniform float displayAspect;

void main()
{
    vec2 pos = position[0];
    
    // Convert to NDC
    float ndc_x = pos.x * 2.0 - 1.0;
    float ndc_y = (1.0 - pos.y) * 2.0 - 1.0;
    float offset_x = 0.002 * 2.0;
    float offset_y = 0.002 * 2.0 * displayAspect;
    
    // Set color: green for warp points, red for texture points
    vertexColor = (isTexture[0] == 1) ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
    
    // Generate box vertices (line loop)
    gl_Position = vec4(ndc_x - offset_x, ndc_y - offset_y, 0.0, 1.0);
    EmitVertex();
    
    gl_Position = vec4(ndc_x + offset_x, ndc_y - offset_y, 0.0, 1.0);
    EmitVertex();
    
    gl_Position = vec4(ndc_x + offset_x, ndc_y + offset_y, 0.0, 1.0);
    EmitVertex();
    
    gl_Position = vec4(ndc_x - offset_x, ndc_y + offset_y, 0.0, 1.0);
    EmitVertex();
    
    gl_Position = vec4(ndc_x - offset_x, ndc_y - offset_y, 0.0, 1.0);
    EmitVertex();
    
    EndPrimitive();
}
"""

POINT_FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

in vec3 vertexColor;

void main()
{
    FragColor = vec4(vertexColor, 1.0);
}
"""

def create_point_shader() -> Shader:
    """Create the point rendering shader."""
    return Shader(POINT_VERTEX_SHADER, POINT_FRAGMENT_SHADER, POINT_GEOMETRY_SHADER)
