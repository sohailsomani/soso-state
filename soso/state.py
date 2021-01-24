import copy
import logging
import traceback
import typing
from collections import defaultdict
from dataclasses import dataclass, field, is_dataclass
from enum import Enum

from soso.event import Event, EventToken

__all__ = ('Model')

StateT = typing.TypeVar('StateT')


class PropertyCallback(typing.Protocol):
    def __call__(self, state: StateT) -> typing.Any:
        ...


class EventCallback(typing.Protocol):
    def __call__(self, *args: typing.Any) -> typing.Optional[typing.Any]:
        ...


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

    def execute(self, obj) -> typing.Optional[typing.Any]:
        if self.access == AttributeAccess.GETATTR:
            return getattr(obj, self.key)
        elif self.access == AttributeAccess.GETITEM:
            return obj[self.key]
        elif self.access == AttributeAccess.SETATTR:
            setattr(obj, self.key, self.value)
            return None
        else:
            assert self.access == AttributeAccess.SETITEM
            obj[self.key] = self.value
            return None

    def get_value(self, obj) -> typing.Any:
        if self.access in [AttributeAccess.GETATTR, AttributeAccess.SETATTR]:
            return getattr(obj, self.key)
        else:
            assert self.access in [
                AttributeAccess.GETITEM, AttributeAccess.SETITEM
            ]
            return obj[self.key]


@dataclass
class Node:
    children: typing.DefaultDict[str, "Node"] = field(
        default_factory=lambda: defaultdict(Node))
    event: Event = field(default_factory=lambda: Event("NodeUpdateEvent"))
    # The type of access to this node
    op: typing.Optional[PropertyOp] = None


class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        self.__state_klass = state_klass = typing.get_args(model_klass)[0]
        assert is_dataclass(state_klass)
        self.__current_state = state_klass()
        self.__root = Node()

    def __get_node_for_ops(self, ops: typing.List[PropertyOp]) -> Node:
        root: Node = self.__root
        children = []
        for op in ops:
            child = op.key
            children.append(str(child))
            root = root.children[child]
            root.op = op
        root.event._name = ".".join(children)
        return root

    def __get_value_for_ops(self, ops: typing.List[PropertyOp]) -> Node:
        root: typing.Any = self.__current_state
        for op in ops:
            root = op.get_value(root)
        return root

    def subscribe(self, func: PropertyCallback,
                  callback: EventCallback) -> EventToken:
        event, ops = self.__event(func)
        token = event.connect(callback, Event.Group.PROCESS)
        value = self.__get_value_for_ops(ops)
        # call with the initial value
        callback(value)
        return token

    def __event(
        self, func: PropertyCallback
    ) -> typing.Tuple[Event, typing.List[PropertyOp]]:
        proxy = Proxy()
        func(proxy)  # type: ignore
        ops = _get_ops(proxy)

        node = self.__get_node_for_ops(ops)
        return node.event, ops

    def event(self, func: PropertyCallback) -> Event:
        return self.__event(func)[0]

    def snapshot(self) -> StateT:
        return copy.deepcopy(self.state)

    def restore(self, snapshot: StateT) -> None:
        self.__current_state = snapshot
        self.__fire_all_child_events(self.__root, self.__current_state)

    def __fire_all_child_events(self, node: Node, parent: typing.Any) -> None:
        for name, child_node in node.children.items():
            try:
                assert child_node.op is not None
                child_value = child_node.op.get_value(parent)
                child_node.event.emit(child_value)
                self.__fire_all_child_events(child_node, child_value)
            except Exception:
                logging.getLogger(__name__).info(traceback.format_exc())

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

        # Get all changes
        proxy = Proxy()
        func(proxy)
        ops = _get_ops(proxy)
        obj = self.__current_state

        # Apply changes tos tate
        stmts: typing.List[typing.List[PropertyOp]] = [[]]
        for op in ops:
            stmts[-1].append(op)
            obj = op.execute(obj)
            # end of statement
            if obj is None:
                obj = self.__current_state
                stmts.append([])

        if stmts[-1] == []:
            stmts.pop()

        if len(stmts) == 0:
            return

        # Always emit root event
        self.__root.event.emit(self.__current_state)
        for stmt in stmts:
            assert stmt
            # if foo.bar.baz[0] is modified then we need to signal foo,
            # foo.bar, foo.bar, foo.bar.baz[0], and then everything
            # below foo.bar.baz[0]
            curr = []
            for op in stmt:
                curr.append(op)
                node = self.__get_node_for_ops(curr)
                value = self.__get_value_for_ops(curr)
                node.event.emit(value)
            # Now everything below node
            self.__fire_all_child_events(node, value)

    @property
    # TODO: this should return a read-only view to avoid accidents
    def state(self) -> StateT:
        return self.__current_state


class Proxy:
    def __init__(self):
        self.__dict__['__ops'] = []

    def __setattr__(self, name: str, value: typing.Any) -> None:
        self.__dict__['__ops'].append(
            PropertyOp(AttributeAccess.SETATTR, name, value))

    def __getattr__(self, name: str) -> "Proxy":
        self.__dict__['__ops'].append(PropertyOp(AttributeAccess.GETATTR,
                                                 name))
        return self

    def __setitem__(self, key, value) -> None:
        self.__dict__['__ops'].append(
            PropertyOp(AttributeAccess.SETITEM, key, value))

    def __getitem__(self, key) -> "Proxy":
        self.__dict__['__ops'].append(PropertyOp(AttributeAccess.GETITEM, key))
        return self


def _get_ops(proxy: Proxy):
    return proxy.__dict__['__ops']
