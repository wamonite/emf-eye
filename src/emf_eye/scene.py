"""Scenes combine video with animation."""

import json
import logging
from pathlib import Path
from timeit import default_timer as timer
from typing import Self

from .texture import Texture

log = logging.getLogger("scene")


PATH_DEFAULT = "resources/scenes"
SCENE_DEFAULT = "default"


class Scene:
    """Scene class."""

    def __init__(self: Self, path: Path) -> None:
        """
        Construct the scene, loading the scene definitions from the path.

        Args:
            path (Path): Path to the scene directory.

        """
        self._path = path

        self._name = None

        self._texture = None

        self._moves = None
        self._move_idx = 0
        self._move_start_x = 0.0
        self._move_start_y = 0.0
        self._move_start_time = None
        self._move_end_x = 0.0
        self._move_end_y = 0.0
        self._move_end_time = None

        with open(path / "scene.json") as file_object:
            self._data = json.load(file_object)

        self.validate()

    def validate(self: Self) -> None:
        """
        Validate the loaded scene definitions.

        Raises:
            FileNotFoundError: If a scene video file is not found.

        """
        for data in self._data.values():
            for file_key in ["video"]:
                if file_key in data:
                    file_path = self._path / data[file_key]
                    if not file_path.exists():
                        log.error("file not found %s", file_path)
                        raise FileNotFoundError(file_path)

    def __repr__(self: Self) -> str:
        """Return a string representation of the object."""
        return f"<scene.Scene {self._path}>"

    @property
    def fps(self: Self) -> float | None:
        """Return the video file FPS."""
        return self._texture.fps if self._texture else None

    def update_texture(self: Self) -> int | None:
        """Update the video playback."""
        return self._texture.update()

    def update_position(self: Self) -> tuple[float, float]:
        """Return the interpolated movement coordinates."""
        if not self._moves:
            return 0.0, 0.0

        move_now = timer() - self._move_start_time
        move_ratio = move_now / self._move_end_time
        if move_ratio > 1.0:
            tx_x = self._move_end_x
            tx_y = self._move_end_y
            self._next_move()

        else:
            tx_x = (
                (self._move_end_x - self._move_start_x) * move_ratio
            ) + self._move_start_x
            tx_y = (
                (self._move_end_y - self._move_start_y) * move_ratio
            ) + self._move_start_y

        return tx_x, tx_y

    @staticmethod
    def load_scenes(path: Path | None = None) -> list["Scene"]:
        """Load all the scenes in a directory."""
        if path is None:
            path = Path(PATH_DEFAULT)

        scenes = []
        for scene_path in sorted(
            [
                d
                for d in path.iterdir()
                if d.is_dir() and not str(d).endswith(".disabled")
            ],
        ):
            try:
                scenes.append(Scene(scene_path))

            except FileNotFoundError:
                log.error("invalid scene %s", scene_path)

        log.debug(scenes)

        return scenes

    def _next_move(self: Self) -> None:
        """Load the next move step."""
        self._move_start_x = self._move_end_x
        self._move_start_y = self._move_end_y

        move_idx = self._move_idx + 1
        if move_idx == len(self._moves):
            move_idx = 0

        self._set_move(move_idx)

    def _set_move(self: Self, idx: int, on_start: bool = False) -> None:
        """Set the current move steo."""
        self._move_idx = idx
        self._move_start_time = timer()
        self._move_end_x = self._moves[self._move_idx][0]
        self._move_end_y = self._moves[self._move_idx][1]
        self._move_end_time = self._moves[self._move_idx][2]

        if on_start:
            self._next_move()

    def start(
        self: Self,
        name: str = SCENE_DEFAULT,
    ) -> None:
        """Load the resources and start the scene."""
        log.debug("scene start %s %s", self._path, name)

        self._name = name

        assert not self._texture, "texture not released"
        self._texture = Texture(self._path / self._data[name]["video"])

        self._moves = None
        if "moves" in self._data[name]:
            self._moves = self._data[self._name]["moves"]
            self._set_move(0, on_start=True)

    def stop(self: Self) -> None:
        """Stop the scene and release the resources."""
        log.debug("scene stop %s", self._path)

        if self._texture:
            self._texture.release()
            self._texture = None
            self._name = None

        self._moves = []
