from pathlib import Path
from OpenGL import GL
import cv2
from .exceptions import ScriptException
from typing import Optional
import pygame


class Texture:

    def __init__(self, path: Path) -> None:
        self._path = path

        self._video = None
        self._reset_video()
        self._fps = self._video.get(cv2.CAP_PROP_FPS)

        self._tx_ref = GL.glGenTextures(1)

    @property
    def fps(self) -> Optional[float]:
        return self._fps

    def _reset_video(self) -> None:
        if self._video:
            self._video.release()

        if not self._path.exists():
            raise ScriptException(f"video {self._path} not found")

        self._video = cv2.VideoCapture(str(self._path))

    def update(self) -> Optional[int]:
        if not self._tx_ref:
            return None

        cv_read_ok, cv_image = self._video.read()
        if not cv_read_ok:
            self._reset_video()
            cv_read_ok, cv_image = self._video.read()
            if not cv_read_ok:
                raise ScriptException(f"unable to load {self._path}")

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

    def release(self) -> None:
        if self._tx_ref:
            GL.glDeleteTextures([self._tx_ref])
        self._tx_ref = None

        if self._video:
            self._video.release()
            self._video = None
            self._fps = None
