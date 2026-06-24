"""Tests for UI entry point module."""

from unittest.mock import MagicMock, patch


def test_signal_force_sync_sets_flag_when_enabled():
    from resources.lib.ui import main
    window = MagicMock()
    with patch.object(main, 'get_bool_setting', return_value=True):
        main._signal_force_sync_on_open(window)
    window.setProperty.assert_called_once_with('EasyTV.force_sync', '1')


def test_signal_force_sync_noop_when_disabled():
    from resources.lib.ui import main
    window = MagicMock()
    with patch.object(main, 'get_bool_setting', return_value=False):
        main._signal_force_sync_on_open(window)
    window.setProperty.assert_not_called()


def test_ui_main_importable():
    """Verify the UI main module can be imported."""
    from resources.lib.ui.main import main
    assert callable(main)


def test_main_entry_importable():
    """Verify main_entry is importable."""
    from resources.lib.ui.main import main_entry
    assert callable(main_entry)


def test_handle_special_modes_importable():
    """Verify _handle_special_modes is importable."""
    from resources.lib.ui.main import _handle_special_modes
    assert callable(_handle_special_modes)


def test_check_service_running_importable():
    """Verify _check_service_running is importable."""
    from resources.lib.ui.main import _check_service_running
    assert callable(_check_service_running)


def test_handle_version_mismatch_importable():
    """Verify _handle_version_mismatch is importable."""
    from resources.lib.ui.main import _handle_version_mismatch
    assert callable(_handle_version_mismatch)


def test_get_population_importable():
    """Verify _get_population is importable."""
    from resources.lib.ui.main import _get_population
    assert callable(_get_population)


def test_get_skin_setting_importable():
    """Verify _get_skin_setting is importable."""
    from resources.lib.ui.main import _get_skin_setting
    assert callable(_get_skin_setting)
