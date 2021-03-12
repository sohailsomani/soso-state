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


def RootModel() -> state.protocols.Model[State]:  # noqa
    return state.build_model(State())


class TestSubModel(unittest.TestCase):
    def test_simple(self) -> None:
        root = state.build_model(State())
        root.update_properties(userlist=UserList([User("willsmith", "willsmith@gmail.com")]))
        submodel = root.submodel(lambda x: x.userlist)
        test_type: state.protocols.Model[UserList] = submodel
        assert test_type is not None

        submock = MagicMock()
        submodel.observe_property(lambda x: x, submock)
        submock.assert_called_with(UserList([User("willsmith", "willsmith@gmail.com")]))

    def test_propagation(self) -> None:
        root = RootModel()
        root.update_properties(userlist=UserList([User("willsmith", "willsmith@gmail.com")]))
        rootmock = MagicMock()
        root.observe_property(lambda x: x.userlist, rootmock)
        submodel = root.submodel(lambda x: x.userlist)

        submock = MagicMock()
        submodel.observe_property(lambda x: x, submock)
        submock.assert_called_with(UserList([User("willsmith", "willsmith@gmail.com")]))

        # check that updating submodel updates the root model
        def update(proxy: UserList) -> None:
            proxy.users = [User("jazzyjeff", "jazzyjeff@gmail.com")]

        submock.reset()
        rootmock.reset()

        submodel.update_state(update)

        submock.assert_called_with(UserList([User("jazzyjeff", "jazzyjeff@gmail.com")]))

        rootmock.assert_called_with(UserList([User("jazzyjeff", "jazzyjeff@gmail.com")]))

        submock.reset()
        rootmock.reset()

        # check that updating root model updates the submodel
        def update2(proxy: State) -> None:
            proxy.userlist.users = [User("unclephil", "unclephil@gmail.com")]

        root.update_state(update2)
        submock.assert_called_with(UserList([User("unclephil", "unclephil@gmail.com")]))

        rootmock.assert_called_with(UserList([User("unclephil", "unclephil@gmail.com")]))

    def test_probably_bug(self) -> None:
        root = RootModel()
        sub: state.protocols.Model[UserList] = root.submodel(lambda x: x.userlist)
        mock1 = MagicMock()
        mock2 = MagicMock()
        sub.observe_property(lambda x: x.users, mock1)
        sub.observe_property(lambda x: x.anumber, mock2)

        # hunch: updating multiple values through a submodel update function is
        # buggy
        def update(proxy: UserList) -> None:
            proxy.users = [User("willsmith", "willsmith@gmail.com")]
            proxy.anumber = 5

        sub.update_state(update)
        mock1.assert_called_with([User("willsmith", "willsmith@gmail.com")])
        mock2.assert_called_with(5)

    def test_observe(self) -> None:
        root = RootModel()
        sub = root.submodel(lambda x: x.userlist)
        mock = MagicMock()
        sub.observe(mock)
        mock.reset_mock()

        def update(proxy: UserList) -> None:
            proxy.users = [User("willsmith", "willsmith@gmail.com")]
            proxy.anumber = 5

        sub.update_state(update)
        mock.assert_called_with(
            UserList(users=[User("willsmith", "willsmith@gmail.com")], anumber=5))

    def test_update_properties(self) -> None:
        root = RootModel()
        sub: state.protocols.Model[UserList] = root.submodel(lambda x: x.userlist)
        mock1 = MagicMock()
        mock2 = MagicMock()
        sub.observe_property(lambda x: x.users, mock1)
        sub.observe_property(lambda x: x.anumber, mock2)

        sub.update_properties(users=[User("willsmith", "willsmith@gmail.com")], anumber=5)

        mock1.assert_called_with([User("willsmith", "willsmith@gmail.com")])
        mock2.assert_called_with(5)


@dataclass
class SubState:
    v1: int = 0
    v2: int = 0


@dataclass
class RootState:
    sub: SubState = field(default_factory=SubState)


def test_inline_submodel() -> None:
    model = state.build_model(RootState())
    mock = MagicMock()
    model.observe_property(lambda x: x.sub, mock)
    mock.reset_mock()

    model.submodel(lambda x: x.sub).update_properties(v1=4, v2=2)

    mock.assert_called_with(SubState(v1=4, v2=2))
