import typing
from dataclasses import is_dataclass
from enum import Enum

from soso.event import EventToken

__all__ = ('Model')

StateT = typing.TypeVar('StateT', covariant=True)
StateT2 = typing.TypeVar('StateT2', contravariant=True)


class PropertyCallback(typing.Generic[StateT2], typing.Protocol):
    def __call__(self, state: StateT2) -> typing.Any:
        ...


class EventCallback(typing.Protocol):
    def __call__(self, *args: typing.Any) -> None:
        ...


class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        self.__state_klass = state_klass = typing.get_args(model_klass)[0]
        assert is_dataclass(state_klass)
        self.__current_state = state_klass()

    def subscribe(self, property: typing.Union[
        PropertyCallback[StateT], typing.List[PropertyCallback[StateT]]],
                  callback: EventCallback) -> EventToken:
        pass

    def update(self, *args, **kwargs: typing.Any):
        func: typing.Callable[[StateT], None]

        if len(args) == 0:
            assert len(kwargs) != 0

            def doit(state):
                for key, value in kwargs.items():
                    setattr(state, key, value)

            func = doit
        else:
            assert len(args) == 1
            assert len(kwargs) == 0
            assert callable(args[0])
            func = args[0]

        proxy = Proxy()
        func(proxy)
        path = _get_proxy_path(proxy)
        path.reverse()
        obj = self.__current_state

        while path:
            op = path.pop()
            # setattr/setitem means end of a statement, so the next operation
            # would occur only on the root object.
            if op == AttributeAccess.SETATTR:
                setattr(obj, path.pop(), path.pop())
                obj = self.__current_state
            elif op == AttributeAccess.SETITEM:
                obj[path.pop()] = path.pop()
                obj = self.__current_state
            elif op == AttributeAccess.GETITEM:
                obj = obj[path.pop()]
            else:
                assert op == AttributeAccess.GETATTR
                obj = getattr(obj, path.pop())

    @property
    def state(self) -> StateT:
        return self.__current_state


class AttributeAccess(Enum):
    SETATTR = 1
    GETATTR = 2
    SETITEM = 3
    GETITEM = 4


class Proxy:
    def __init__(self):
        self.__dict__['__path'] = []

    def __setattr__(self, name: str, value: typing.Any) -> None:
        self.__dict__['__path'].extend([AttributeAccess.SETATTR, name, value])

    def __getattr__(self, name: str) -> "Proxy":
        self.__dict__['__path'].extend([AttributeAccess.GETATTR, name])
        return self

    def __setitem__(self, key, value) -> None:
        self.__dict__['__path'].extend([AttributeAccess.SETITEM, key, value])

    def __getitem__(self, key) -> "Proxy":
        self.__dict__['__path'].extend([
            AttributeAccess.GETITEM,
            key  # type: ignore
        ])
        return self


def _get_proxy_path(proxy: Proxy):
    return proxy.__dict__['__path']
