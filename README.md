# soso.statetree

`soso.statetree` is a Python implementation of a general state container
pattern. Its goal is to centralize application state similar to Redux but allow
efficient monitoring and updating of any portion of the state tree. 

With `soso.statetree`, you describe the shape of any portion of your state and
compose it as needed for a particular application. Less time spent thinking
about boilerplate means more time spent thinking about the actual business
problem.

## Quickstart

`$ pip install soso-statetree`

```python
from soso import statetree
from dataclasses import dataclass, field

@dataclass
class Person:
  first_name: str
  last_name: str

@dataclass
class AppState:
  regional_managers: list[Person] = field(default_factory=list)
  assistant_to_the_regional_managers: list[Person] = field(default_factory=list)
  employees: list[Person] = field(default_factory=list)
  
class AppModel(statetree.Model[AppState]):
  pass
  
...
app = AppModel(AppState(
  regional_managers = [Person("Michael","Scott")],
  assistant_to_the_regional_managers = [Person("Dwight","Schrute")],
  employees = [Person("Jim","Halpert"),
               Person("Pam","Beesly")] 
))

# Subscribe to changes in the 0th position of the regional_managers array
token = app.subscribe(lambda state: state.regional_managers[0],print)
app.update(regional_managers = [Person("Dwight","Schrute")],
           assistant_to_the_regional_managers = [])
# output: Person("Dwight","Schrute")
token.disconnect()
app.update(regional_managers = [Person("Jim","Halpert")])
# No output
```

## Main Features

* Intuitive (hopefully) syntax
* Compose state and model behaviour
* Potentially as efficient, if not more efficient than hand-written code, with
  fewer bugs and way less code
* No cloning of state
* Sensible default behaviour
* Judicious use of Python 3.9 typing to catch errors as early as possible

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
in one place.

Consider the following code:

```python
class MyModel:
   def __init__(self):
     self.__myproperty = 5
     self.myproperty_changed = Event()
     
   @property
   def myproperty(self) -> int:
     return self.__myproperty
     
   @myproperty.setter
   def myproperty(self,val:int):
     if self.__myproperty == val: return
     self.__myproperty = val
     self.myproperty_changed.signal()
...

m = MyModel()
m.myproperty_changed.connect(print)
print(m.myproperty)
m.myproperty = 12
```

Although we have two major concepts here, `MyModel` and its property
`myproperty`, there are nearly a dozen lines of boilerplate, none of which
really add much value. With `soso.statetree`, this code looks something like:

```python
from soso import statetree
from dataclasses import dataclass

@dataclass
class State:
  myproperty: int = 5
  
class MyModel(statetree.Model[State]):
  pass
  
m = MyModel()
state:State # for typing support only
m.on_changed(lambda state: state.myproperty)
print(m.state.myproperty)
m.update(myproperty = 12)
```

It is much clearer that we have an application state with a single property and
we get all of the features of the hand-written version, for free.

**NOTE:** I am not at all married to this syntax. I feel there could be more
consistency in the syntax for events, state viewing and state updating.
