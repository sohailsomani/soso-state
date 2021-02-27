# soso.state

`soso.state` is a simple, yet powerful Python library inspired by Redux which
gives you a single place (`Model[State]`) to put all your running application state.
Updates are mediated through the `Model.update` function and changes are
observed through the `Model.observe` function. Via the use of `SubModel`s, you
can write components that read from and write to any level of application state
without loss of generality.

[This image](README.png) may help get a better idea of the different components
and how they work together.


* [Main Benefits](#main-benefits): it gud
* [Quickstart - Event-based](#quickstart---event-based)
* [Quickstart - Streaming](#quickstart---streaming)
* [Status](#status): In daily use
* [Motivation](#motivation): Don't Repeat Yourself, Keep It Simple
* [Implementation](#implementation): Proxy -> writes -> events
* [Gotchas](#gotchas): Sadly, there is ~one~~two~one
* [Profiling notes](#profiling-notes): ~100K updates/second with CPython, ~4
  million updates/second with pypy3.8

## Main Benefits

* Centralized:
    * Single source of truth for entire application state
    * Easily implement
      [undo/redo](examples/undo.py)/[persistence](examples/todo.py)
* Flexible:
    * Observe changes to any subset of the application state you are interested
      in ([ui.py](examples/notebooks/ui.py))
    * Create [streaming](tests/test_Stream.py) calculations with relative ease.
* Efficient:
    * Zero copying except for snapshot/restore functionality
    * Only events for data that is actually changed are propagated
* Predictable:
    * Consistent state => predictable application
    * Using Python's optional strong static typing ([no, really](typecheck.png)) to catch as many
      errors as possible.

## Quickstart - Event-based

```sh
$ python3 -m pip install git+https://github.com/sohailsomani/soso-state
```

The entire interface is defined in two places:

1. [soso.state.protocols](soso/state/protocols.py): The `Model[State]` interface
2. `soso.state.build_model(State) -> Model[State]`

Use the latter to create instances of the former. `State` should be a dataclass
that describes the application state.

Fuller examples are below.

**Note**: The most up-to-date version of this code is in
[`test_README.py`](tests/test_README.py). Feel free to check out the code and
use the `tox` command to play around with the test.

```python
from dataclasses import dataclass, field

from soso import state


@dataclass
class Person:
  first_name: str
  last_name: str

@dataclass
class AppState:
  regional_managers: list[Person] = field(default_factory=list)
  assistant_to_the_regional_managers: list[Person] = field(default_factory=list)
  employees: list[Person] = field(default_factory=list)

app = state.build_model(AppState)

app.update(
  regional_managers = [Person("Michael","Scott")],
  assistant_to_the_regional_managers = [Person("Dwight","Schrute")],
  employees = [Person("Jim","Halpert"),
               Person("Pam","Beesly")]
)

# Observe changes in the 0th position of the regional_managers array.
# The callback function is always called initially with the current values
token = app.observe(lambda state: state.regional_managers[0],print)
# Output: Person("Michael","Scott")

# Update regional_managers and assistant_to_the_regional_managers atomically
app.update(regional_managers = [Person("Dwight","Schrute")],
           assistant_to_the_regional_managers = [])
# output: Person("Dwight","Schrute")

# No longer interested in regional_manager updates
token.disconnect()

# Observe changes to Pam's last name
app.observe(lambda state: state.employees[1].last_name,print)
# output: Beesley

# create a submodel to track Pam Beesly
pam = app.submodel(lambda x: x.employees[1])
pam.update(last_name = "Halpert")
# output: "Halpert"

app.update(regional_managers = [Person("Jim","Halpert")])
# No output, since no longer interested

# TODO: Observe multiple values at the same time,
# notified only once when one or more change at the same time
app.observe(lambda state: state.regional_managers,
            lambda state: state.employees,
            print)
# output: [Person("Jim","Halpert")] [Person("Pam","Halpert")]
```


## Quickstart - Streaming

The streaming interface is a simple adaptation of the event-based interface to
make use in async code (like generators) more palatable and easier to debug.

Imagine a running calculation like a mean with state. One can solve this problem
using callbacks, but that can often lead to spaghetti code with captured
variables all over the place.

The key entrypoint for this usage is the function
`Model[State].wait_for(property_access_function=None)`

This returns an awaitable `Event[T]` which allows you to stream and sink
calculations.

A simple (incomplete) example is below. A fuller example is available in [streaming](tests/test_Stream.py).

```python
from soso import state

# Step 1: define the shape of your state
@dataclasses.dataclass
class Mean:
  num_periods: int = 10
  mean: float = float("nan")

@dataclasses.dataclass
class State:
  value: int = 0
  mean: Mean = field(default_factory=Mean)
  
# Step 2: create the stateful function and take in a source/sink
# Note that although we could have the function take a Mean as 
# a sink, that makes the function less reusable so we separate
# num_periods and the eventual target value
async def mean_calc(source: state.protocols.Model[int],
                    num_periods: state.protocols.Model[int],
                    sink: state.protocols.Model[float]):
  values = []
  async for value in source.wait_for():
    values.append(value)
    # not enough values yet
    if len(values) < num_periods.state:
       continue
    values = values[-num_periods.state:]
    mean = sum(values)/float(len(values))
    sink.restore(mean)
    
# The value comes from some other process, not
# important for the example.
async def value_generator(some_source: AsyncIterator[float],
                          sink: state.protocols.Model[float]):
  async for value in some_source:
    sink.put(value)
    
# Step 3: create a model and the relevant tasks:
model = state.build_model(State)

mean = asyncio.get_event_loop().create_task(mean_calc(
  model.submodel(lambda x: x.value),
  model.submodel(lambda x: x.mean.num_periods),
  model.submodel(lambda x: x.mean.mean)
))

value =  asyncio.get_event_loop().create_task(value_generator(
  get_value_generator(), # this depends on your app
  model.submodel(lambda x: x.value)
))

# run the task
loop.run_until_complete(value)
```

## Status

Although this particular library is new, multiple versions of it are
in production in private in a variety of industries ranging from healthcare
to finance. See the [Motivation](#motivation) section below.

In particular, although the design allows for atomic updates, those are not
really implemented due to a lack of a pressing need. This means that if there
are indeed errors during updates, it could leave things in an inconsistent
state. But we don't write code with errors in it anyway. It's the outside world
that is wrong.



## Motivation

The idea was initially conceived after finding the Redux model was way too slow
for real-time code (well, as real-time as you can get in a browser) and that the
Redux way of solving the performance issue required way too much ceremony on the
part of developers. That is, we could not find a way to factor out the thinking
about performance in one place.

See
[here](https://github.com/reduxjs/reselect#motivation-for-memoized-selectors)
for an excellent example of where the Redux approach has issues.

Then multiply the proposed solution (memoized selectors) by the size of your
team and you will have so much repetitive code that the actual logic of your app
will be buried within obscure incantations and cache bugs that will drive you
crazy. Look no further than
[here](https://github.com/reduxjs/reselect#sharing-selectors-with-props-across-multiple-component-instances)
for evidence of the type of thing you can expect to see.

The goal then, is to achieve the same performance improvements, without writing
a ton of unnecessary code both as part of a library and on the part of the
developer. A lazy developer is a good developer.

The original version of this implementation was written in Typescript by yours
truly and is very similar in spirit. Alas, that version is in some corporate
repository somewhere making lives easier for a select few. Indeed, a separate
Python version also written by yours truly is also currently in some corporate
repository somewhere and I am tired of rewriting the damn thing every few years.
So I am rewriting it for the last time.

**NOTE:** I am not at all married to this syntax. I feel there could be more
consistency in the syntax for events, state viewing and state updating.

## Implementation

Boring and straightforward. Your state update function gets a proxy. The proxy
records what you set. The `update` function then updates the actual state using
this record and emits the appropriate events.

## Gotchas

### Type checking

Python type checking through mypy is still in its early phases even though it is
quite robust and accurate. There are occasionally issues with imports especially
since `soso.state` lives in a namespace only package (why, I don't know, why not
I guess).

All this means is that your `mypy.ini` file should look a lot like this
project's [mypy.ini](mypy.ini). The reason being that you really want to know if
mypy is unable to locate imports which will impact typing and will potentially
lead to you thinking your code is type safe when it is not.

## Profiling notes

**Note:** See the output of [test_benchmark.py](tests/test_benchmark.py)
[here](https://github.com/sohailsomani/soso-state/runs/1809770788#step:5:134).

In CPython, `soso.state` update+event emit has a median overhead of ~10
microseconds vs 1.5 microseconds.

For pypy3.8, the median update+event emit is ~260 nanoseconds vs 60 nanoseconds.

Therefore, if performance is a major concern, use pypy3.8.

There have been minor structural optimizations implemented, but nothing for high
performance Python. There is the possibility of a major (i.e., order of
magnitude improvement) via a redesign of the implementation but it would take a
long time to implement and there is no pressing need for it.

### Atomic updates

To implement atomic updates (apply all changes or none), the safest thing to do
would be to copy the state, apply changes to the copy and then overwrite the
original state.

As this is a performance issue, it is currently left incomplete.

However, it could be done with a context manager. Note that in the case of an
error, there will be events sent for the entire tree as it is being restored.

This is probably fine.

```python
from contextlib import contextmanager


def atomic_updates(model):
    snapshot = model.snapshot()
    try:
        yield
    except:
        model.restore(snapshot)

...
with atomic_updates(model):
    model.update(hello="goodbye")
    def update(x):
        raise RuntimeError()
    model.update(update) # oops, error, no changes made
```
