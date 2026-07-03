from __future__ import annotations

from typing import Optional

import numpy as np

_face_app = None


def _get_face_app():
    global _face_app
    if _face_app is None:
        import insightface
        from insightface.app import FaceAnalysis

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        _face_app = FaceAnalysis(name="buffalo_l", providers=providers)
        try:
            _face_app.prepare(ctx_id=0)
        except Exception:
            _face_app.prepare(ctx_id=-1)
    return _face_app


def get_face_embedding(image_bytes: bytes) -> Optional[np.ndarray]:
    import cv2

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        return None

    faces = _get_face_app().get(image)
    if not faces:
        return None

    face = max(
        faces,
        key=lambda item: (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1]),
    )
    return face.normed_embedding


def compare_face_images(image_a: bytes, image_b: bytes) -> Optional[float]:
    emb_a = get_face_embedding(image_a)
    emb_b = get_face_embedding(image_b)
    if emb_a is None or emb_b is None:
        return None
    return float(np.dot(emb_a, emb_b))