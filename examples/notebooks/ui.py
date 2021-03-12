import typing

import pandas as pd
import plotly.graph_objects as go
from examples.notebooks import model
from ipywidgets.widgets import Dropdown, VBox
from soso import state


class Chart(go.FigureWidget):  # type: ignore
    def __init__(self, m: state.protocols.Model[model.Chart],
                 **kw: typing.Any) -> None:
        super().__init__(data=go.Ohlc(), **kw)
        self.update(layout_xaxis_rangeslider_visible=False)
        self.__model = m
        m.observe_property(lambda x: x.bars, self.__bars_updated)

    def __bars_updated(self, bars: pd.DataFrame) -> None:
        with self.batch_update():
            self.update(layout_title=self.__model.state.selected_ticker)
            data = self.data[0]
            data.x = bars.index
            data.open = bars.open
            data.high = bars.high
            data.low = bars.low
            data.close = bars.close


def bind_dropdown(  # type: ignore
        options: state.protocols.Model[typing.List[state.T]],
        target: state.protocols.Model[state.T]) -> Dropdown:
    dropdown = Dropdown()

    def update_options(options: typing.List[state.T]) -> None:
        dropdown.options = [str(s) for s in options]

    options.observe(update_options)

    def update_target(newvalue: typing.Any) -> None:
        target.restore(options.state[newvalue['new']])

    dropdown.observe(update_target, 'index')
    return dropdown


class UI(VBox):  # type: ignore
    def __init__(self, m: state.protocols.Model[model.State]) -> None:
        super().__init__(children=[
            bind_dropdown(m.submodel(lambda x: x.tickers),
                          m.submodel(lambda x: x.chart.selected_ticker)),
            Chart(m.submodel(lambda x: x.chart))
        ])
