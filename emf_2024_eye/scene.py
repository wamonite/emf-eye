from pathlib import Path
import json
from typing import Optional, Self
from .texture import Texture
import logging


log = logging.getLogger("scene")
log.setLevel(logging.DEBUG)


PATH_DEFAULT = "scenes"
SCENE_DEFAULT = "default"


class Scene:

    def __init__(self: Self, path: Path) -> None:
        self._path = path
        self._texture = None
        self._name = None

        with open(path / "scene.json") as file_object:
            self._data = json.load(file_object)

        self.validate()

    def validate(self: Self) -> None:
        for name, data in self._data.items():
            for file_key in ["video"]:
                if file_key in data:
                    file_path = self._path / data[file_key]
                    if not file_path.exists():
                        log.error("file not found %s", file_path)
                        raise FileNotFoundError(file_path)

    def __repr__(self: Self) -> str:
        return f"<scene.Scene {self._path}>"

    @property
    def fps(self: Self) -> Optional[float]:
        return self._texture.fps if self._texture else None

    def update_texture(self: Self) -> Optional[int]:
        return self._texture.update()

    @staticmethod
    def load_scenes(path: Optional[Path] = None) -> list[Self]:
        if path is None:
            path = Path(PATH_DEFAULT)

        scenes = []
        for scene_path in sorted([d for d in path.iterdir() if d.is_dir()]):
            try:
                scenes.append(Scene(scene_path))

            except FileNotFoundError:
                log.error("invalid scene %s", scene_path)

        log.debug(scenes)

        return scenes

    def start(self: Self, name: str = SCENE_DEFAULT) -> None:
        log.debug("scene start %s %s", self._path, name)

        self._name = name
        self._texture = Texture(self._path / self._data[name]["video"])

    def stop(self: Self) -> None:
        log.debug("scene stop %s", self._path)

        if self._texture:
            self._texture.release()
            self._texture = None
            self._name = None
