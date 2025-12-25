import typing

from soso.state.event import Event, EventCallback, EventToken

StateT_contra = typing.TypeVar("StateT_contra", contravariant=True)
StateT = typing.TypeVar("StateT")
RootStateT = typing.TypeVar("RootStateT")
T = typing.TypeVar("T")
T_contra = typing.TypeVar("T_contra", contravariant=True)
T_co = typing.TypeVar("T_co", covariant=True)

__all__: list[str] = []

PropertyCallback = typing.Callable[[StateT_contra], T_co]
StateUpdateCallback = typing.Callable[[StateT_contra], None]


class Model(typing.Protocol[StateT]):
    def observe(self, callback: EventCallback[StateT]) -> EventToken: ...

    def observe_changes(
        self, callback: typing.Callable[[typing.Optional[StateT], StateT], None]
    ) -> EventToken: ...

    def observe_property(
        self, property: typing.Callable[[StateT], T], callback: EventCallback[T]
    ) -> EventToken: ...

    def observe_property_changes(
        self,
        property: typing.Callable[[StateT], T],
        callback: typing.Callable[[typing.Optional[T], T], None],
    ) -> EventToken: ...

    def update_state(self, func: StateUpdateCallback[StateT]) -> None: ...

    # used by submodels
    def update_state_root(
        self, root: typing.Callable[[StateT], T], func: StateUpdateCallback[T]
    ) -> None: ...

    def update_properties(self, **kwargs: typing.Any) -> None: ...

    @property
    def state(self) -> StateT: ...

    def wait_for(self) -> Event[StateT]: ...

    def wait_for_property(self, property: typing.Callable[[StateT], T]) -> Event[T]: ...

    def wait_for_change(
        self,
    ) -> Event[typing.Tuple[typing.Optional[StateT], StateT]]: ...

    def wait_for_property_change(
        self, property: typing.Callable[[StateT], T]
    ) -> Event[typing.Tuple[typing.Optional[T], T]]: ...

    def snapshot(self) -> StateT: ...

    def snapshot_property(self, property: typing.Callable[[StateT], T]) -> T: ...

    def restore(self, snapshot: StateT) -> None: ...

    def restore_property(
        self, snapshot: T, property: typing.Callable[[StateT], T]
    ) -> None: ...

    def submodel(self, property: typing.Callable[[StateT], T]) -> "Model[T]": ...
