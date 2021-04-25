import typing
import asyncio
import unittest
from unittest.mock import MagicMock
import datetime as dt

from soso.state.event import Event, TimerEvent


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

    def test_sample(self) -> None:
        timer: Event[None] = Event("Timer")
        event: Event[int] = Event("HELLO", int)
        sampled: Event[int] = event.sample(timer)

        mock = MagicMock()
        sampled.connect(mock)

        event.emit(42)
        mock.assert_not_called()

        timer.emit(None)
        mock.assert_called()

    def test_sample_ergonomic(self) -> None:
        event: Event[int] = Event("HELLO", int)
        sampled: Event[int] = event.sample(dt.timedelta(seconds=0.25))

        mock = MagicMock()
        sampled.connect(mock)

        event.emit(42)
        mock.assert_not_called()

        task = asyncio.get_event_loop().create_task(self.__sleep(dt.timedelta(seconds=1.5)))
        asyncio.get_event_loop().run_until_complete(task)

        # Even though the timer would have triggered a few times, the mock is
        # only called once since the event was only emitted once
        assert mock.call_count == 1

    def test_timer(self) -> None:
        timer: TimerEvent = TimerEvent("Timer", dt.timedelta(seconds=0.25))
        mock = MagicMock()
        timer.connect(mock)

        mock.assert_not_called()

        task = asyncio.get_event_loop().create_task(self.__sleep(dt.timedelta(seconds=1.5)))
        asyncio.get_event_loop().run_until_complete(task)

        assert 4 <= mock.call_count <= 8

    async def __sleep(self, interval: dt.timedelta) -> None:
        await asyncio.sleep(interval.total_seconds())
