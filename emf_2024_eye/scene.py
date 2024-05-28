from pathlib import Path
import json
from typing import Optional
from .texture import Texture
import logging


log = logging.getLogger("scene")
# log.setLevel(logging.DEBUG)


PATH_DEFAULT = "scenes"
SCENE_DEFAULT = "default"


class Scene:

    def __init__(self, path: Path) -> None:
        self._path = path
        self._texture = None
        self._name = None

        with open(path / "scene.json") as file_object:
            self._data = json.load(file_object)
            print(path, self._data)

    @property
    def fps(self) -> Optional[float]:
        return self._texture.fps if self._texture else None

    def update_texture(self) -> Optional[int]:
        return self._texture.update()

    @staticmethod
    def load_scenes(path: Optional[Path] = None):
        if path is None:
            path = Path(PATH_DEFAULT)

        return [Scene(d) for d in path.iterdir() if d.is_dir()]

    def start(self, name: str = SCENE_DEFAULT) -> None:
        self._name = name
        self._texture = Texture(self._path / self._data[name]["video"])

    def stop(self) -> None:
        if self._texture:
            self._texture.release()
            self._texture = None
            self._name = None
