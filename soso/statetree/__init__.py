import typing

StateT = typing.TypeVar('StateT', covariant=True)


class Model(typing.Generic[StateT]):
    def __init__(self):
        model_klass = self.__orig_bases__[-1]
        state_klass = typing.get_args(model_klass)[0]
        self.__current_state = state_klass()

    def update(self, *args, **kwargs: typing.Any):
        func: typing.Callable[[StateT], None]

        if len(args) == 0:
            assert len(kwargs) != 0

            def doit(state):
                for key, value in kwargs.items():
                    setattr(state, key, value)

            func = doit
        else:
            assert len(args) == 1
            assert len(kwargs) == 0
            assert callable(args[0])
            func = args[0]

        # TODO
        func(self.__current_state)

    @property
    def state(self) -> StateT:
        return self.__current_state
