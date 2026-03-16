"""Tests for service entry point module."""


def test_service_main_importable():
    """Verify the service main module can be imported."""
    from resources.lib.service.main import main
    assert callable(main)


def test_get_device_name_returns_string():
    """Verify _get_device_name returns a string."""
    from resources.lib.service.main import _get_device_name
    result = _get_device_name()
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_kodi_version_returns_string():
    """Verify _get_kodi_version returns a string."""
    from resources.lib.service.main import _get_kodi_version
    result = _get_kodi_version()
    assert isinstance(result, str)
