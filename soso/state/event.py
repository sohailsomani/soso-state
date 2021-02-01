import asyncio
import typing
import weakref


class EventToken:
    def __init__(self, event: "Event"):
        self.event: typing.Optional[
            weakref.ReferenceType["Event"]] = weakref.ref(event)

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


EventCallback = typing.Callable  # type: ignore


class Event:
    def __init__(self, name: str, *argTypes: type, **kwArgTypes: type):
        self._name = name
        self._handlers: typing.List[typing.Tuple[EventToken,
                                                 EventCallback]] = []

    def __call__(self, *a: typing.Any, **kw: typing.Any) -> None:
        for _, f in self._handlers:
            f(*a, **kw)

    def emit(self, *a: typing.Any, **kw: typing.Any) -> None:
        self(*a, **kw)

    def connect(self, f: EventCallback) -> EventToken:
        token = self._new_token()
        self._handlers.append((token, f))
        return token

    def disconnect_token(self, token: EventToken) -> None:
        for i in range(len(self._handlers)):
            if id(self._handlers[i][0]) == id(token):
                del self._handlers[i]
                break

    def _new_token(self) -> EventToken:
        return EventToken(self)

    def __await__(self) -> typing.Generator[typing.Any, None, typing.Any]:
        def callback(*args: typing.Any) -> None:
            if not fut.done():
                if len(args) == 1:
                    fut.set_result(args[0])
                else:
                    fut.set_result(args)

        fut: asyncio.Future[typing.Any] = asyncio.Future()
        token = self.connect(callback)
        fut.add_done_callback(lambda f: token.disconnect())
        return fut.__await__()
