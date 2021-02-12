import asyncio
import typing
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from soso import state


@dataclass
class Person:
    first_name: str
    last_name: str


@dataclass
class AppState:
    regional_managers: typing.List[Person] = field(default_factory=list)
    assistant_to_the_regional_managers: typing.List[Person] = field(
        default_factory=list)
    employees: typing.List[Person] = field(default_factory=list)


class AppModel(state.Model[AppState]):
    pass


class TestREADME(unittest.TestCase):
    def test_readme(self) -> None:
        app = AppModel()
        # Add some initial values
        app.update(
            regional_managers=[Person("Michael", "Scott")],
            assistant_to_the_regional_managers=[Person("Dwight", "Schrute")],
            employees=[Person("Jim", "Halpert"),
                       Person("Pam", "Beesly")])

        # Ensure that the values actually were persisted to the application
        # state
        self.assertEqual(app.state.regional_managers,
                         [Person("Michael", "Scott")])
        self.assertEqual(app.state.assistant_to_the_regional_managers,
                         [Person("Dwight", "Schrute")])
        self.assertEqual(app.state.employees,
                         [Person("Jim", "Halpert"),
                          Person("Pam", "Beesly")])

        x: AppState
        regional_manager = MagicMock()
        # Observe changes in the first regional manager, a token is returned to
        # allow you to disconnect later if needed.
        token = app.observe(lambda x: x.regional_managers[0], regional_manager)
        # Whenever we observe, the callback is always initially called with
        # the current value.
        regional_manager.assert_called_with(Person("Michael", "Scott"))

        pams_last_name = MagicMock()
        app.observe(lambda x: x.employees[1].last_name, pams_last_name)
        pams_last_name.assert_called_with("Beesly")

        # create a submodel to track Pam Beesly
        pam:state.protocols.Model[Person] = state.SubModel(app,lambda x: x.employees[1])
        pams_last_name.reset_mock()
        pam.update(last_name = "Halpert")

        self.assertEqual(app.state.employees[1].last_name, "Halpert")
        # Note that the callback was called with exactly the attribute that was
        # observed to: x.employees[1].last_name
        pams_last_name.assert_called_with("Halpert")

        regional_manager.reset_mock()
        app.update(regional_managers=[Person("Dwight", "Schrute")],
                   assistant_to_the_regional_managers=[])

        # In this case, the entire first object is returned as opposed to Pam's
        # last name
        regional_manager.assert_called_with(Person("Dwight", "Schrute"))
        regional_manager.reset_mock()
        token.disconnect()

        task = asyncio.get_event_loop().create_task(self.__myfunc(app))
        asyncio.get_event_loop().call_soon(
            lambda: app.update(regional_managers=[Person("Jim", "Halpert")]))
        asyncio.get_event_loop().run_until_complete(task)

        self.assertEqual(task.result(), [Person("Jim", "Halpert")])
        # we disconnected the token, so no more notifications for the regional
        # manager
        regional_manager.assert_not_called()

    async def __myfunc(self, app: AppModel) -> typing.List[Person]:
        def prop(state: AppState) -> typing.List[Person]:
            return state.regional_managers

        regional_managers = await app.wait_for(prop)
        return regional_managers
