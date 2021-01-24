import datetime as dt
import typing
from collections import defaultdict
from dataclasses import is_dataclass
from enum import Enum

from soso.event import Event, EventToken

__all__ = ('Model')

StateT = typing.TypeVar('StateT', covariant=True)
StateT2 = typing.TypeVar('StateT2', contravariant=True)


class PropertyCallback(typing.Generic[StateT2], typing.Protocol):
    def __call__(self, state: StateT2) -> typing.Any:
        ...


class EventCallback(typing.Protocol):
    def __call__(self, *args: typing.Any) -> None:
        ...


class Node:
    def __init__(self):
        self.children: typing.DefaultDict[str, Node] = defaultdict(Node)
        self.data: Event = Event('NodeUpdateEvent')
        self.timestamp: typing.Optional[dt.datetime] = None


class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        self.__state_klass = state_klass = typing.get_args(model_klass)[0]
        assert is_dataclass(state_klass)
        self.__current_state = state_klass()
        self.__root = Node()

    def subscribe(self,
                  props: typing.Union[PropertyCallback[StateT],
                                      typing.List[PropertyCallback[StateT]]],
                  callback: EventCallback) -> EventToken:
        if not isinstance(props, list):
            props = [props]

        paths: typing.List[typing.Any] = []
        for func in props:
            proxy = Proxy()
            func(proxy)  # type: ignore
            path = tuple(_get_proxy_path(proxy))
            paths.append(path)

        # tup = tuple(paths)
        # event = self.__events[tup]  # type: ignore
        # print(event)

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
        # TODO: modify _get_proxy_path to return better structured objects
        path = _get_proxy_path(proxy)
        obj = self.__current_state

        # reverse because I like using pop vs del, can also use a deque on
        # original list. too lazy though. easy fix if performance issue
        path.reverse()
        props: typing.List[typing.List[typing.Any]] = [[]]
        while path:
            op = path.pop()
            props[-1].append(op)
            # setattr/setitem means end of a statement, so the next operation
            # would occur only on the root object.
            if op == AttributeAccess.SETATTR:
                props[-1].append(path[-1])
                props[-1].append(path[-2])
                setattr(obj, path.pop(), path.pop())
                props.append([])
                obj = self.__current_state
            elif op == AttributeAccess.SETITEM:
                props[-1].append(path[-1])
                props[-1].append(path[-2])
                obj[path.pop()] = path.pop()
                props.append([])
                obj = self.__current_state
            elif op == AttributeAccess.GETITEM:
                props[-1].append(path[-1])
                obj = obj[path.pop()]
            else:
                assert op == AttributeAccess.GETATTR
                props[-1].append(path[-1])
                obj = getattr(obj, path.pop())

        # for prop in props:
        #     print(prop)

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
