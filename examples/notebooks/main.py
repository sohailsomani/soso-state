import typing

from examples.notebooks.model import Model
from examples.notebooks.ui import UI
from IPython.core import display


def run() -> typing.Tuple[Model, UI]:
    model = Model()
    gui = UI(model)
    display.display(gui)

    return model, gui
