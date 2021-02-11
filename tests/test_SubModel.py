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
    anumber: int = 0


@dataclass
class State:
    userlist: UserList = field(default_factory=UserList)
    avalue: bool = False


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

        submock = MagicMock()
        submodel.observe(lambda x: x, submock)
        submock.assert_called_with(
            UserList([User("willsmith", "willsmith@gmail.com")]))

    def test_propagation(self) -> None:
        root = RootModel()
        root.update(
            userlist=UserList([User("willsmith", "willsmith@gmail.com")]))
        rootmock = MagicMock()
        root.observe(lambda x: x.userlist, rootmock)
        submodel: state.protocols.Model[UserList] = SubModel(
            root, lambda x: x.userlist)

        submock = MagicMock()
        submodel.observe(lambda x: x, submock)
        submock.assert_called_with(
            UserList([User("willsmith", "willsmith@gmail.com")]))

        # check that updating submodel updates the root model
        def update(proxy: UserList) -> None:
            proxy.users = [User("jazzyjeff", "jazzyjeff@gmail.com")]

        print("HERE")
        submock.reset()
        rootmock.reset()

        submodel.update(update)

        submock.assert_called_with(
            UserList([User("jazzyjeff", "jazzyjeff@gmail.com")]))

        rootmock.assert_called_with(
            UserList([User("jazzyjeff", "jazzyjeff@gmail.com")]))

    def test_probably_bug(self) -> None:
        root = RootModel()
        sub: state.protocols.Model[UserList] = SubModel(
            root, lambda x: x.userlist)
        mock1 = MagicMock()
        mock2 = MagicMock()
        sub.observe(lambda x: x.users, mock1)
        sub.observe(lambda x: x.anumber, mock2)

        # hunch: updating multiple values through a submodel update function is
        # buggy
        def update(proxy: UserList) -> None:
            proxy.users = [User("willsmith", "willsmith@gmail.com")]
            proxy.anumber = 5

        sub.update(update)
        mock1.assert_called_with([User("willsmith", "willsmith@gmail.com")])
        mock2.assert_called_with(5)
