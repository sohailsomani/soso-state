import asyncio
import typing
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from soso import state
from soso.state import protocols


@dataclass
class State:
    value: int = 0
    d: typing.Dict[str, str] = field(default_factory=dict)
    lst: typing.List[int] = field(default_factory=list)


def Model(s: State = State()) -> protocols.Model[State]:  # noqa
    return state.build_model(s)


class NotADataClass:
    pass


def Model2() -> protocols.Model[NotADataClass]:  # noqa
    return state.build_model(NotADataClass())


class TestModel(unittest.TestCase):
    def test_no_change_no_callback(self) -> None:
        model = Model()
        mock = MagicMock()

        model.observe_property(lambda x: x.value, mock)
        mock.assert_called_with(0)
        mock.reset_mock()

        model.update_properties(value=0)
        mock.assert_not_called()

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
        m2: protocols.Model[State] = model
        self.assertIsNotNone(m2)

        self.assertEqual(model.state.value, 0)

    def test_observe_property_changes_basic(self) -> None:
        model = Model()
        mock = MagicMock()

        model.observe_property_changes(lambda x: x.value, mock)
        mock.assert_called_with(None, 0)

        mock.reset_mock()
        model.update_properties(value=5)
        mock.assert_called_with(0, 5)

        mock.reset_mock()
        model.update_properties(value=5)
        mock.assert_not_called()

        mock.reset_mock()
        model.update_properties(value=10)
        mock.assert_called_with(5, 10)

    def test_observe_property_changes_initial_callback(self) -> None:
        model = Model(State(value=42))
        mock = MagicMock()

        model.observe_property_changes(lambda x: x.value, mock)
        mock.assert_called_once_with(None, 42)

    def test_observe_property_changes_independent(self) -> None:
        model = Model()
        mock_changes = MagicMock()
        mock_regular = MagicMock()

        model.observe_property_changes(lambda x: x.value, mock_changes)
        model.observe_property(lambda x: x.value, mock_regular)

        mock_changes.assert_called_with(None, 0)
        mock_regular.assert_called_with(0)

        mock_changes.reset_mock()
        mock_regular.reset_mock()

        model.update_properties(value=5)
        mock_changes.assert_called_with(0, 5)
        mock_regular.assert_called_with(5)

    def test_observe_property_changes_dict_isolation(self) -> None:
        model = Model()

        def update_init(state: State) -> None:
            state.d["key1"] = "value1"
            state.d["key2"] = "value2"

        model.update_state(update_init)

        mock_key1_changes = MagicMock()
        mock_key2_changes = MagicMock()
        mock_dict_regular = MagicMock()

        model.observe_property_changes(lambda x: x.d["key1"], mock_key1_changes)
        model.observe_property_changes(lambda x: x.d["key2"], mock_key2_changes)
        model.observe_property(lambda x: x.d["key2"], mock_dict_regular)

        mock_key1_changes.assert_called_once_with(None, "value1")
        mock_key2_changes.assert_called_once_with(None, "value2")
        mock_dict_regular.assert_called_once_with("value2")

        mock_key1_changes.reset_mock()
        mock_key2_changes.reset_mock()
        mock_dict_regular.reset_mock()

        def update_key2(state: State) -> None:
            state.d["key2"] = "updated2"

        model.update_state(update_key2)

        mock_key1_changes.assert_not_called()
        mock_key2_changes.assert_called_once_with("value2", "updated2")
        mock_dict_regular.assert_called_once_with("updated2")

        mock_key1_changes.reset_mock()
        mock_key2_changes.reset_mock()
        mock_dict_regular.reset_mock()

        def update_key1(state: State) -> None:
            state.d["key1"] = "updated1"

        model.update_state(update_key1)

        mock_key1_changes.assert_called_once_with("value1", "updated1")
        mock_key2_changes.assert_not_called()
        mock_dict_regular.assert_not_called()

        mock_key1_changes.reset_mock()
        mock_key2_changes.reset_mock()
        mock_dict_regular.reset_mock()

        snapshot = model.snapshot()
        # when restoring the entire state, we'd get everything firing unless we only want changes
        model.restore(snapshot)

        mock_key1_changes.assert_not_called()
        mock_key2_changes.assert_not_called()
        mock_dict_regular.assert_called_once_with("updated2")

    def test_wait_for_change_basic(self) -> None:
        model = Model()
        event = model.wait_for_change()

        results = []
        event.connect(lambda prev_new: results.append(prev_new))

        model.update_properties(value=5)
        self.assertEqual(len(results), 1)
        prev, new = results[0]
        self.assertEqual(prev.value, 0)
        self.assertEqual(new.value, 5)

        results.clear()
        model.update_properties(value=10)
        self.assertEqual(len(results), 1)
        prev, new = results[0]
        self.assertEqual(prev.value, 5)
        self.assertEqual(new.value, 10)

    def test_wait_for_change_no_emit_on_same_value(self) -> None:
        model = Model()
        event = model.wait_for_change()

        results = []
        event.connect(lambda prev_new: results.append(prev_new))

        model.update_properties(value=5)
        self.assertEqual(len(results), 1)

        results.clear()
        model.update_properties(value=5)
        self.assertEqual(len(results), 0)

    def test_wait_for_property_change_basic(self) -> None:
        model = Model()
        event = model.wait_for_property_change(lambda x: x.value)

        results = []
        event.connect(lambda prev_new: results.append(prev_new))

        model.update_properties(value=5)
        self.assertEqual(len(results), 1)
        prev, new = results[0]
        self.assertEqual(prev, 0)
        self.assertEqual(new, 5)

        results.clear()
        model.update_properties(value=10)
        self.assertEqual(len(results), 1)
        prev, new = results[0]
        self.assertEqual(prev, 5)
        self.assertEqual(new, 10)

    def test_wait_for_property_change_no_emit_on_same_value(self) -> None:
        model = Model()
        event = model.wait_for_property_change(lambda x: x.value)

        results = []
        event.connect(lambda prev_new: results.append(prev_new))

        model.update_properties(value=5)
        self.assertEqual(len(results), 1)

        results.clear()
        model.update_properties(value=5)
        self.assertEqual(len(results), 0)

    # TODO: figure out how to do this
    """
    def test_update_context(self) -> None:
        model = state.build_model(State())

        with model.update_context() as s:
            s.lst.append(25)

        self.assertEqual(model.state.lst, [25])
    """


class TestModelAsync(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_change_async(self) -> None:
        model = Model()

        async def trigger_change() -> None:
            await asyncio.sleep(0)
            model.update_properties(value=42)

        asyncio.create_task(trigger_change())

        prev, new = await model.wait_for_change()

        assert prev is not None

        self.assertEqual(prev.value, 0)
        self.assertEqual(new.value, 42)
