import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from core.auth import get_current_user
from core.responses import api_success


class UploadView(APIView):
    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

    def _allowed_formats(self):
        raw = getattr(settings, "UPLOAD_ALLOWED_IMAGE_FORMATS", "JPEG,PNG,WEBP")
        return {x.strip().upper() for x in raw.split(",") if x.strip()}

    def _normalize_image(self, raw_bytes: bytes):
        try:
            src = io.BytesIO(raw_bytes)
            image = Image.open(src)
            image.verify()
            src.seek(0)
            image = Image.open(src)
        except UnidentifiedImageError as exc:
            raise ValidationError({"detail": "Invalid image content"}) from exc

        img_format = (image.format or "").upper()
        if img_format not in self._allowed_formats():
            raise ValidationError({"detail": f"Unsupported image format: {img_format}"})

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        elif image.mode == "L":
            image = image.convert("RGB")

        max_w = int(getattr(settings, "UPLOAD_IMAGE_MAX_WIDTH", 1280))
        max_h = int(getattr(settings, "UPLOAD_IMAGE_MAX_HEIGHT", 1280))
        image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

        out = io.BytesIO()
        quality = int(getattr(settings, "UPLOAD_IMAGE_JPEG_QUALITY", 85))
        image.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue(), image.width, image.height

    def post(self, request):
        _user = get_current_user(request, required=True)
        file_obj = request.FILES.get("file")
        if not file_obj:
            raise ValidationError({"detail": "File is required"})

        content_type = (file_obj.content_type or "").lower()
        if content_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError({"detail": "Unsupported image mime type"})

        max_bytes = int(float(getattr(settings, "UPLOAD_MAX_FILE_MB", 5)) * 1024 * 1024)
        if file_obj.size > max_bytes:
            raise ValidationError({"detail": f"Image too large, max {max_bytes // (1024 * 1024)}MB"})

        raw = file_obj.read()
        if not raw:
            raise ValidationError({"detail": "Empty image file"})

        normalized, width, height = self._normalize_image(raw)
        if len(normalized) > max_bytes:
            raise ValidationError({"detail": f"Processed image too large, max {max_bytes // (1024 * 1024)}MB"})

        upload_dir = Path(settings.MEDIA_ROOT) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{timezone.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.jpg"
        file_path = upload_dir / filename
        with open(file_path, "wb+") as destination:
            destination.write(normalized)

        return api_success(
            data={
                "url": f"{settings.MEDIA_URL}uploads/{filename}",
                "width": width,
                "height": height,
                "size": len(normalized),
            },
            message="upload success",
        )
