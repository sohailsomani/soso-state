from dataclasses import dataclass

from soso import state
from soso.event import Event


def test_raw_update(benchmark):
    emitted = []
    def on_update(e):
        assert e == 42
        emitted.append(True)
    event = Event("Event")
    event.connect(on_update,Event.Group.PROCESS)

    @benchmark
    def doit():
        value = 0
        value = 42
        event.emit(value)

    assert emitted

def test_model_update(benchmark):
    @dataclass
    class State:
        value:int = 42

    class Model(state.Model[State]):
        pass

    model = Model()
    emitted = []
    def on_update(e):
        assert e == 42
        emitted.append(True)

    model.subscribe(lambda x: x.value,on_update)

    @benchmark
    def doit():
        model.state.value = 0
        model.update(value=42)

    assert emitted
