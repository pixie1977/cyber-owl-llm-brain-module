# Модель для входных данных
from typing import List

from pydantic import BaseModel


class TextRequest(BaseModel):
    text: str

class FaceDetection(BaseModel):
    bbox: List[int]  # [x1, y1, x2, y2]
    name: str
    confidence: float

class DetectionRequest(BaseModel):
    timestamp: str
    faces: List[FaceDetection]
    success: bool
