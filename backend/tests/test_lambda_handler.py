from mangum import Mangum

from app.lambda_handler import handler


def test_lambda_handler_is_importable() -> None:
    assert isinstance(handler, Mangum)
