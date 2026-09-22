from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "svg"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v"}


def save_uploaded_media(file_storage, folder, kind):
    """Save a validated uploaded image/video and return its public static URL."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None

    original = secure_filename(file_storage.filename or "")
    extension = Path(original).suffix.lower().lstrip(".")
    allowed = IMAGE_EXTENSIONS if kind == "image" else VIDEO_EXTENSIONS
    expected_mime = "image/" if kind == "image" else "video/"

    if not extension or extension not in allowed:
        raise ValueError("نوع الملف غير مدعوم. استخدم صورة أو فيديو مدعومًا.")

    mimetype = (getattr(file_storage, "mimetype", "") or "").lower()
    if mimetype and not mimetype.startswith(expected_mime):
        raise ValueError("نوع الملف لا يطابق نوع الوسائط المطلوب.")

    upload_dir = Path(current_app.static_folder) / "uploads" / folder
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}.{extension}"
    destination = upload_dir / filename
    file_storage.save(destination)

    return f"/static/uploads/{folder}/{filename}"
