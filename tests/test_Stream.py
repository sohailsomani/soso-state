import asyncio
import math
import random
import typing
import unittest
from dataclasses import dataclass, field

from soso import state

# An example (not really a test) of how to implement streaming calculations

NaN = float('nan')


@dataclass
class State:
    sensor_value: float = NaN
    period_10_range: typing.Tuple[float, float] = field(
        default_factory=lambda: (NaN, NaN))
    period_30_range: typing.Tuple[float, float] = field(
        default_factory=lambda: (NaN, NaN))


class Model(state.Model[State]):
    pass


async def range_calculator(source: state.protocols.Model[float],
                           sink: state.protocols.Model[typing.Tuple[float,
                                                                    float]],
                           n: int) -> None:
    values = []
    while True:
        # Although this only returns a new value when the source changes, one
        # can imagine using a "tick" variable if that is undesired
        new_value = await source.wait_for(lambda x: x)
        values.append(new_value)
        values = values[-n:]
        if len(values) < n:
            continue
        rng = (min(values), max(values))
        sink.restore(rng)


async def sensor(sink: state.protocols.Model[float], iters: int) -> None:
    for _ in range(iters):
        value = random.random()
        sink.restore(value)
        await asyncio.sleep(0.01)


class TestStream(unittest.TestCase):
    def test_simple(self) -> None:
        model = Model()
        f1 = range_calculator(model.submodel(lambda x: x.sensor_value),
                              model.submodel(lambda x: x.period_10_range),
                              n=10)
        f2 = range_calculator(model.submodel(lambda x: x.sensor_value),
                              model.submodel(lambda x: x.period_30_range),
                              n=30)

        # We'll generate enough to get output for period_10_range but not
        # enough for period_30_range
        generator = sensor(model.submodel(lambda x: x.sensor_value), iters=20)

        loop = asyncio.get_event_loop()
        loop.create_task(f1)
        loop.create_task(f2)
        t3 = loop.create_task(generator)

        # Ensure all NaN
        self.assertTrue(math.isnan(model.state.period_10_range[0]))
        self.assertTrue(math.isnan(model.state.period_10_range[1]))
        self.assertTrue(math.isnan(model.state.period_30_range[0]))
        self.assertTrue(math.isnan(model.state.period_30_range[1]))

        asyncio.get_event_loop().run_until_complete(t3)

        # Ensure we get values for period_10, but not period_30
        self.assertTrue(not math.isnan(model.state.period_10_range[0]))
        self.assertTrue(not math.isnan(model.state.period_10_range[1]))
        self.assertTrue(math.isnan(model.state.period_30_range[0]))
        self.assertTrue(math.isnan(model.state.period_30_range[1]))

        # Run it a bit more so we get values for period_30

        generator = sensor(model.submodel(lambda x: x.sensor_value), iters=20)
        t4 = loop.create_task(generator)

        asyncio.get_event_loop().run_until_complete(t4)

        # Now should have values for both
        self.assertTrue(not math.isnan(model.state.period_10_range[0]))
        self.assertTrue(not math.isnan(model.state.period_10_range[1]))
        self.assertTrue(not math.isnan(model.state.period_30_range[0]))
        self.assertTrue(not math.isnan(model.state.period_30_range[1]))
