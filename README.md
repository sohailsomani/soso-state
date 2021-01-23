# soso.statetree

`soso.statetree` is a Python implementation of a general state container
pattern. Its goal is to centralize application state similar to Redux but allow
efficient monitoring and updating of any portion of the state tree. The original
version of this implementation was written in Typescript and is very similar in
spirit. Alas, that version is in some corporate repository somewhere making
lives easier for a select few. Indeed, a separate Python version written by
yours truly is also currently in some corporate repository somewhere and I am
tired of rewriting the damn thing every few years.

With `soso.statetree`, you describe the shape of any portion of your state and
combine it as needed for a particular application.

## Main Features

* Intuitive syntax
* Potentially as efficient, if not more efficient than hand-written code, with
  fewer bugs
* Sensible default behaviour
* Judicious use of Python typing to catch errors as early as possible
* Requires Python 3.9 for typing/protocols niceties

## Motivation
 
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
x:State # for typing support in the lambda only
m.on_changed(lambda x: x.myproperty,print)
```

It is much clearer that we have an application state with a single property and
we get all of the features of the hand-written version, for free.
