import base64
from urllib.parse import unquote_to_bytes, urlsplit

from fastapi import HTTPException, UploadFile, status

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
IMAGE_TOO_LARGE_DETAIL = "Image must not exceed 5 MB."
JPEG_MIME_TYPE = "image/jpeg"
ALLOWED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": JPEG_MIME_TYPE,
    ".jpeg": JPEG_MIME_TYPE,
    ".webp": "image/webp",
}


def _bad_image(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _has_valid_signature(content: bytes, mime_type: str) -> bool:
    if mime_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == JPEG_MIME_TYPE:
        return content.startswith(b"\xff\xd8\xff")
    if mime_type == "image/webp":
        return (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        )
    return False


def _validate_data_image(value: str) -> None:
    header, separator, encoded_content = value.partition(",")
    mime_type = header[5:].split(";", maxsplit=1)[0].lower()
    if (
        not separator
        or mime_type not in ALLOWED_IMAGE_TYPES.values()
        or not header.lower().endswith(";base64")
    ):
        raise _bad_image("Image data must use a supported base64 image MIME type.")
    if len(encoded_content) > 4 * ((MAX_IMAGE_SIZE_BYTES + 2) // 3):
        raise _bad_image(IMAGE_TOO_LARGE_DETAIL)
    try:
        content = base64.b64decode(encoded_content, validate=True)
    except ValueError:
        raise _bad_image("Image data is not valid base64.") from None
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise _bad_image(IMAGE_TOO_LARGE_DETAIL)
    if not _has_valid_signature(content, mime_type):
        raise _bad_image("Image content does not match its declared format.")


def _validate_remote_image_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _bad_image("Image URL must be an absolute HTTP or HTTPS URL.")

    path = unquote_to_bytes(parsed.path).decode("utf-8", errors="replace").lower()
    extension = path.rsplit("/", maxsplit=1)[-1]
    extension = f".{extension.rsplit('.', maxsplit=1)[-1]}" if "." in extension else ""
    if extension not in ALLOWED_IMAGE_TYPES:
        raise _bad_image("Image URL must end in .png, .jpg, .jpeg, or .webp.")


def validate_image_url(image_url: str | None) -> None:
    if image_url is None:
        return

    value = image_url.strip()
    if not value:
        raise _bad_image("Image URL cannot be blank.")

    if value.startswith("data:"):
        _validate_data_image(value)
    else:
        _validate_remote_image_url(value)


async def validate_image_upload(upload: UploadFile) -> None:
    filename = upload.filename or ""
    extension = f".{filename.rsplit('.', maxsplit=1)[-1]}".lower() if "." in filename else ""
    expected_mime_type = ALLOWED_IMAGE_TYPES.get(extension)
    if expected_mime_type is None:
        raise _bad_image("Image file must be PNG, JPG, JPEG, or WEBP.")
    if upload.content_type != expected_mime_type:
        raise _bad_image("Image MIME type does not match the file extension.")

    content = await upload.read(MAX_IMAGE_SIZE_BYTES + 1)
    await upload.seek(0)
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise _bad_image(IMAGE_TOO_LARGE_DETAIL)
    if not _has_valid_signature(content, expected_mime_type):
        raise _bad_image("File content is not a valid image of the declared type.")
