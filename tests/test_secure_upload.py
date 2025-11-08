from pathlib import Path

from app.src.upload_secure import secure_save, sniff_image_type


def test_sniff_image_type_ok_png():
    """Проверка корректного определения PNG."""
    data = b"\x89PNG\r\n\x1a\n123"
    assert sniff_image_type(data) == "image/png"


def test_sniff_image_type_bad_type():
    """Проверка, что неправильный тип возвращает None."""
    data = b"notanimage123"
    assert sniff_image_type(data) is None


def test_secure_save_too_big(tmp_path: Path):
    """Проверка, что слишком большой файл не сохраняется."""
    data = b"\x89PNG\r\n\x1a\n" + b"0" * 5_000_001
    try:
        secure_save(tmp_path, data)
        assert False, "Expected ValueError('too_big')"
    except ValueError as e:
        assert str(e) == "too_big"


def test_secure_save_ok(tmp_path: Path):
    """Проверка успешного сохранения корректного файла."""
    data = b"\x89PNG\r\n\x1a\nhello"
    path = secure_save(tmp_path, data)
    p = Path(path)
    assert p.exists()
    assert p.read_bytes() == data
    assert p.suffix == ".png"
