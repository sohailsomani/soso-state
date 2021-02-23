import typing

from soso.state.event import Event, EventCallback, EventToken

StateT_contra = typing.TypeVar('StateT_contra', contravariant=True)
StateT = typing.TypeVar('StateT')
RootStateT = typing.TypeVar('RootStateT')
T = typing.TypeVar('T')
T_contra = typing.TypeVar('T_contra', contravariant=True)
T_co = typing.TypeVar('T_co', covariant=True)

__all__ = []  # type: ignore

PropertyCallback = typing.Callable[[StateT_contra], T_co]
StateUpdateCallback = typing.Callable[[StateT_contra], None]


class Model(typing.Generic[StateT], typing.Protocol):
    def observe_root(self, callback: EventCallback[StateT]) -> EventToken:
        ...

    def observe(self, property: typing.Callable[[StateT], T],
                callback: EventCallback[T]) -> EventToken:
        ...

    @typing.overload
    def update(self, **kwargs: typing.Any) -> None:
        ...

    @typing.overload
    def update(self, func: StateUpdateCallback[StateT]) -> None:
        ...

    @property
    def state(self) -> StateT:
        ...

    @typing.overload
    def wait_for(self, property: typing.Callable[[StateT], T]) -> Event[T]:
        ...

    @typing.overload
    def wait_for(self) -> Event[StateT]:
        ...

    @typing.overload
    def snapshot(self) -> StateT:
        ...

    @typing.overload
    def snapshot(self, property: typing.Callable[[StateT], T]) -> T:
        ...

    @typing.overload
    def restore(self, snapshot: StateT) -> None:
        ...

    @typing.overload
    def restore(self, snapshot: T, property: typing.Callable[[StateT],
                                                             T]) -> None:
        ...

    def submodel(self, property: typing.Callable[[StateT], T]) -> "Model[T]":
        ...
