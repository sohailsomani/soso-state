import os
import pickle
import tkinter as tk
import typing
from dataclasses import dataclass, field

from soso import state

"""Simple example of a TODO app that implements undo/redo. See make_undoable"""


@dataclass
class Todo:
    description: str = ''
    done: bool = False


T = typing.TypeVar('T')


@dataclass
class UndoState(typing.Generic[T]):
    current: T
    past: typing.List[T] = field(default_factory=list)
    is_active: bool = False


@dataclass
class TodoAppState:
    todos: typing.List[Todo] = field(default_factory=list)


def make_undoable(
    # Note that here we use the protocol as the contract so this can work with
    # anything that implements the interface, in particular, submodels
    model: state.protocols.Model[state.StateT],
    prop: state.PropertyCallback[state.StateT, state.T]
) -> typing.Callable[[], None]:
    # The idea here is to catch every state update, memorize that as the
    # "current" state and push it onto the "past" stack when we get a new
    # update. Rinse and repeat.
    #
    # Important to note that we need to avoid against recursive updates when we
    # restore the previous state using the is_active member of the undo state.
    # (undo -> restore old state -> technically a new state -> add new undo
    # state? No!)
    #
    # Future improvements could be to attach the UndoState automatically onto
    # the state tree as technically this is part of application state.

    undo = UndoState(current=model.snapshot(prop))

    def on_state_update(__ignored: state.T) -> None:
        if undo.is_active:
            return
        undo.past.append(undo.current)
        undo.current = model.snapshot(prop)

    def on_do_undo() -> None:
        if len(undo.past) == 0:
            return
        try:
            undo.is_active = True
            model.restore(undo.past.pop(), prop)
        finally:
            undo.is_active = False

    model.observe(prop, on_state_update)

    return on_do_undo


class TodoAppModel(state.Model[TodoAppState]):
    def __init__(self) -> None:
        super().__init__()
        # Ensure we load any state before we make it undoable, otherwise the
        # initial "current" state will be empty
        self.load('.todos')

        self.__undo = make_undoable(self, lambda x: x.todos)

    def undo(self) -> None:
        self.__undo()

    def add_todo(self, text: str) -> None:
        assert text
        todo = Todo(description=text)
        self.update(todos=self.state.todos + [todo])

    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            pickle.dump(self.snapshot(), f)

    def load(self, filename: str) -> None:
        if not os.path.isfile(filename):
            return
        with open(filename, 'rb') as f:
            snapshot = pickle.load(f)
        self.restore(snapshot)


class UI(tk.Frame):
    def __init__(self, model: TodoAppModel) -> None:
        self.__model = model
        root = tk.Tk()
        super().__init__(root)

        self.entry = tk.Entry()
        self.entry_contents = tk.StringVar()
        self.entry["textvariable"] = self.entry_contents
        self.entry.bind('<Key-Return>', self.__add_todo)
        self.entry.pack(fill=tk.X)

        self.button = tk.Button()
        self.button["text"] = "Add TODO"
        self.button["command"] = self.__add_todo
        self.button.pack(fill=tk.X)

        self.listbox_contents = tk.StringVar()
        self.listbox = tk.Listbox(listvariable=self.listbox_contents)
        self.listbox.pack(fill=tk.BOTH, expand=1)

        self.undo = tk.Button()
        self.undo["text"] = "Undo"
        self.undo["command"] = self.__model.undo
        self.undo.pack()

        self.pack()

        x: TodoAppState
        self.__model.observe(lambda x: x.todos,
                             lambda todos: self.__update_listbox(todos))

    def __update_listbox(self, todos: typing.List[Todo]) -> None:
        t: Todo
        choices = [t.description for t in todos]
        self.listbox_contents.set(choices)  # type: ignore

    def __add_todo(self, *a: typing.Any, **kw: typing.Any) -> None:
        txt = self.entry_contents.get()
        if not txt:
            return
        self.__model.add_todo(txt)
        self.entry_contents.set("")

    def run(self) -> None:
        self.mainloop()


model = TodoAppModel()

ui = UI(model)
ui.run()

model.save('.todos')
