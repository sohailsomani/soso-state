import typing
import unittest
from unittest.mock import MagicMock

from soso.state.event import Event


class TestEvent(unittest.TestCase):
    def test_multiple_callbacks(self) -> None:
        event: Event[int] = Event("HELLO", int)
        mock1 = MagicMock()
        mock2 = MagicMock()
        event.connect(mock1)
        event.connect(mock2)
        event.emit(42)

        mock1.assert_called_with(42)
        mock2.assert_called_with(42)

    def test_disconnect_during_event(self) -> None:
        event: Event[int] = Event("HELLO", int)

        def cb(*a: typing.Any) -> None:
            token1.disconnect()

        token1 = event.connect(cb)
        mock = MagicMock()
        event.connect(mock)

        event.emit(42)

        mock.assert_called_with(42)
