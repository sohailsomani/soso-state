import copy
import typing
from dataclasses import dataclass, field

from soso.state.util import GetAttr, GetItem, SetAttr, SetItem, delta


@dataclass
class C1:
    a: int


def test_simple() -> None:
    base = C1(5)
    new = C1(3)

    ops = delta(base, new)
    assert ops == [SetAttr('a', 3)]


@dataclass
class C2:
    a: typing.List[int] = field(default_factory=list)


def test_list() -> None:
    base = C2([1, 2, 3])
    new = C2([1, 2, 2])

    ops = delta(base, new)
    assert ops == [GetAttr('a'), SetItem(2, 2)]


@dataclass
class C3:
    a: typing.List[typing.List[int]] = field(default_factory=lambda: [[]])


def test_nested_list() -> None:
    base = C3([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    new = copy.deepcopy(base)
    new.a[1][1] = -2

    ops = delta(base, new)
    assert ops == [GetAttr('a'), GetItem(1), SetItem(1, -2)]


@dataclass
class C4:
    a: typing.List[typing.List[int]] = field(default_factory=lambda: [[]])


def test_nested_list_2() -> None:
    base = C4([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

    new = copy.deepcopy(base)
    new.a[1][1] = -2
    new.a[2][2] = -4

    ops = delta(base, new)
    # yapf: disable
    assert ops == [
        GetAttr('a'), GetItem(1), SetItem(1, -2),
        GetAttr('a'), GetItem(2), SetItem(2, -4)
    ]
    # yapf: enable


@dataclass
class C5:
    a: typing.Dict[str, str] = field(default_factory=dict)


def test_dict() -> None:
    base = C5(dict(hello='world'))
    new = copy.deepcopy(base)
    new.a['hello'] = 'goodbye'

    ops = delta(base, new)
    assert ops == [GetAttr('a'), SetItem('hello', 'goodbye')]


@dataclass
class C6:
    a: typing.List[typing.List[int]] = field(default_factory=lambda: [[]])


@dataclass
class C7:
    a: typing.Dict[str, C6] = field(default_factory=dict)


def test_nested_dict() -> None:
    base = C7(dict(hello=C6([[1, 2, 3], [4, 5, 6], [7, 8, 9]])))
    new = copy.deepcopy(base)
    new.a['hello'].a[1][1] = -2
    new.a['hello'].a[2][2] = -4

    ops = delta(base, new)
    # yapf: disable
    assert ops == [
        GetAttr('a'), GetItem('hello'), GetAttr('a'), GetItem(1), SetItem(1, -2),
        GetAttr('a'), GetItem('hello'), GetAttr('a'), GetItem(2), SetItem(2, -4),
    ]
    # yapf: enable
