import copy
import logging
import traceback
import typing
from collections import defaultdict
from dataclasses import dataclass, field, is_dataclass

from soso.state import protocols
from soso.state.event import Event, EventCallback, EventToken

try:
    import pandas as pd

    def _is_not_equal(x: typing.Any, y: typing.Any) -> bool:
        if isinstance(x, (pd.DataFrame, pd.Series)) or \
           isinstance(y, (pd.DataFrame, pd.Series)):
            return id(x) != id(y)
        else:
            return x != y  # type: ignore
except ImportError:

    def _is_not_equal(x: typing.Any, y: typing.Any) -> bool:
        return x != y  # type: ignore


__all__ = ['Model', 'StateT', 'T', 'PropertyCallback']

StateT_contra = typing.TypeVar('StateT_contra', contravariant=True)
StateT = typing.TypeVar('StateT')
RootStateT = typing.TypeVar('RootStateT')
T = typing.TypeVar('T')
T_contra = typing.TypeVar('T_contra', contravariant=True)
T_co = typing.TypeVar('T_co', covariant=True)

PropertyCallback = typing.Callable[[StateT_contra], T_co]
StateUpdateCallback = typing.Callable[[StateT_contra], None]


class PropertyOp(typing.Protocol):
    @property
    def key(self) -> typing.Any:
        ...

    def execute(
            self, obj: typing.Any
    ) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        ...

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        ...

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        ...


@dataclass
class Node:
    children: typing.DefaultDict[str, "Node"] = field(
        default_factory=lambda: defaultdict(Node))
    event: Event[typing.Any] = field(
        default_factory=lambda: Event("NodeUpdateEvent"))
    # The type of access to this node
    op: typing.Optional[PropertyOp] = None


class Model(typing.Generic[StateT], protocols.Model[StateT]):
    def __init__(self, initial_state: typing.Optional[StateT] = None) -> None:
        model_klass = self.__orig_bases__[-1]  # type:ignore
        self.__state_klass = state_klass = typing.get_args(model_klass)[0]
        if not is_dataclass(state_klass):
            raise ValueError("Expected a dataclass, got %s", state_klass)
        assert is_dataclass(state_klass)
        if initial_state is None:
            self.__current_state: StateT = state_klass()
        else:
            self.__current_state = copy.deepcopy(initial_state)
        self.__root = Node()
        self.__root.event._name = "root"

    def __get_node_for_ops(self, ops: typing.List[PropertyOp]) -> Node:
        root: Node = self.__root
        s = root.event._name
        for op in ops:
            root = root.children[op.key]
            root.op = op
            s += '.' + str(op.key)
            root.event._name = s
        return root

    def __get_value_for_ops(self, ops: typing.List[PropertyOp]) -> typing.Any:
        root: typing.Any = self.__current_state
        for op in ops:
            root = op.get_value(root)
        return root

    def submodel(self, func: PropertyCallback[StateT,
                                              T]) -> protocols.Model[T]:
        return _SubModel(self, func)

    def observe_root(self, callback: EventCallback[StateT]) -> EventToken:
        return self.observe(lambda x: x, callback)

    def observe(self, func: PropertyCallback[StateT, T],
                callback: EventCallback[T]) -> EventToken:
        event, ops = self.__event(func)
        token = event.connect(callback)
        value = self.__get_value_for_ops(ops)
        # call with the initial value
        callback(value)
        return token

    def __event(
        self, func: PropertyCallback[StateT, T]
    ) -> typing.Tuple[Event[T], typing.List[PropertyOp]]:
        proxy: StateT = typing.cast(StateT, Proxy())
        func(proxy)
        ops = _get_ops(proxy)  # type:ignore

        node = self.__get_node_for_ops(ops)
        return node.event, ops

    def event(self, property: PropertyCallback[StateT, T]) -> Event[T]:
        return self.__event(property)[0]

    async def wait_for(self, property: PropertyCallback[StateT, T]) -> T:
        result = await self.event(property)
        return result

    @typing.overload
    def snapshot(self) -> StateT:
        ...

    @typing.overload
    def snapshot(self, property: PropertyCallback[StateT, T]) -> T:
        ...

    def snapshot(
            self,
            property: typing.Optional[PropertyCallback[StateT,
                                                       T]] = None) -> T:
        if property is None:

            def cb(x: StateT) -> StateT:
                return x

            property = cb  # type: ignore
        assert property is not None
        subtree = property(self.state)
        return copy.deepcopy(subtree)

    def restore(
            self,
            snapshot: typing.Union[T, StateT],
            property: typing.Optional[PropertyCallback[StateT,
                                                       T]] = None) -> None:
        if property is None:
            self.__current_state = typing.cast(StateT, snapshot)
            self.__fire_all_child_events(self.__root, self.__current_state)
            return

        proxy = typing.cast(StateT, Proxy())
        property(proxy)
        ops = _get_ops(typing.cast(Proxy, proxy))
        if isinstance(ops[-1], GetAttr):
            ops[-1] = SetAttr(ops[-1].key, snapshot)
        else:
            assert isinstance(ops[-1], GetItem)
            ops[-1] = SetItem(ops[-1].key, snapshot)

        def update(state: StateT) -> None:
            obj: typing.Optional[typing.Any] = state
            for op in ops:
                obj = op.execute_raw(obj)

        self.update(update)

    def __fire_all_child_events(self, node: Node, parent: typing.Any) -> None:
        for name, child_node in node.children.items():
            try:
                assert child_node.op is not None
                child_value = child_node.op.get_value(parent)
                child_node.event.emit(child_value)
                self.__fire_all_child_events(child_node, child_value)
            except Exception:
                # It's common for values to disappear, no need to pepper
                # info logs. TODO: should GC such child nodes? Probably
                logging.getLogger(__name__).debug(traceback.format_exc())

    @typing.overload
    def update(self, **kwargs: typing.Any) -> None:
        ...

    @typing.overload
    def update(self, func: StateUpdateCallback[StateT]) -> None:
        ...

    def update(self, *args: StateUpdateCallback[StateT],
               **kwargs: typing.Any) -> None:
        func: StateUpdateCallback[StateT]
        if '__submodel_root' in kwargs:
            __submodel_root = kwargs['__submodel_root']
            del kwargs['__submodel_root']
        else:

            def cb(x: StateT) -> StateT:
                return x

            __submodel_root = cb

        if len(args) == 0:
            assert len(kwargs) != 0

            def doit(state: StateT) -> None:
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
        func(proxy)  # type: ignore
        ops = _get_ops(proxy)
        obj: typing.Optional[typing.Any] = __submodel_root(
            self.__current_state)

        # Apply changes tos tate
        stmts: typing.List[typing.List[PropertyOp]] = []
        curr_stmt: typing.List[PropertyOp] = []
        for op in ops:
            curr_stmt.append(op)
            obj, changed = op.execute(obj)
            # end of statement
            if obj is None:
                obj = __submodel_root(self.__current_state)
                if changed:
                    stmts.append(curr_stmt)
                    curr_stmt = []
                else:
                    # if not changed, ignore this statement
                    curr_stmt = []

        # if the last expression had no set, then that means it was a read
        # without a write. No good. Let the user know.
        assert not curr_stmt

        if len(stmts) == 0:
            return

        # Always emit root
        self.__root.event.emit(self.__current_state)

        # Emit everything from actual root to __submodel_root
        rootproxy = Proxy()
        __submodel_root(rootproxy)
        rootops = _get_ops(rootproxy)
        curr = []
        for op in rootops:
            curr.append(op)
            node = self.__get_node_for_ops(curr)
            value = self.__get_value_for_ops(curr)
            node.event.emit(value)

        # Now emit the fields that were actually modified
        for stmt in stmts:
            assert stmt
            # if foo.bar.baz[0] is modified then we need to signal foo,
            # foo.bar, foo.bar, foo.bar.baz[0], and then everything
            # below foo.bar.baz[0]
            curr = rootops[:]
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

    def __str__(self) -> str:
        return f"#<Model state={self.state}>"

    def __repr__(self) -> str:
        return str(self)


class _SubModel(typing.Generic[RootStateT, StateT], protocols.Model[StateT]):
    def __init__(self, root_model: protocols.Model[RootStateT],
                 root_property: typing.Callable[[RootStateT], StateT]):
        self.__model = root_model
        self.__property = root_property

    def observe_root(self, callback: EventCallback[StateT]) -> EventToken:
        return self.observe(lambda x: x, callback)

    def observe(self, property: PropertyCallback[StateT, T],
                callback: EventCallback[T]) -> EventToken:
        def propfunc(root: RootStateT) -> T:
            return property(self.__property(root))

        return self.__model.observe(propfunc, callback)

    @property
    def state(self) -> StateT:
        return self.__property(self.__model.state)

    async def wait_for(self, property: PropertyCallback[StateT, T]) -> T:
        def propfunc(root: RootStateT) -> T:
            return property(self.__property(root))

        result = await self.__model.wait_for(propfunc)
        return result

    @typing.overload
    def snapshot(self) -> StateT:
        ...

    @typing.overload
    def snapshot(self, property: PropertyCallback[StateT, T]) -> T:
        ...

    def snapshot(
        self,
        property: typing.Optional[PropertyCallback[StateT, T]] = None
    ) -> typing.Union[StateT, T]:
        def propfunc(root: RootStateT) -> typing.Union[StateT, T]:
            if property is None:
                return self.__property(root)
            else:
                return property(self.__property(root))

        return self.__model.snapshot(propfunc)

    def restore(
            self,
            snapshot: typing.Union[StateT, T],
            property: typing.Optional[PropertyCallback[StateT,
                                                       T]] = None) -> None:
        def propfunc(root: RootStateT) -> typing.Union[StateT, T]:
            if property is None:
                return self.__property(root)
            else:
                return property(self.__property(root))

        return self.__model.restore(snapshot, propfunc)

    @typing.overload
    def update(self, **kwargs: typing.Any) -> None:
        ...

    @typing.overload
    def update(self, property: StateUpdateCallback[StateT]) -> None:
        ...

    def update(self, *args: StateUpdateCallback[StateT],
               **kwargs: typing.Any) -> None:
        self.__model.update(*args, __submodel_root=self.__property, **kwargs)

    def submodel(self, property: PropertyCallback[StateT,
                                                  T]) -> protocols.Model[T]:
        def func(x: RootStateT) -> T:
            return property(self.__property(x))

        return self.__model.submodel(func)

    def __str__(self) -> str:
        return f"#<SubModel state={self.state} root={self.__model}>"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class GetAttr:
    key: typing.Any

    def execute(
            self, obj: typing.Any
    ) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        return getattr(obj, self.key), False

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return getattr(obj, self.key)

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return getattr(obj, self.key)


@dataclass
class SetAttr:
    key: typing.Any
    value: typing.Any

    def execute(
            self, obj: typing.Any
    ) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        curr_value = getattr(obj, self.key)
        changed = _is_not_equal(curr_value, self.value)
        if changed:
            setattr(obj, self.key, self.value)
        return None, changed

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return setattr(obj, self.key, self.value)

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return getattr(obj, self.key)


@dataclass
class GetItem:
    key: typing.Any

    def execute(
            self, obj: typing.Any
    ) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        return obj[self.key], False

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return obj[self.key]

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return obj[self.key]


@dataclass
class SetItem:
    key: typing.Any
    value: typing.Any

    def execute(
            self, obj: typing.Any
    ) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        try:
            curr_value = obj[self.key]
            changed = curr_value != self.value
        except KeyError:
            changed = True
        if changed:
            obj[self.key] = self.value
        return None, changed

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        obj[self.key] = self.value

    def get_value(self, obj: typing.Any) -> typing.Any:
        return obj[self.key]


@dataclass
class Call:
    args: typing.Tuple[typing.Any, ...]
    kwargs: typing.Dict[str, typing.Any]
    key: str = '__call__'

    def execute(
            self, obj: typing.Any
    ) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        return obj(*self.args, **self.kwargs), True

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return obj(*self.args, **self.kwargs)

    def get_value(self, obj: typing.Any) -> typing.Any:
        return obj.__call__


class Proxy:
    def __init__(self) -> None:
        self.__dict__['__ops'] = []

    def __setattr__(self, name: str, value: typing.Any) -> None:
        self.__dict__['__ops'].append(SetAttr(name, value))

    def __getattr__(self, name: str) -> "Proxy":
        self.__dict__['__ops'].append(GetAttr(name))
        return self

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        self.__dict__['__ops'].append(SetItem(key, value))

    def __getitem__(self, key: typing.Any) -> "Proxy":
        self.__dict__['__ops'].append(GetItem(key))
        return self

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.__dict__['__ops'].append(Call(args, kwargs))


def _get_ops(proxy: Proxy) -> typing.List[PropertyOp]:
    return proxy.__dict__['__ops']  # type:ignore
