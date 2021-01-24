import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock

from soso import state


@dataclass
class State:
    value: int = 0


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

    def test_root_changes(self) -> None:
        model = Model()
        mock = MagicMock()

        model.subscribe(lambda x: x,mock)
        mock.assert_called_with(State(value=0))

        mock.reset_mock()
        model.update(value=12)
        mock.assert_called_with(State(value=12))

