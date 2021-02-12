import typing

import pandas as pd
import plotly.graph_objects as go
from ipywidgets.widgets import Dropdown, VBox
from soso import state

import model


class Chart(go.FigureWidget):  # type: ignore
    def __init__(self, m: state.protocols.Model[model.Chart],
                 **kw: typing.Any) -> None:
        super().__init__(data=go.Ohlc(), **kw)
        self.update(layout_xaxis_rangeslider_visible=False)
        self.__model = m
        m.observe(lambda x: x.bars, self.__bars_updated)

    def __bars_updated(self, bars: pd.DataFrame) -> None:
        with self.batch_update():
            self.update(layout_title=self.__model.state.selected_ticker)
            data = self.data[0]
            data.x = bars.index
            data.open = bars.open
            data.high = bars.high
            data.low = bars.low
            data.close = bars.close


def bind_dropdown(options: state.protocols.Model[typing.List[state.T]],
                  target: state.protocols.Model[state.T]) -> Dropdown:
    dropdown = Dropdown()

    def update_options(options: typing.List[state.T]) -> None:
        dropdown.options = [str(s) for s in options]

    options.observe(lambda x: x, update_options)

    def update_target(newvalue: typing.Any) -> None:
        target.restore(options.state[newvalue['new']])

    dropdown.observe(update_target, 'index')
    return dropdown


class UI(VBox):  # type: ignore
    def __init__(self, m: state.protocols.Model[model.State]) -> None:
        super().__init__(children=[
            # Note, we need to ignore the type because lambda functions are not
            # very amenable to type checking and mypy complains. In future
            # iterations, the idea is to use something like:
            #
            #    state.SubModel(m.state.tickers)
            #
            # To ensure consistent typing
            bind_dropdown(
                state.SubModel(m, lambda x: x.tickers),  # type: ignore
                state.SubModel(m, lambda x: x.chart.selected_ticker)),
            Chart(state.SubModel(m, lambda x: x.chart))
        ])
