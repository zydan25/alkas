from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
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


ATTACHMENT_EXTENSIONS = {
    "pdf", "jpg", "jpeg", "png", "webp", "gif", "heic"
}

def save_uploaded_attachment(file_storage, folder="booking"):
    """Save a customer attachment such as a payment receipt."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None

    original = secure_filename(file_storage.filename or "")
    extension = Path(original).suffix.lower().lstrip(".")
    if not extension or extension not in ATTACHMENT_EXTENSIONS:
        raise ValueError("المرفق غير مدعوم. استخدم PDF أو صورة JPG/PNG/WebP.")

    mimetype = (getattr(file_storage, "mimetype", "") or "").lower()
    allowed_mimes = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
    }
    if mimetype and mimetype not in allowed_mimes:
        raise ValueError("نوع المرفق غير مسموح.")

    upload_dir = Path(current_app.static_folder) / "uploads" / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    destination = upload_dir / filename
    file_storage.save(destination)
    return {
        "url": f"/static/uploads/{folder}/{filename}",
        "name": original[:240],
        "mime": mimetype or "application/octet-stream",
    }
