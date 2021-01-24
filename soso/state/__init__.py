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
        self.event: Event = Event('NodeUpdateEvent')


class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        self.__state_klass = state_klass = typing.get_args(model_klass)[0]
        assert is_dataclass(state_klass)
        self.__current_state = state_klass()
        self.__root = Node()

    def __getNodeForPath(self, path: typing.List[typing.Any]) -> Node:
        it = iter(path)
        root: Node = self.__root
        children = []
        for op in it:
            if op in [AttributeAccess.SETATTR, AttributeAccess.SETITEM]:
                child = next(it)
                next(it)
                assert len(path) == 0
            else:
                assert op in [AttributeAccess.GETITEM, AttributeAccess.GETATTR]
                child = next(it)
            children.append(str(child))
            root = root.children[child]
        root.event._name = ".".join(children)
        return root

    def __getValueForPath(self, path: typing.List[typing.Any]) -> Node:
        it = iter(path)
        root: typing.Any = self.__current_state
        for op in it:
            if op in [AttributeAccess.SETATTR, AttributeAccess.GETATTR]:
                child = next(it)
                root = getattr(root, child)
            else:
                assert op in [AttributeAccess.SETITEM, AttributeAccess.GETITEM]
                child = next(it)
                root = root[child]
        return root

    def subscribe(self,
                  props: typing.Union[PropertyCallback[StateT],
                                      typing.List[PropertyCallback[StateT]]],
                  callback: EventCallback) -> EventToken:
        if not isinstance(props, list):
            props = [props]

        # we don't yet handle subscribing to multiple properties
        assert len(props) == 1

        func = props[0]
        proxy = Proxy()
        func(proxy)  # type: ignore
        path = _get_proxy_path(proxy)

        node = self.__getNodeForPath(path)
        token = node.event.connect(callback, Event.Group.PROCESS)

        value = self.__getValueForPath(path)
        callback(value)

        return token

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
        # TODO: modify _get_proxy_path to return a better structured list of
        # objects
        path = _get_proxy_path(proxy)
        obj = self.__current_state

        props: typing.List[typing.List[typing.Any]] = [[]]
        it = iter(path)
        for op in it:
            assert isinstance(op,AttributeAccess)
            props[-1].append(op)
            # setattr/setitem means end of a statement, so the next operation
            # would occur only on the root object.
            if op == AttributeAccess.SETATTR:
                props[-1].append(path[-1])
                props[-1].append(path[-2])
                setattr(obj, next(it), next(it))
                props.append([])
                obj = self.__current_state
            elif op == AttributeAccess.SETITEM:
                props[-1].append(path[-1])
                props[-1].append(path[-2])
                obj[next(it)] = next(it)
                props.append([])
                obj = self.__current_state
            elif op == AttributeAccess.GETITEM:
                props[-1].append(path[-1])
                obj = obj[next(it)]
            else:
                assert op == AttributeAccess.GETATTR
                props[-1].append(path[-1])
                obj = getattr(obj, next(it))

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
