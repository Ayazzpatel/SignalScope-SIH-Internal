from abc import ABC, abstractmethod

from PIL import Image

from .types import Detection


class Detector(ABC):
    """Interface every detector implementation must satisfy.

    `load()` is called once at startup; `predict()` is called per image from a worker thread.
    """

    name: str

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def predict(self, image: Image.Image) -> Detection: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @property
    @abstractmethod
    def is_ready(self) -> bool: ...
