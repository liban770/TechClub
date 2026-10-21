import io
from PIL import Image
from django.core.exceptions import ValidationError

ALLOWED_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
DEFAULT_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

def validate_uploaded_image(file_obj, max_size_bytes=DEFAULT_MAX_IMAGE_SIZE, max_size_mb=None):
    """
    Strict security validator for image file uploads:
    1. Enforces strict file size limits (defeats storage exhaustion DoS).
    2. Validates declared MIME type against a strict whitelist.
    3. Validates file header and structure using Pillow (defeats disguised scripts & corrupted payloads).
    4. Guards against decompression bombs (pixel flood attacks).
    """
    if not file_obj:
        return None

    if max_size_mb is not None:
        max_size_bytes = int(max_size_mb * 1024 * 1024)

    # 1. Enforce size limit
    if file_obj.size > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise ValidationError(f"File size exceeds the {max_mb}MB limit. Current size: {file_obj.size / (1024 * 1024):.1f}MB.")

    # 2. Enforce declared MIME type
    content_type = getattr(file_obj, 'content_type', '').lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError("Invalid file type. Only JPEG, PNG, and WebP images are allowed.")

    # 3. Deep image inspection using Pillow
    try:
        # Prevent Decompression Bomb DoS
        Image.MAX_IMAGE_PIXELS = 25000000  # Max 25 megapixels
        
        # Read the file header
        file_obj.seek(0)
        img = Image.open(file_obj)
        img.verify()  # Verifies image integrity without executing code

        if img.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(f"Unsupported image format ({img.format}). Allowed: JPEG, PNG, WebP.")

        # Reset pointer for subsequent Django storage write
        file_obj.seek(0)
        return file_obj

    except Exception as e:
        file_obj.seek(0)
        if isinstance(e, ValidationError):
            raise
        raise ValidationError("Corrupted or invalid image file. Please upload a genuine JPG, PNG, or WebP.")

ALLOWED_DOC_EXTENSIONS = {'.pdf', '.ppt', '.pptx', '.xls', '.xlsx', '.csv', '.doc', '.docx', '.zip'}
DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.sh', '.cmd', '.php', '.py', '.js', '.vbs', '.msi', '.jar', '.scr', '.html', '.htm', '.svg'}
DEFAULT_MAX_DOC_SIZE = 25 * 1024 * 1024  # 25 MB

def validate_uploaded_document(file_obj, max_size_bytes=DEFAULT_MAX_DOC_SIZE):
    """
    Validates uploaded event resources (PDF, PPT, Excel, Word, ZIP):
    1. Blocks dangerous executable extensions.
    2. Allows only verified document extensions.
    3. Enforces a 25MB maximum file size limit.
    """
    if not file_obj:
        return None

    import os
    ext = os.path.splitext(file_obj.name)[1].lower()

    if ext in DANGEROUS_EXTENSIONS:
        raise ValidationError(f"Security Alert: Executable or script files ({ext}) are strictly forbidden.")

    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise ValidationError(f"Unsupported file format ({ext}). Allowed: PDF, PPT, PPTX, Excel (XLSX, CSV), Word (DOCX), and ZIP archives.")

    if file_obj.size > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise ValidationError(f"File size exceeds {max_mb}MB limit. Current size: {file_obj.size / (1024 * 1024):.1f}MB.")

    return file_obj
