import copy
import typing

StateT = typing.TypeVar('StateT',covariant=True)

class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        state_klass = typing.get_args(model_klass)[0]
        self.__current_state = state_klass()

    def update(self,**kwargs):
        pass

