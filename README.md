# soso.state

`soso.state` is a Python 3.8+ implementation of a general state management
pattern using a mostly declarative syntax. It is inspired by and has goals
similar to Redux, but where it differs is that it is designed to perform well by
default through the use of little to no copying and a focus on efficient, finely
grained notifications for any subset of the application state. Through the
declarative approach, it is designed to centralize most, if not all decisions
regarding efficiency and structural organization.

* [Status](#status): In daily use
* [Main Benefits](#main-benefits)
* [Quickstart](#quickstart)
* [Motivation](#motivation): Don't Repeat Yourself
* [Implementation](#implementation): Proxy -> writes -> events
* [Profiling notes](#profiling-notes): Use PyPy 3.8 if perf critical, otherwise 14us overhead per update

## Status

Although this particular library is new, multiple versions of it are
in production in private in a variety of industries ranging from healthcare
to finance. See the [Motivation](#motivation) section below.

In particular, although the design allows for atomic updates, those are not
really implemented due to a lack of a pressing need. This means that if there
are indeed errors during updates, it could leave things in an inconsistent
state. But we don't write code with errors in it anyway. It's the outside world
that is wrong.

## Main Benefits

* Centralized:
    * Single source of truth for entire application state
    * Easily implement
      [undo/redo](examples/undo.py)/[persistence](examples/todo.py)
* Flexible:
    * Observe changes to any subset of the application state you are interested
      in
* Efficient
    * Zero copying except for snapshot/restore functionality
    * Only events for data that is actually changed are propagated
* Predictable:
    * Consistent state => predictable application
    * Using Python's optional strong static typing (no, really) to catch as many
      errors as possible.

## Quickstart

```sh
$ python3 -m pip install git+https://github.com/sohailsomani/soso-state
```

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

class AppModel(state.Model[AppState]):
  pass

app = AppModel()

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

# Observe changes to Pam's last name updates
app.observe(lambda state: state.employees[1].last_name,print)

# Update regional_managers and assistant_to_the_regional_managers atomically
app.update(regional_managers = [Person("Dwight","Schrute")],
           assistant_to_the_regional_managers = [])
# output: Person("Dwight","Schrute")

# No longer interested in regional_manager updates
token.disconnect()

# For more complex state updates, use a function. Note that
# this is NOT the actual state object, it is a write-only proxy.
# Do not try to read from the argument that is passed in
def pam_gets_married(state:AppState):
   state.employees[1].last_name = "Halpert"
app.update(pam_gets_married)
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

## Async examples

```python
async def myfunc(app:AppModel):
  regional_managers = await app.wait_for(lambda state: state.regional_managers)
  print(regional_managers)

asyncio.get_event_loop().create_task(myfunc(app))
# No output yet
app.update(regional_managers = [Person("Pam","Halpert")],
           employees=[])
# Output: [Person("Pam","Halpert")]
```

## Motivation

The original version of this implementation was written in Typescript by yours
truly and is very similar in spirit. Alas, that version is in some corporate
repository somewhere making lives easier for a select few. Indeed, a separate
Python version also written by yours truly is also currently in some corporate
repository somewhere and I am tired of rewriting the damn thing every few years.
So I am rewriting it for the last time.

The idea was initially conceived after finding the Redux model was way too slow
for real-time code (well, as real-time as you can get in a browser) and that the
Redux way of solving the performance issue required way too much ceremony on the
part of developers. That is, we could not find a way to factor out the thinking
about performance in one place.

**NOTE:** I am not at all married to this syntax. I feel there could be more
consistency in the syntax for events, state viewing and state updating.

## Implementation

Boring and straightforward. Your state update function gets a proxy. The proxy
records what you set. The `update` function then updates the actual state using
this record and emits the appropriate events.

## Profiling notes

**Note:** See the output of [test_benchmark.py](tests/test_benchmark.py)
[here](https://github.com/sohailsomani/soso-state/runs/1809770788#step:5:134).

In a nutshell, for CPython update+event emit takes ~14 microseconds as compared
to a manual update + event which takes about ~2 microseconds.

For pypy3.8, update+event emit takes 300 nanoseconds as compared to a manual
update + event which takes 200 nanoseconds.

So if performance is a major concern, then use pypy3.8.

### Atomic updates

To implement atomic updates (apply all changes or none), the safest thing to do
would be to copy the state, apply changes to the copy and then overwrite the
original state.

As this is a performance issue, it is currently left incomplete.

However, it could be done with a context manager. Note that this would not
prevent events from propagating so its probably useless:

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
