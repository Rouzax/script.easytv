#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the service liveness fast path.

The UI used to prove the service alive with a marco/polo round trip on every
launch. The service can only answer between operations, so a launch landing
inside a long blocking JSON-RPC call waited for it to finish: measured at 2.88s
on the reporter's box, with a 5s timeout beyond which the UI ejects the user
with a restart prompt.

The service now also publishes a timestamp. A fresh one proves liveness with no
round trip. Anything else falls back to the original handshake, so a wrong
threshold, a clock jump or an older service costs at most today's behaviour and
never a wrongful "service not running".
"""
import time
from unittest.mock import MagicMock, patch

from resources.lib.constants import (
    PROP_SERVICE_HEARTBEAT,
    PROP_SERVICE_RUNNING,
    SERVICE_HEARTBEAT_MAX_AGE_S,
)


def _window(props):
    win = MagicMock()
    win.getProperty.side_effect = lambda k: props.get(k, '')
    return win


class TestLivenessFastPath:

    def test_fresh_heartbeat_passes_without_a_handshake(self):
        from resources.lib.ui.main import _check_service_running
        win = _window({PROP_SERVICE_HEARTBEAT: str(time.time())})

        assert _check_service_running(win) is True
        # No handshake: the UI must not have written 'marco'
        assert not [c for c in win.setProperty.call_args_list
                    if c[0][1] == 'marco']

    def test_absent_heartbeat_falls_back_to_the_handshake(self):
        """An older service publishes no timestamp; clones rely on this."""
        from resources.lib.ui.main import _check_service_running
        props = {PROP_SERVICE_RUNNING: 'polo'}
        win = _window(props)

        assert _check_service_running(win) is True
        assert [c for c in win.setProperty.call_args_list
                if c[0][1] == 'marco'], "should have fallen back to marco"

    def test_stale_heartbeat_falls_back_rather_than_declaring_death(self):
        """A service blocked longer than the threshold is busy, not dead."""
        from resources.lib.ui.main import _check_service_running
        old = time.time() - (SERVICE_HEARTBEAT_MAX_AGE_S + 30)
        props = {PROP_SERVICE_HEARTBEAT: str(old),
                 PROP_SERVICE_RUNNING: 'polo'}
        win = _window(props)

        assert _check_service_running(win) is True
        assert [c for c in win.setProperty.call_args_list
                if c[0][1] == 'marco'], "should have fallen back to marco"

    def test_future_dated_heartbeat_falls_back(self):
        """A backwards clock correction must not look infinitely fresh."""
        from resources.lib.ui.main import _check_service_running
        props = {PROP_SERVICE_HEARTBEAT: str(time.time() + 3600),
                 PROP_SERVICE_RUNNING: 'polo'}
        win = _window(props)

        assert _check_service_running(win) is True
        assert [c for c in win.setProperty.call_args_list
                if c[0][1] == 'marco']

    def test_garbage_heartbeat_falls_back(self):
        from resources.lib.ui.main import _check_service_running
        props = {PROP_SERVICE_HEARTBEAT: 'not-a-number',
                 PROP_SERVICE_RUNNING: 'polo'}
        win = _window(props)

        assert _check_service_running(win) is True
        assert [c for c in win.setProperty.call_args_list
                if c[0][1] == 'marco']

    @patch('resources.lib.ui.main.xbmc')
    def test_dead_service_still_reports_missing(self, _mock_xbmc):
        """No heartbeat and no answer: the ejection path must still work."""
        from resources.lib.ui.main import _check_service_running
        win = _window({PROP_SERVICE_RUNNING: 'marco'})

        assert _check_service_running(win) is False


class TestServiceHeartbeatPublishing:

    @patch('resources.lib.utils.xbmcgui')
    def test_publishes_a_timestamp(self, mock_gui):
        from resources.lib.utils import service_heartbeat
        win = MagicMock()
        win.getProperty.return_value = ''
        mock_gui.Window.return_value = win

        service_heartbeat()

        stamped = [c for c in win.setProperty.call_args_list
                   if c[0][0] == PROP_SERVICE_HEARTBEAT]
        assert stamped, "no heartbeat timestamp published"
        assert abs(float(stamped[-1][0][1]) - time.time()) < 5

    @patch('resources.lib.utils.xbmcgui')
    def test_still_answers_marco_for_older_clone_uis(self, mock_gui):
        from resources.lib.utils import service_heartbeat
        win = MagicMock()
        win.getProperty.side_effect = lambda k: (
            'marco' if k == PROP_SERVICE_RUNNING else '')
        mock_gui.Window.return_value = win

        service_heartbeat()

        win.setProperty.assert_any_call(PROP_SERVICE_RUNNING, 'polo')
