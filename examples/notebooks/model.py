import datetime as dt
import math
import typing
from dataclasses import dataclass, field

import numpy as np
from soso import state


@dataclass
class Bars:
    date: typing.List[dt.datetime] = field(default_factory=list)
    open: typing.List[float] = field(default_factory=list)
    high: typing.List[float] = field(default_factory=list)
    low: typing.List[float] = field(default_factory=list)
    close: typing.List[float] = field(default_factory=list)


@dataclass
class Chart:
    bars: Bars = field(default_factory=Bars)
    selected_ticker: str = ''


@dataclass
class State:
    tickers: typing.List[str] = field(default_factory=lambda: ['TICK1', 'TICK2', 'TICK3'])
    chart: Chart = field(default_factory=Chart)


class Model(state.Model[State]):
    def __init__(self) -> None:
        super().__init__(State())
        _init_gbm_generator(self.submodel(lambda x: x.chart.selected_ticker),
                            self.submodel(lambda x: x.chart.bars))


def _init_gbm_generator(ticker_model: state.protocols.Model[str],
                        bars_model: state.protocols.Model[Bars]) -> None:
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

        st = float(np.random.randint(50, 150))
        bars = Bars()
        date = dt.datetime(2020, 1, 1, 9, 30)
        for hour in range(24):
            o = h = low = c = np.nan
            for minute in range(60):
                st = generate_value()
                if math.isnan(o):
                    o = st
                c = st
                if math.isnan(h):
                    h = st
                if math.isnan(low):
                    low = st
                h = max(h, st)
                low = min(low, st)
            o = round(o, 2)
            h = round(h, 2)
            low = round(low, 2)
            c = round(c, 2)
            bars.date.append(date)
            bars.open.append(o)
            bars.high.append(h)
            bars.low.append(low)
            bars.close.append(c)
            date = date + dt.timedelta(hours=1)
        bars_model.restore(bars)

    ticker_model.observe(lambda ticker: generate_data(ticker))
