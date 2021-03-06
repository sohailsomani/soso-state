# type: ignore

from dataclasses import dataclass

from soso import state


def test_raw(benchmark) -> None:
    emitted = []

    def on_update(e):
        assert e == 42
        emitted.append(True)

    event = state.Event("Event")
    event.connect(on_update)

    @benchmark
    def doit():
        value = 0
        value = 42
        event.emit(value)

    assert emitted


def test_fancy(benchmark):
    @dataclass
    class State:
        value: int = 42

    model = state.build_model(State())
    emitted = []

    def on_update(e):
        assert e == 42
        emitted.append(True)

    model.observe_property(lambda x: x.value, on_update)

    @benchmark
    def doit():
        model.state.value = 0

        def update(state):
            state.value = 42

        model.update_state(update)

    assert emitted
