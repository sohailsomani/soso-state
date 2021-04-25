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

    async def __emit_continuous(self, event: Event[int], start_value: int) -> None:
        while True:
            event.emit(start_value)
            start_value += 1
            await asyncio.sleep(0.01)

    def test_sample_ergonomic(self) -> None:
        event: Event[int] = Event("HELLO", int)
        sampled: Event[int] = event.sample(dt.timedelta(seconds=0.25))

        mock = MagicMock()
        sampled.connect(mock)

        mock2 = MagicMock()
        event.connect(mock2)  # so we can grab the last value of __emit_continuous

        asyncio.get_event_loop().create_task(self.__emit_continuous(event, 1))

        task = asyncio.get_event_loop().create_task(self.__sleep(dt.timedelta(seconds=1.5)))
        asyncio.get_event_loop().run_until_complete(task)

        # The source event was triggered at least 100 times
        assert mock2.call_args_list[-1].args[-1] > 100

        # Even though the source event would have triggered many times, the
        # mock is only called a few times (should be 6 but we allow
        # flexibility)
        assert 5 <= mock.call_count <= 7

    def test_timer(self) -> None:
        timer: TimerEvent = TimerEvent("Timer", dt.timedelta(seconds=0.25))
        mock = MagicMock()
        timer.connect(mock)

        mock.assert_not_called()

        task = asyncio.get_event_loop().create_task(self.__sleep(dt.timedelta(seconds=1.5)))
        asyncio.get_event_loop().run_until_complete(task)

        # Technically, should only happen 6 times but we allow flexibility
        assert 5 <= mock.call_count <= 7

    async def __sleep(self, interval: dt.timedelta) -> None:
        await asyncio.sleep(interval.total_seconds())
