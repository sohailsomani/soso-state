# soso.state

`soso.state` is a Python 3.8+ implementation of a general state management
pattern using a mostly declarative syntax. It is inspired by and has goals
similar to Redux, but where it differs is that it is designed to perform well by
default through the use of little to no copying and a focus on efficient, finely
grained notifications for any subset of the application state. Through the
declarative approach, it is designed to centralize most, if not all decisions
regarding efficiency and structural organization.

* [Status](#status)
* [Main Benefits](#main-benefits)
* [Quickstart](#quickstart)
* [Motivation](#motivation)
* [Implementation](#implementation)
* [Obvious optimizations](#obvious-optimizations)

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
    * Easily implement [undo/redo](examples/undo.py)/[persistence](examples/todo.py)
* Flexible:
    * Observe changes to any subset of the application state you are interested in
* Efficient
    * Zero copying except for snapshot/restore functionality
    * Only events for data that is actually changed are propagated
* Predictable:
    * Consistent state => predictable application

## Quickstart

`$ pip install git+https://github.com/sohailsomani/soso-state`

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

Boring and straightforward

## Obvious optimizations

**Note:** At the moment, [test_benchmark.py](tests/test_benchmark.py) shows that
setting a value through a `soso.state.Model` and processing the event is about
2x as slow as doing it by hand which is approximately what would be expected for
completely non-optimized code.

The most obvious optimization would be to compile the state traversal into
python code. This sounds complex and scary but isn't really. At the moment, we
do something like this:

```python
root = self.__current_state
for prop in properties:
  root = getattr(root,prop)
```

This code compiles down to:

```python
  2           0 LOAD_FAST                1 (properties)
              2 GET_ITER
        >>    4 FOR_ITER                14 (to 20)
              6 STORE_FAST               2 (prop)

  3           8 LOAD_GLOBAL              0 (getattr)
             10 LOAD_FAST                0 (root)
             12 LOAD_FAST                2 (prop)
             14 CALL_FUNCTION            2
             16 STORE_FAST               0 (root)
             18 JUMP_ABSOLUTE            4

  4     >>   20 LOAD_FAST                0 (root)
             22 RETURN_VALUE
```

Whereas the hand-written code:

```python
root = self.__current_state.property1.property2
```

compiles to:

```python
  2           0 LOAD_FAST                0 (root)
              2 LOAD_ATTR                0 (a)
              4 LOAD_ATTR                1 (b)
              6 RETURN_VALUE
```

So obviously, caching and compiling the traversals that are needed:

1. The traversal to find the correct event to emit
2. The traversal to find the current property
3. The traversal to set the new value

would result in a system that is effectively equivalent to hand-written code.

This is the trapdoor for performance referenced earlier and I believe it would
be very difficult to improve upon this performance for hand-written code. There
are still other performance improvements that can be made, but this is the one
that could overcome performance issues if needed.

This is not the only way to optimize the code, but given that most of the code
the developer writes is **meta-programming**, it leaves lots of options open.

As of yet, I haven't had to optimize this type of implementation at this level
after having used it for about 3 years, including in a situation where we had
real-time sensor updates and needed to maintain 60FPS so take from that what you
will.

Not to say I wouldn't enjoy doing the above :-)

### A second trapdoor

Say you have a real-time data feed coming in and you _really_ don't like the
overhead of `app.update()` for the purpose of notifications, in that case you
can do something like:

```python
bid_event = app.event(lambda x: x.stock["IBM"].bid)
...
def on_bid_update(bid):
  # manually update the state and emit the event
  app.state.stock["IBM"].bid = bid
  bid_event.emit(bid)
```

This should be done with care as it has the possibility for creating an
inconsistent state. The idea is that the first trapdoor, if implemented, should
do exactly this, but automatically.

### Atomic updates

To implement atomic updates (apply all changes or none), the safest thing to do
would be to copy the state, apply changes to the copy and then overwrite the
original state.

As this is a performance issue, it is currently left incomplete.
