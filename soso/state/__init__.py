import typing
from dataclasses import is_dataclass
from unittest.mock import MagicMock, Mock

__all__ = ('Model')

StateT = typing.TypeVar('StateT', covariant=True)


def _get_attrs_set(mock,ignored_attrs):
    stack = [mock]
    path = []
    visited = set()
    attrs_set = []

    while stack:
        s = stack.pop()
        if id(s) not in visited:
            visited.add(id(s))
        path.append(s)
        if isinstance(s, Mock):
            attrs = set(dir(s)) - ignored_attrs
            stack.extend(attrs)
        else:
            value = getattr(path[-2], s)
            attrs_set.extend(path + [value])
            path.pop()

    return attrs_set


class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        self.__state_klass = state_klass = typing.get_args(model_klass)[0]
        assert is_dataclass(state_klass)
        self.__current_state = state_klass()
        self.__default_attrs = set(dir(MagicMock()) + ["__str__"])

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

        # TODO: Use a more relevant mock library that doesn't have edge cases
        # like "name" properties
        mock = MagicMock()
        func(mock)
        attrs_set = _get_attrs_set(mock,self.__default_attrs)

    @property
    def state(self) -> StateT:
        return self.__current_state
