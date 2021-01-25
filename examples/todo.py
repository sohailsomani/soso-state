import tkinter as tk
import typing
from dataclasses import dataclass, field

from soso import state


@dataclass
class Todo:
    done: bool = False
    description: str = ''


@dataclass
class TodoAppState:
    todos: typing.List[Todo] = field(default_factory=list)


class TodoAppModel(state.Model[TodoAppState]):
    def __init__(self) -> None:
        super().__init__()


class UI(tk.Frame):
    def __init__(self, model: TodoAppModel, master: tk.Tk) -> None:
        self.__model = model
        super().__init__(master)
        self.pack()

        self.entry = tk.Entry()
        self.entry.pack()


model = TodoAppModel()
root = tk.Tk()
ui = UI(model, root)
ui.mainloop()
