import typing

from IPython.core import display

from .model import Model
from .ui import UI


def run() -> typing.Tuple[Model, UI]:
    model = Model()
    gui = UI(model)
    display.display(gui)

    return model, gui
