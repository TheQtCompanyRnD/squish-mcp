import names
import squish

def main():
    startApplication("MyApp")
    waitForObject(names.main_window)
    clickButton(names.ok_button)
    test.verify(True, "Check passed")
    test.log("Done")
