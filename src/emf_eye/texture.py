"""Video as an OpenGL texture."""

import logging
from pathlib import Path
from typing import Self

import cv2
import pygame
from OpenGL import GL

from .exceptions import ScriptError

log = logging.getLogger("texture")


class Texture:
    """Texture class."""

    def __init__(self: Self, path: Path) -> None:
        """Load the video from a file."""
        self._path = path

        self._video: cv2.VideoCapture | None = None
        self._reset_video()
        self._fps = self._video.get(cv2.CAP_PROP_FPS)

        self._tx_ref = GL.glGenTextures(1)

    @property
    def fps(self: Self) -> float | None:
        """Get the video FPS if available."""
        return self._fps

    def _reset_video(self: Self) -> None:
        """Release and reload the video."""
        if self._video:
            self._video.release()

        if not self._path.exists():
            raise ScriptError(f"video {self._path} not found")

        self._video = cv2.VideoCapture(str(self._path))

    def update(self: Self) -> int | None:
        """Update the texture with a new frame."""
        if not self._tx_ref:
            return None

        cv_read_ok, cv_image = self._video.read()
        if not cv_read_ok:
            self._reset_video()
            cv_read_ok, cv_image = self._video.read()
            if not cv_read_ok:
                raise ScriptError(f"unable to load {self._path}")

        tx_h, tx_w, _ = cv_image.shape
        tx_surface = pygame.image.frombuffer(
            cv_image.tobytes(),
            cv_image.shape[1::-1],
            "BGR",
        )
        tx_data = pygame.image.tobytes(tx_surface, "RGB", True)

        GL.glBindTexture(GL.GL_TEXTURE_2D, self._tx_ref)
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

        return self._tx_ref

    def release(self: Self) -> None:
        """Release the video and texture resources."""
        if self._tx_ref:
            GL.glDeleteTextures([self._tx_ref])
        self._tx_ref = None

        if self._video:
            self._video.release()
            self._video = None
            self._fps = None
