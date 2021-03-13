import math
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass

_basic_types = (int, float, str)


class PropertyOp(typing.Protocol):
    @property
    def key(self) -> typing.Any:
        ...

    def execute(self, obj: typing.Any) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        ...

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        ...

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        ...


def delta(base: typing.Any,
          new: typing.Any,
          prefix: typing.Optional[typing.List[PropertyOp]] = None) -> typing.List[PropertyOp]:
    if prefix is None:
        prefix = []
    ret: typing.List[PropertyOp] = []

    if is_dataclass(base):
        assert is_dataclass(new)
        for f in fields(base):
            basevalue = getattr(base, f.name)
            newvalue = getattr(new, f.name)
            if basevalue != newvalue:
                if isinstance(basevalue, _basic_types) or newvalue is None:
                    ret.append(SetAttr(f.name, newvalue))
                elif isinstance(base, Sequence):
                    ret.append(SetAttr(f.name, newvalue))
                else:
                    ret.extend(delta(basevalue, newvalue, prefix + [GetAttr(f.name)]))
    elif isinstance(base, Sequence):
        assert isinstance(new, Sequence)
        assert len(base) == len(new)
        idx = 0
        for baseval, newval in zip(base, new):
            if baseval != newval:
                if isinstance(baseval, _basic_types) or newval is None:
                    ret.extend(prefix + [SetItem(idx, newval)])
                else:
                    ret.extend(delta(baseval, newval, prefix + [GetItem(idx)]))
            idx += 1
    elif isinstance(base, Mapping):
        assert isinstance(new, Mapping)
        for key in base.keys():
            baseval = base.get(key)
            if key not in new:
                continue
            newval = new.get(key)
            if baseval != newval:
                if isinstance(baseval, _basic_types) or newval is None:
                    ret.extend(prefix + [SetItem(key, newval)])
                else:
                    ret.extend(delta(baseval, newval, prefix + [GetItem(key)]))
    else:
        raise NotImplementedError("Unhandled types: %s", type(base))

    return ret


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
    return proxy.__dict__['__ops']  # type: ignore


@dataclass
class GetAttr:
    key: typing.Any

    def execute(self, obj: typing.Any) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        return getattr(obj, self.key), False

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return getattr(obj, self.key)

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return getattr(obj, self.key)


@dataclass
class SetAttr:
    key: typing.Any
    value: typing.Any

    def execute(self, obj: typing.Any) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        curr_value = getattr(obj, self.key)
        changed = curr_value != self.value
        if changed and isinstance(curr_value, float):
            # At least one should not be NaN
            changed = not math.isnan(curr_value) or not math.isnan(self.value)
        if changed:
            setattr(obj, self.key, self.value)
        return None, changed

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        setattr(obj, self.key, self.value)
        return None

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return getattr(obj, self.key)


@dataclass
class GetItem:
    key: typing.Any

    def execute(self, obj: typing.Any) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        return obj[self.key], False

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return obj[self.key]

    def get_value(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return obj[self.key]


@dataclass
class SetItem:
    key: typing.Any
    value: typing.Any

    def execute(self, obj: typing.Any) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        try:
            curr_value = obj[self.key]
            changed = curr_value != self.value
            if changed and isinstance(curr_value, float):
                # At least one should not be NaN
                changed = not math.isnan(curr_value) or not math.isnan(self.value)
        except KeyError:
            changed = True
        if changed:
            obj[self.key] = self.value
        return None, changed

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        obj[self.key] = self.value
        return None

    def get_value(self, obj: typing.Any) -> typing.Any:
        return obj[self.key]


@dataclass
class Call:
    args: typing.Tuple[typing.Any, ...]
    kwargs: typing.Dict[str, typing.Any]
    key: str = '__call__'

    def execute(self, obj: typing.Any) -> typing.Tuple[typing.Optional[typing.Any], bool]:
        return obj(*self.args, **self.kwargs), True

    def execute_raw(self, obj: typing.Any) -> typing.Optional[typing.Any]:
        return obj(*self.args, **self.kwargs)

    def get_value(self, obj: typing.Any) -> typing.Any:
        return obj.__call__
