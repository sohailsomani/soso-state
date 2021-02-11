import typing
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from soso import state


@dataclass
class User:
    username: str
    email: str


@dataclass
class UserList:
    users: typing.List[User] = field(default_factory=list)


@dataclass
class State:
    userlist: UserList = field(default_factory=UserList)


class RootModel(state.Model[State]):
    pass


class SubModel(state.SubModel[State, UserList]):
    pass


class TestSubModel(unittest.TestCase):
    def test_simple(self) -> None:
        root = RootModel()
        root.update(
            userlist=UserList([User("willsmith", "willsmith@gmail.com")]))
        submodel: state.protocols.Model[UserList] = SubModel(
            root, lambda x: x.userlist)

        mock = MagicMock()
        submodel.observe(lambda x: x, mock)
        mock.assert_called_with(
            UserList([User("willsmith", "willsmith@gmail.com")]))
