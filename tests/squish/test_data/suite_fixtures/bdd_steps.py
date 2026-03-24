import names
from squish import *

@given("the application is running")
def step_given_app_running(context):
    startApplication("MyApp")

@when("I enter |any| in the |any| field")
def step_when_enter(context, value, field):
    type(waitForObject(names.input_field), value)

@then("I should see the dashboard")
def step_then_dashboard(context):
    test.verify(waitForObjectExists(names.dashboard), "Dashboard visible")
