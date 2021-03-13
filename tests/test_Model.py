import typing
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from soso import state


@dataclass
class State:
    value: int = 0
    d: typing.Dict[str, str] = field(default_factory=dict)
    lst: typing.List[int] = field(default_factory=list)


def Model(s: State = State()) -> state.protocols.Model[State]: # noqa
    return state.build_model(s)


class NotADataClass:
    pass


def Model2() -> state.protocols.Model[NotADataClass]: # noqa
    return state.build_model(NotADataClass())


class TestModel(unittest.TestCase):
    def test_snapshot(self) -> None:
        model = Model()
        mock = MagicMock()

        model.observe_property(lambda x: x.value, mock)
        mock.assert_called_with(0)

        model.update_properties(value=25)
        snapshot = model.snapshot()

        mock.reset_mock()
        model.update_properties(value=0)
        mock.assert_called_with(0)

        self.assertEqual(model.state.value, 0)

        mock.reset_mock()
        model.restore(snapshot)
        mock.assert_called_with(25)

    def test_snapshot_subtree(self) -> None:
        model = Model()
        x: State
        model.update_properties(value=42)
        snapshot = model.snapshot_property(lambda x: x.value)
        model.update_properties(value=69)
        self.assertIsInstance(snapshot, int)

        mock = MagicMock()
        model.observe_property(lambda x: x.value, mock)
        mock.assert_called_with(69)
        mock.reset_mock()
        model.restore_property(snapshot, lambda x: x.value)
        self.assertEqual(model.state.value, 42)
        mock.assert_called_with(42)
        mock.assert_called_once()

    def test_snapshot_subtree_getitem(self) -> None:
        model = Model()
        x: State

        def subtree(state: State) -> str:
            return state.d["hello"]

        model.update_properties(d=dict(hello="goodbye"))
        snapshot = model.snapshot_property(subtree)
        model.update_properties(d=dict(hello="world"))
        self.assertIsInstance(snapshot, str)

        mock = MagicMock()
        model.observe_property(subtree, mock)
        mock.assert_called_with("world")
        mock.reset_mock()
        model.restore_property(snapshot, subtree)
        self.assertEqual(model.state.d["hello"], "goodbye")
        mock.assert_called_with("goodbye")
        mock.assert_called_once()

    def test_root_changes(self) -> None:
        model = Model()
        mock = MagicMock()

        model.observe_property(lambda x: x, mock)
        mock.assert_called_with(State(value=0))

        mock.reset_mock()
        model.update_properties(value=12)
        mock.assert_called_with(State(value=12))

    def test_no_change_no_update(self) -> None:
        model = Model()
        mock = MagicMock()

        model.observe_property(lambda x: x.value, mock)
        mock.assert_called_with(0)

        mock.reset_mock()
        mock.assert_not_called()
        model.update_properties(value=0)
        mock.assert_not_called()

    def test_dict(self) -> None:
        model = Model()

        mock = MagicMock()
        # doesn't exist yet, so can't listen to it, we swallow the error, and
        # the callback is not called
        model.observe_property(lambda x: x.d["key"], mock)
        mock.assert_not_called()

        def update(state: State) -> None:
            state.d["key"] = "value"

        model.update_state(update)
        mock.reset_mock()
        model.observe_property(lambda x: x.d["key"], mock)
        mock.assert_called_with("value")

        def update2(state: State) -> None:
            state.d["key"] = "value2"

        mock.reset_mock()
        model.update_state(update2)
        mock.assert_called_with("value2")

    def test_funcall(self) -> None:
        model = Model()

        mock = MagicMock()

        def update(state: State) -> None:
            state.lst.append(1)

        model.observe_property(lambda x: x.lst, mock)
        mock.reset_mock()

        model.update_state(update)
        mock.assert_called_with([1])

    def test_constructor(self) -> None:
        model = Model(State(value=42))

        self.assertEqual(model.state.value, 42)

        self.assertRaisesRegex(ValueError, "Expected a dataclass", lambda: Model2())

        self.assertRaisesRegex(ValueError, "Expected a dataclass", lambda: Model2())

    def test_build_model(self) -> None:
        model = state.build_model(State())
        m2: state.protocols.Model[State] = model
        self.assertIsNotNone(m2)

        self.assertEqual(model.state.value, 0)
