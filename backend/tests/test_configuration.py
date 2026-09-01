from app.main import _cors_origins


def test_cors_origins_include_local_frontends(monkeypatch) -> None:
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    assert _cors_origins() == [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


def test_cors_origins_include_deployed_frontends(monkeypatch) -> None:
    monkeypatch.setenv(
        "FRONTEND_URL",
        "https://app.example.com/, https://preview.example.com",
    )

    assert "https://app.example.com" in _cors_origins()
    assert "https://preview.example.com" in _cors_origins()
