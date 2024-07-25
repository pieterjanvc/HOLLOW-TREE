# *************************************
# ----------- TEST ACCORNS -----------
# *************************************
# https://shiny.posit.co/py/docs/end-to-end-testing.html

from shiny.playwright import controller
from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.pytest import create_app_fixture

app = create_app_fixture("../accorns_app.py")

def test1(page: Page, app: ShinyAppProc):
    page.goto(app.url)  
    controller.InputText(page, "login-lUsername").set("admin")
    controller.InputText(page, "login-lPassword").set("admin")
    controller.InputActionButton(page, "login-login").click()
    controller.NavPanel(page, "vTab")
    True


