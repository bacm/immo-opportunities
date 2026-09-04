from pathlib import Path

from sqlalchemy import URL, make_url

from immo.config import Settings


def test_database_url_preserves_and_escapes_password(tmp_path: Path) -> None:
    password_file = tmp_path / "password"
    password_file.write_text("a+/ complex-password\n", encoding="utf-8")
    settings = Settings(database_password_file=password_file)

    url = settings.sqlalchemy_url()

    assert isinstance(url, URL)
    assert url.password == "a+/ complex-password"
    assert make_url(url.render_as_string(hide_password=False)).password == "a+/ complex-password"
