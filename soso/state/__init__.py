import typing
from collections import defaultdict
from dataclasses import dataclass, is_dataclass
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

    def __getNodeForPath(self, ops: typing.List["PropertyOp"]) -> Node:
        root: Node = self.__root
        children = []
        for op in ops:
            child = op.key
            children.append(str(child))
            root = root.children[child]
        root.event._name = ".".join(children)
        return root

    def __getValueForPath(self, ops: typing.List["PropertyOp"]) -> Node:
        root: typing.Any = self.__current_state
        for op in ops:
            root = op.get_value(root)
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
        ops = _get_ops(proxy)

        node = self.__getNodeForPath(ops)
        token = node.event.connect(callback, Event.Group.PROCESS)

        value = self.__getValueForPath(ops)
        # call with the initial value
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
        ops = _get_ops(proxy)
        obj = self.__current_state

        stmts: typing.List[typing.List["PropertyOp"]] = [[]]
        for op in ops:
            stmts[-1].append(op)
            obj = op.execute(obj)
            # end of statement
            if obj is None:
                obj = self.__current_state

        for stmt in stmts:
            # if foo.bar.baz[0].blah is modified then we need to signal foo,
            # foo.bar, foo.bar[0], foo.bar.baz[0].blah
            print(stmt)

    @property
    def state(self) -> StateT:
        return self.__current_state


class AttributeAccess(Enum):
    SETATTR = 1
    GETATTR = 2
    SETITEM = 3
    GETITEM = 4

@dataclass
class PropertyOp:
    access: AttributeAccess
    key: typing.Any
    value: typing.Optional[typing.Any] = None

    def execute(self,obj) -> typing.Optional[typing.Any]:
        if self.access  == AttributeAccess.GETATTR:
            return getattr(obj,self.key)
        elif self.access == AttributeAccess.GETITEM:
            return obj[self.key]
        elif self.access == AttributeAccess.SETATTR:
            setattr(obj,self.key,self.value)
            return None
        else:
            assert self.access == AttributeAccess.SETITEM
            obj[self.key] = self.value
            return None

    def get_value(self,obj) -> typing.Any:
        if self.access in [AttributeAccess.GETATTR,AttributeAccess.SETATTR]:
            return getattr(obj,self.key)
        else:
            assert self.access in [AttributeAccess.GETITEM,
                                   AttributeAccess.SETITEM]
            return obj[self.key]


class Proxy:
    def __init__(self):
        self.__dict__['__ops'] = []

    def __setattr__(self, name: str, value: typing.Any) -> None:
        self.__dict__['__ops'].append(
            PropertyOp(AttributeAccess.SETATTR,
                       name,value)
        )

    def __getattr__(self, name: str) -> "Proxy":
        self.__dict__['__ops'].append(
            PropertyOp(AttributeAccess.GETATTR,name)
        )
        return self

    def __setitem__(self, key, value) -> None:
        self.__dict__['__ops'].append(
            PropertyOp(AttributeAccess.SETITEM,key,value)
        )

    def __getitem__(self, key) -> "Proxy":
        self.__dict__['__ops'].append(
            PropertyOp(AttributeAccess.GETITEM,key)
        )
        return self


def _get_ops(proxy: Proxy):
    return proxy.__dict__['__ops']
