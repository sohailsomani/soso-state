import typing
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from soso import state


@dataclass
class State:
    value: int = 0
    d: typing.Dict[str, str] = field(default_factory=dict)


class Model(state.Model[State]):
    pass


class TestModel(unittest.TestCase):
    def test_snapshot(self) -> None:
        model = Model()
        mock = MagicMock()

        model.subscribe(lambda x: x.value, mock)
        mock.assert_called_with(0)

        model.update(value=25)
        snapshot = model.snapshot()

        mock.reset_mock()
        model.update(value=0)
        mock.assert_called_with(0)

        self.assertEqual(model.state.value, 0)

        mock.reset_mock()
        model.restore(snapshot)
        mock.assert_called_with(25)

    def test_snapshot_subtree(self) -> None:
        model = Model()
        x: State
        model.update(value=42)
        snapshot = model.snapshot(lambda x: x.value)
        model.update(value=69)
        self.assertIsInstance(snapshot,int)

        mock = MagicMock()
        model.subscribe(lambda x: x.value,mock)
        mock.assert_called_with(69)
        mock.reset_mock()
        model.restore(snapshot,lambda x: x.value)
        self.assertEqual(model.state.value,42)
        mock.assert_called_with(42)
        mock.assert_called_once()

    def test_root_changes(self) -> None:
        model = Model()
        mock = MagicMock()

        model.subscribe(lambda x: x, mock)
        mock.assert_called_with(State(value=0))

        mock.reset_mock()
        model.update(value=12)
        mock.assert_called_with(State(value=12))

    def test_no_change_no_update(self) -> None:
        model = Model()
        mock = MagicMock()

        model.subscribe(lambda x: x.value, mock)
        mock.assert_called_with(0)

        mock.reset_mock()
        mock.assert_not_called()
        model.update(value=0)
        mock.assert_not_called()

    def test_dict(self) -> None:
        model = Model()

        mock = MagicMock()
        # doesn't exist yet, so can't listen to it
        self.assertRaises(KeyError,
                          lambda: model.subscribe(lambda x: x.d["key"], mock))
        mock.assert_not_called()

        def update(state: State) -> None:
            state.d["key"] = "value"

        model.update(update)
        mock.reset_mock()
        model.subscribe(lambda x: x.d["key"], mock)
        mock.assert_called_with("value")

        def update2(state: State) -> None:
            state.d["key"] = "value2"

        mock.reset_mock()
        model.update(update2)
        mock.assert_called_with("value2")
