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

    def add_todo(self,text):
        assert text
        todo = Todo(description=text)
        self.update(
            todos = self.state.todos + [todo]
        )

class UI(tk.Frame):
    def __init__(self, model: TodoAppModel, master: tk.Tk) -> None:
        self.__model = model
        super().__init__(master)

        self.entry = tk.Entry()
        self.entry_contents = tk.StringVar()
        self.entry["textvariable"] = self.entry_contents
        self.entry.bind('<Key-Return>',self.__add_todo)
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
        self.__model.subscribe(lambda x: x.todos,
                               self.__update_listbox)

    def __update_listbox(self,todos:typing.List[Todo]):
        t:Todo
        choices = [t.description for t in todos]
        self.listbox_contents.set(choices)

    def __add_todo(self,*a,**kw):
        txt = self.entry_contents.get()
        if not txt: return
        self.__model.add_todo(txt)
        self.entry_contents.set("")

model = TodoAppModel()
root = tk.Tk()
ui = UI(model, root)
ui.mainloop()
