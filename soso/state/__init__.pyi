import typing

from soso.event import Event, EventToken

StateT_contra = typing.TypeVar('StateT_contra', contravariant=True)
StateT = typing.TypeVar('StateT')
T = typing.TypeVar('T')
T_contra = typing.TypeVar('T_contra', contravariant=True)
T_co = typing.TypeVar('T_co', covariant=True)


class EventCallback(typing.Generic[T_contra], typing.Protocol):
    def __call__(self, __value: T_contra) -> typing.Optional[typing.Any]:
        ...


class PropertyCallback(typing.Generic[StateT_contra, T_co], typing.Protocol):
    def __call__(self, __state: StateT_contra) -> T_co:
        ...


class StateUpdateCallback(typing.Generic[StateT_contra], typing.Protocol):
    def __call__(self, __state: StateT_contra) -> None:
        ...


class Model(typing.Generic[StateT]):
    def subscribe(self, property: PropertyCallback[StateT, T],
                  callback: EventCallback[T_contra]) -> EventToken:
        ...

    @typing.overload
    def update(self, **kwargs: typing.Any) -> None:
        ...

    @typing.overload
    def update(self, property: StateUpdateCallback[StateT]) -> None:
        ...

    @property
    def state(self) -> StateT:
        ...

    async def wait_for(
            self,
            property: PropertyCallback[StateT,
                                       T]) -> T:
        ...

    def event_trapdoor(self, property: PropertyCallback[StateT, T]) -> Event:
        ...

    def snapshot(self) -> StateT:
        ...

    def restore(self, snapshot: StateT) -> None:
        ...
