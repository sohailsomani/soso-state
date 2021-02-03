import typing

from soso.state.event import Event, EventCallback, EventToken

StateT_contra = typing.TypeVar('StateT_contra', contravariant=True)
StateT = typing.TypeVar('StateT')
T = typing.TypeVar('T')
T_contra = typing.TypeVar('T_contra', contravariant=True)
T_co = typing.TypeVar('T_co', covariant=True)

class PropertyCallback(typing.Generic[StateT_contra, T_co], typing.Protocol):
    def __call__(self, __proxy: StateT_contra) -> T_co:
        ...


class StateUpdateCallback(typing.Generic[StateT_contra], typing.Protocol):
    def __call__(self, __proxy: StateT_contra) -> None:
        ...


class Model(typing.Generic[StateT]):
    def observe(self, property: PropertyCallback[StateT, T],
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

    @typing.overload
    def snapshot(self) -> StateT:
        ...

    @typing.overload
    def snapshot(self,property:PropertyCallback[StateT,T]) -> T:
        ...

    @typing.overload
    def restore(self, snapshot: StateT) -> None:
        ...

    @typing.overload
    def restore(self, snapshot: T, property:PropertyCallback[StateT,T]) -> None:
        ...
