# soso.state

`soso.state` is a Python 3.8+ implementation of a general state container
pattern. Its goals are similar to Redux, but where it differs is that it
is designed to perform well by default through the use of little to no 
copying and a focus on finely grained notifications for any subset of the
application state.

## Status

Although this particular library is new, multiple versions of it are 
in production in private in a variety of industries ranging from healthcare
to finance. See the Motivation section below.

## Main Features

* Centralized:
    * Single source of truth for entire application state
    * Easily implement undo/redo/persistence
* Flexible:
    * Subscribe to changes in any subset of the application state you are interested in
* Efficient
    * Zero copying except for snapshot/restore functionality
    * Only events for data that is actually changed are propagated
* Predictable:
    * Consistent state => predictable application

## Quickstart

`$ pip install git+https://github.com/sohailsomani/soso-state`

**Note**: The most up-to-date version of this code is in [`test_README.py`](tests/test_README.py).

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

# Subscribe to changes in the 0th position of the regional_managers array.
# The callback function is always called initially with the current values
token = app.subscribe(lambda state: state.regional_managers[0],print)
# Output: Person("Michael","Scott")

# Subscribe to Pam's last name updates
app.subscribe(lambda state: state.employees[1].last_name,print)

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

# TODO: Subscribe to multiple values at the same time, 
# notified only once when one or more change at the same time
app.subscribe(lambda state: state.regional_managers,
              lambda state: state.employees,
              print)
# output: [Person("Jim","Halpert")] [Person("Pam","Halpert")]
```

## Async examples

```python
async def myfunc(app:AppModel):
  regional_managers = await app.event(lambda state: state.regional_managers)
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
