"""Тесты для безопасной загрузки файлов."""

from pathlib import Path

import pytest
from app.src.upload_secure import secure_save, sniff_image_type


def test_sniff_image_type_ok_png():
    """Проверка корректного определения PNG."""
    data = b"\x89PNG\r\n\x1a\n123"
    assert sniff_image_type(data) == "image/png"


def test_sniff_image_type_ok_jpeg():
    """Проверка корректного определения JPEG."""
    data = b"\xff\xd8" + b"data" + b"\xff\xd9"
    assert sniff_image_type(data) == "image/jpeg"


def test_sniff_image_type_bad_type():
    """Проверка, что неправильный тип возвращает None."""
    data = b"notanimage123"
    assert sniff_image_type(data) is None


def test_sniff_image_type_empty():
    """Негативный тест: пустые данные."""
    assert sniff_image_type(b"") is None


def test_sniff_image_type_incomplete_jpeg():
    """Негативный тест: неполный JPEG (нет EOI маркера)."""
    data = b"\xff\xd8" + b"data"
    assert sniff_image_type(data) is None


def test_secure_save_too_big(tmp_path: Path):
    """Негативный тест: слишком большой файл (>5MB)."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    data = b"\x89PNG\r\n\x1a\n" + b"0" * 5_000_001
    with pytest.raises(ValueError, match="too_big"):
        secure_save(str(base_dir), data)


def test_secure_save_ok(tmp_path: Path):
    """Проверка успешного сохранения корректного файла."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    data = b"\x89PNG\r\n\x1a\nhello"
    path = secure_save(str(base_dir), data)
    p = Path(path)
    assert p.exists()
    assert p.read_bytes() == data
    assert p.suffix == ".png"
    # Проверяем, что файл находится внутри базовой директории
    assert str(p).startswith(str(base_dir.resolve()))


def test_secure_save_jpeg(tmp_path: Path):
    """Проверка сохранения JPEG файла."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    data = b"\xff\xd8" + b"jpeg data" + b"\xff\xd9"
    path = secure_save(str(base_dir), data)
    p = Path(path)
    assert p.exists()
    assert p.read_bytes() == data
    assert p.suffix == ".jpg"


def test_secure_save_invalid_type(tmp_path: Path):
    """Негативный тест: неподдерживаемый тип файла."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    data = b"not an image"
    with pytest.raises(ValueError, match="bad_type"):
        secure_save(str(base_dir), data)


def test_secure_save_nonexistent_dir(tmp_path: Path):
    """Негативный тест: несуществующая базовая директория."""
    nonexistent_dir = tmp_path / "nonexistent"
    data = b"\x89PNG\r\n\x1a\n" + b"data"
    with pytest.raises(ValueError, match="base_dir_not_found"):
        secure_save(str(nonexistent_dir), data)


def test_secure_save_file_as_base_dir(tmp_path: Path):
    """Негативный тест: базовый путь указывает на файл, а не директорию."""
    base_file = tmp_path / "file.txt"
    base_file.write_text("test")
    data = b"\x89PNG\r\n\x1a\n" + b"data"
    with pytest.raises(ValueError, match="base_dir_not_directory"):
        secure_save(str(base_file), data)


def test_secure_save_generates_unique_names(tmp_path: Path):
    """Проверка, что каждый файл получает уникальное имя (UUID)."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    data = b"\x89PNG\r\n\x1a\n" + b"data"

    path1 = secure_save(str(base_dir), data)
    path2 = secure_save(str(base_dir), data)

    # Имена должны быть разными
    assert Path(path1).name != Path(path2).name
    # Но оба файла должны существовать
    assert Path(path1).exists()
    assert Path(path2).exists()
