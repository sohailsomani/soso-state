import typing

from soso.event import Event, EventToken

StateT = typing.TypeVar('StateT', covariant=True)
StateT2 = typing.TypeVar('StateT2',contravariant=True)

class PropertyCallback(typing.Generic[StateT2],
                       typing.Protocol):
    def __call__(self,state:StateT2) -> typing.Any:
        ...

class EventCallback(typing.Protocol):
    def __call__(self,*args:typing.Any) -> typing.Optional[typing.Any]:
        ...

class Model(typing.Generic[StateT]):
    @typing.overload
    def update(self, **kwargs: typing.Any) -> None:
        ...

    @typing.overload
    def update(self, func: typing.Callable[[StateT], None]) -> None:
        ...

    @property
    def state(self) -> StateT:
        ...

    def subscribe(self,
                  property:PropertyCallback[StateT],
                  callback:EventCallback) -> EventToken:
        ...

    def event(self,
              property:PropertyCallback[StateT]) -> Event:
        ...
