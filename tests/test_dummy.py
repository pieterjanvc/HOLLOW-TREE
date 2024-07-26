from shiny.playwright import controller
from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.pytest import create_app_fixture

pytest_plugins = ["tests.testDBs"]

app = create_app_fixture("dummy_app/test_app.py")

def test_basic_app(page: Page, app: ShinyAppProc):
    page.goto(app.url)
    txt = controller.OutputText(page, "txt")
    textBox = controller.InputText(page, "txtBox")
    textBox.set("Hello")
    txt.expect_value("Hello")
    textBox.set("test")
    txt.expect_value("tet")
    # slider = controller.InputSlider(page, "n")
    # slider.set("1")
    # txt.expect_value("n*2 is 0")



