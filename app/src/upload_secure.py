import os
import uuid
from pathlib import Path
from typing import Optional

MAX_BYTES = 5_000_000
PNG = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


def sniff_image_type(data: bytes) -> Optional[str]:
    if not data:
        return None
    if data.startswith(PNG):
        return "image/png"
    if data.startswith(JPEG_SOI) and data.endswith(JPEG_EOI):
        return "image/jpeg"
    return None


def secure_save(base_dir: str, data: bytes) -> str:
    mt = sniff_image_type(data)
    if not mt:
        raise ValueError("bad_type")

    if len(data) > MAX_BYTES:
        raise ValueError("too_big")

    base_path = Path(base_dir)

    # Проверяем, что базовый путь не является символьной ссылкой
    if base_path.is_symlink():
        raise ValueError("root_is_symlink")

    try:
        root = base_path.resolve(strict=True)
    except FileNotFoundError:
        raise ValueError("base_dir_not_found")

    if not root.is_dir():
        raise ValueError("base_dir_not_directory")

    ext = ".png" if mt == "image/png" else ".jpg"
    name = f"{uuid.uuid4()}{ext}"

    path = (root / name).resolve()

    try:
        root_str = str(root)
        path_str = str(path)
        common = os.path.commonpath([root_str, path_str])
        if os.path.normpath(common) != os.path.normpath(root_str):
            raise ValueError("path_traversal")
    except (ValueError, OSError):
        raise ValueError("path_traversal")

    current = path
    while current != root and current != current.parent:
        if current.is_symlink():
            raise ValueError("symlink_parent")
        current = current.parent

    path.write_bytes(data)

    return str(path)
