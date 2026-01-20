import importlib


def test_rich_click_importable():
    assert importlib.import_module("rich_click") is not None
