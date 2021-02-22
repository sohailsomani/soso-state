import asyncio
import unittest
from unittest.mock import MagicMock

from soso.state.event import Event


async def waitfor(event: Event[int], mock: MagicMock) -> None:
    result = await event
    mock(result)


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

    def test_multiple_await(self) -> None:
        # This has nothing to do with asyncio, the original problem was that
        # event handlers can disconnect and that was made obvious when using
        # await during a single event's handling from test_Stream
        event: Event[int] = Event("HELLO2", int)
        mock1 = MagicMock()
        mock2 = MagicMock()

        t1 = asyncio.get_event_loop().create_task(waitfor(event, mock1))
        t2 = asyncio.get_event_loop().create_task(waitfor(event, mock2))
        asyncio.get_event_loop().call_soon(lambda: event.emit(42))

        fut = asyncio.gather(t1, t2)
        asyncio.get_event_loop().run_until_complete(fut)

        mock1.assert_called_with(42)
        mock2.assert_called_with(42)
