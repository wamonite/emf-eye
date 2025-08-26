"""Shader implementation for EMF Eye."""

import logging
from typing import Self

import numpy as np
from OpenGL import GL
from OpenGL.GL import shaders

log = logging.getLogger("shader")


class Shader:
    """Shader program wrapper."""

    def __init__(self: Self, vertex_source: str, fragment_source: str) -> None:
        """
        Create a shader program from vertex and fragment shader sources.

        Args:
            vertex_source (str): Vertex shader source code
            fragment_source (str): Fragment shader source code

        """
        self._program = None
        self._vao = None
        self._vbo = None
        self._ebo = None

        # Compile shaders
        vertex_shader = shaders.compileShader(vertex_source, GL.GL_VERTEX_SHADER)
        fragment_shader = shaders.compileShader(fragment_source, GL.GL_FRAGMENT_SHADER)

        # Create program (without validation to avoid VAO binding issues during init)
        self._program = GL.glCreateProgram()
        GL.glAttachShader(self._program, vertex_shader)
        GL.glAttachShader(self._program, fragment_shader)
        GL.glLinkProgram(self._program)

        # Check for linking errors
        if not GL.glGetProgramiv(self._program, GL.GL_LINK_STATUS):
            error = GL.glGetProgramInfoLog(self._program)
            raise RuntimeError(f"Shader program linking failed: {error}")

        # Clean up individual shaders
        GL.glDeleteShader(vertex_shader)
        GL.glDeleteShader(fragment_shader)

        # Create VAO, VBO, EBO
        self._vao = GL.glGenVertexArrays(1)
        self._vbo = GL.glGenBuffers(1)
        self._ebo = GL.glGenBuffers(1)

    def use(self: Self) -> None:
        """Use this shader program."""
        GL.glUseProgram(self._program)

    def set_float(self: Self, name: str, value: float) -> None:
        """Set a float uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform1f(location, value)

    def set_vec2(self: Self, name: str, x: float, y: float) -> None:
        """Set a vec2 uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform2f(location, x, y)

    def set_vec3(self: Self, name: str, x: float, y: float, z: float) -> None:
        """Set a vec3 uniform value."""
        location = GL.glGetUniformLocation(self._program, name)
        GL.glUniform3f(location, x, y, z)

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
        GL.glBindVertexArray(self._vao)

        # Load vertex data
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL.GL_STATIC_DRAW)

        # Load index data
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self._ebo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL.GL_STATIC_DRAW)

        # Determine stride based on vertex data
        if len(vertices) % 4 == 0:  # Position + texcoord (4 floats per vertex)
            stride = 4 * 4
            # Position attribute
            GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, None)
            GL.glEnableVertexAttribArray(0)
            # Texture coordinate attribute
            GL.glVertexAttribPointer(1, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, GL.ctypes.c_void_p(2 * 4))
            GL.glEnableVertexAttribArray(1)
        else:  # Position only (2 floats per vertex)
            stride = 2 * 4
            # Position attribute only
            GL.glVertexAttribPointer(0, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, None)
            GL.glEnableVertexAttribArray(0)

        GL.glBindVertexArray(0)

    def draw_mesh(self: Self, count: int) -> None:
        """
        Draw the mesh using the current shader.
        
        Args:
            count (int): Number of indices to draw

        """
        GL.glBindVertexArray(self._vao)
        GL.glDrawElements(GL.GL_TRIANGLES, count, GL.GL_UNSIGNED_INT, None)
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


# Default shader sources
DEFAULT_VERTEX_SHADER = """
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

DEFAULT_FRAGMENT_SHADER = """
#version 330 core
out vec4 FragColor;

in vec2 TexCoord;

uniform sampler2D texture1;
uniform vec2 offset;

void main()
{
    FragColor = texture(texture1, TexCoord + offset);
}
"""

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
uniform bool invertX;

void main()
{
    vec2 tc = TexCoord;
    
    // Apply offset
    tc += offset;
    
    // Apply inversion if needed
    if (invertX) {
        tc.x = 1.0 - tc.x;
    }
    
    FragColor = texture(texture1, tc);
}
"""

def create_default_shader() -> Shader:
    """Create the default shader."""
    return Shader(DEFAULT_VERTEX_SHADER, DEFAULT_FRAGMENT_SHADER)

POINT_VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in int aIsTexture;

out vec3 vertexColor;

uniform vec2 textureOffset;

void main()
{
    vec2 pos = aPos;
    
    // Apply offset for texture points
    if (aIsTexture == 1) {
        pos += textureOffset;
    }
    
    gl_Position = vec4(pos, 0.0, 1.0);
    
    // Set color: green for warp points, red for texture points
    vertexColor = (aIsTexture == 1) ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
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

def create_warp_shader() -> Shader:
    """Create the warp shader."""
    return Shader(WARP_VERTEX_SHADER, WARP_FRAGMENT_SHADER)

def create_point_shader() -> Shader:
    """Create the point rendering shader."""
    return Shader(POINT_VERTEX_SHADER, POINT_FRAGMENT_SHADER)
