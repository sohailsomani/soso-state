import asyncio
import logging
import typing
import weakref

T = typing.TypeVar('T')
T_contra = typing.TypeVar('T_contra', contravariant=True)

__all__ = ['Event', 'EventToken']


class EventCallback(typing.Generic[T_contra], typing.Protocol):
    def __call__(self, __value: T_contra) -> None:
        ...


class _LoggerInterface(typing.Protocol):
    def info(self, msg: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        ...

    def debug(self, msg: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        ...

    def error(self, msg: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        ...

    def exception(self, msg: typing.Any, *args: typing.Any, **kwargs: typing.Any) -> None:
        ...


class _DummyLogger:
    def info(self, msg, *args, **kwargs):  # type: ignore
        pass

    def debug(self, msg, *args, **kwargs):  # type: ignore
        pass

    def error(self, msg: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        pass

    def exception(self, msg: typing.Any, *args: typing.Any, **kwargs: typing.Any) -> None:
        pass


class Event(typing.Generic[T]):
    def __init__(self, name: str, *arg_types: type, **kwarg_types: type):
        self._name = name
        self._handlers: typing.List[typing.Tuple["EventToken", EventCallback[T]]] = []

    _logger: typing.ClassVar[_LoggerInterface] = _DummyLogger()

    @staticmethod
    def _initialize_logging() -> None:
        Event._logger = logging.getLogger(__name__)
        Event._logger.info("Event logger initialized")

    def __call__(self, __value: T) -> None:
        self._logger.debug("EMITTING: %s", self._name)
        for _, f in self._handlers:
            try:
                f(__value)
            except Exception as e:
                self._logger.error("Exception occurred when emitting event")
                self._logger.exception(e)

    def emit(self, __value: T) -> None:
        self(__value)

    def connect(self, f: EventCallback[T]) -> "EventToken":
        token = self._new_token()
        self._handlers.append((token, f))
        return token

    def disconnect_token(self, token: "EventToken") -> None:
        for i in range(len(self._handlers)):
            if id(self._handlers[i][0]) == id(token):
                # Create a copy of the handlers array just in case this is
                # happening in an event callback
                self._handlers = [h for h in self._handlers if id(h[0]) != id(token)]
                break

    def _new_token(self) -> "EventToken":
        return EventToken(self)

    def __await__(self) -> typing.Generator[None, None, T]:
        def callback(arg: T) -> None:
            assert not fut.done()
            token.disconnect()
            fut.set_result(arg)

        fut: asyncio.Future[T] = asyncio.Future()
        token = self.connect(callback)
        return fut.__await__()

    async def __aiter__(self) -> typing.AsyncGenerator[T, T]:
        q: asyncio.Queue[T] = asyncio.Queue()

        def callback(arg: T) -> None:
            q.put_nowait(arg)

        token = self.connect(callback)

        try:
            while True:
                value: T = await q.get()
                yield value
        finally:
            token.disconnect()


class EventToken:
    def __init__(self, event: Event[T]):
        self.event: typing.Optional[weakref.ReferenceType[Event[T]]] = weakref.ref(event)

    def disconnect(self) -> None:
        if self.event is None:
            return
        event = self.event()
        if event is None:
            return
        event.disconnect_token(self)
        self.event = None

    def __del__(self) -> None:
        self.disconnect()
