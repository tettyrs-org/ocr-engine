from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Type

import numpy as np


@dataclass
class WordResult:
    text: str
    bbox: List[int]
    confidence: float


@dataclass
class OcrEngineResult:
    words: List[WordResult]
    engine_name: str
    engine_version: str
    confidence_mean: float
    duration_ms: int


class OcrEngine(ABC):
    @abstractmethod
    def recognize(self, image: np.ndarray) -> OcrEngineResult:
        ...

    @abstractmethod
    def get_name(self) -> str:
        ...

    @abstractmethod
    def get_version(self) -> str:
        ...


class OcrEngineFactory:
    _engines: Dict[str, Type[OcrEngine]] = {}

    @classmethod
    def register(cls, name: str, engine_class: Type[OcrEngine]) -> None:
        cls._engines[name] = engine_class

    @classmethod
    def create(cls, name: str, **kwargs) -> OcrEngine:
        if name not in cls._engines:
            raise ValueError(
                f"Mesin OCR tidak dikenal: {name}. Tersedia: {cls.get_available()}"
            )
        return cls._engines[name](**kwargs)

    @classmethod
    def get_available(cls) -> List[str]:
        return sorted(cls._engines)
