import typing

from soso.event import Event, EventToken

StateT = typing.TypeVar('StateT')
T = typing.TypeVar('T')


class Model(typing.Generic[StateT]):
    def subscribe(self, prop_get_func: typing.Callable[[StateT], T],
                  callback: typing.Callable[[T], typing.Any]) -> EventToken:
        ...

    @typing.overload
    def update(self, **kwargs: typing.Any) -> None:
        ...

    @typing.overload
    def update(self, func: typing.Callable[[StateT], None]) -> None:
        ...

    @property
    def state(self) -> StateT:
        ...

    def event(self, property: typing.Callable[[StateT], T]) -> Event:
        ...

    def snapshot(self) -> StateT:
        ...

    def restore(self, snapshot: StateT) -> None:
        ...
