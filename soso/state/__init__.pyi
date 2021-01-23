import typing

StateT = typing.TypeVar('StateT',covariant=True)

class Model(typing.Generic[StateT]):
    @typing.overload
    def update(self,**kwargs:typing.Any) -> None: ...

    @typing.overload
    def update(self,func:typing.Callable[[StateT],None]) -> None:...

    @property
    def state(self) -> StateT: ...
