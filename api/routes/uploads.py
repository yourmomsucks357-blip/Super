from pathlib import Path
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.vision import compare_face_images

router = APIRouter(prefix="/uploads", tags=["uploads"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_UPLOAD_DIR = _STATIC_DIR / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        suffix = ".png"

    target_name = f"{uuid.uuid4().hex}{suffix}"
    target_path = _UPLOAD_DIR / target_name
    data = await file.read()
    target_path.write_bytes(data)

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "url": f"/static/uploads/{target_name}",
    }


@router.post("/compare-faces")
async def compare_faces(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
):
    if file_a.content_type not in _ALLOWED_TYPES or file_b.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    try:
        image_a = await file_a.read()
        image_b = await file_b.read()
        similarity = compare_face_images(image_a, image_b)
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"Missing dependency: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Face comparison failed: {exc}")

    if similarity is None:
        raise HTTPException(status_code=400, detail="Could not detect a face in one or both images")

    return {
        "similarity": similarity,
        "same_person_likely": similarity >= 0.35,
    }
