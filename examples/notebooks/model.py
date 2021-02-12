import datetime as dt
import typing
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from soso import state


@dataclass
class Chart:
    bars: pd.DataFrame = field(
        default_factory=lambda: pd.DataFrame(  # type: ignore
            index=[],
            data=dict(open=[], high=[], low=[], close=[])))
    selected_ticker: str = ''


@dataclass
class State:
    tickers: typing.List[str] = field(
        default_factory=lambda: ['TICK1', 'TICK2', 'TICK3'])
    chart: Chart = field(default_factory=Chart)


class Model(state.Model[State]):
    def __init__(self) -> None:
        super().__init__()
        _init_gbm_generator(
            state.SubModel(self, lambda x: x.chart.selected_ticker),
            state.SubModel(self, lambda x: x.chart.bars))


def _init_gbm_generator(
        ticker_model: state.protocols.Model[str],
        bars_model: state.protocols.Model[pd.DataFrame]) -> None:
    from math import exp, sqrt
    from random import gauss

    st = 100.0
    mu = 0.1
    sigma = 0.05

    # https://towardsdatascience.com/create-a-stock-price-simulator-with-python-b08a184f197d
    def generate_value() -> float:
        nonlocal st

        st *= exp((mu - 0.5 * sigma**2) * (1. / 365.) +
                  sigma * sqrt(1. / 365.) * gauss(mu=0, sigma=1))
        return st

    def generate_data(__ticker: str) -> None:
        # ticker ignored
        nonlocal st

        st = np.random.randint(50, 150)
        bars = []
        date = dt.datetime(2020, 1, 1, 9, 30)
        for hour in range(24):
            o = h = low = c = np.nan
            for minute in range(60):
                st = generate_value()
                if np.isnan(o):
                    o = st
                c = st
                if np.isnan(h):
                    h = st
                if np.isnan(low):
                    low = st
                h = max(h, st)
                low = min(low, st)
            o = round(o, 2)
            h = round(h, 2)
            low = round(low, 2)
            c = round(c, 2)
            bars.append(dict(date=date, open=o, high=h, low=low, close=c))
            date = date + dt.timedelta(hours=1)
        df = pd.DataFrame(data=bars).set_index('date')

        bars_model.restore(df)

    ticker_model.observe(lambda x: x, lambda ticker: generate_data(ticker))
