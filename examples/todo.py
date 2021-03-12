import os
import pickle
import tkinter as tk
import typing
from dataclasses import dataclass, field

from soso import state

""" Simple example of a TODO app in Tk that implements persistence. See
save/load methods on TodoAppModel """


# Step 1: Define the application state using data classes nested as far as
# needed
@dataclass
class Todo:
    description: str = ''
    done: bool = False


@dataclass
class TodoAppState:
    todos: typing.List[Todo] = field(default_factory=list)


# Step 2: Create a model which holds and manipulates the state.
class TodoAppModel(state.Model[TodoAppState]):
    def __init__(self) -> None:
        super().__init__(TodoAppState())
        self.load(".todos")
        self.observe(lambda _: self.save(".todos"))

    def add_todo(self, text: str) -> None:
        assert text
        todo = Todo(description=text)
        self.update_properties(todos=self.state.todos + [todo])

    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            pickle.dump(self.snapshot(), f)

    def load(self, filename: str) -> None:
        if not os.path.isfile(filename):
            return
        with open(filename, 'rb') as f:
            snapshot = pickle.load(f)
        self.restore(snapshot)


# Step 3: Connect the model to the view
class UI(tk.Frame):
    def __init__(self, model: TodoAppModel) -> None:
        self.__model = model
        root = tk.Tk()
        super().__init__(root)

        self.entry = tk.Entry()
        self.entry_contents = tk.StringVar()
        self.entry["textvariable"] = self.entry_contents
        self.entry.bind('<Key-Return>', self.__add_todo)
        self.entry.pack()

        self.button = tk.Button()
        self.button["text"] = "Add TODO"
        self.button["command"] = self.__add_todo
        self.button.pack()

        self.listbox_contents = tk.StringVar()
        self.listbox = tk.Listbox(listvariable=self.listbox_contents)
        self.listbox.pack()

        self.pack()

        x: TodoAppState
        self.__model.observe_property(lambda x: x.todos, lambda todos: self.__update_listbox(todos))

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
