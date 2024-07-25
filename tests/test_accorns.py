# *************************************
# ----------- TEST ACCORNS -----------
# *************************************
# https://shiny.posit.co/py/docs/end-to-end-testing.html

from shiny.playwright import controller
from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.pytest import create_app_fixture
import os
import pytest

# pytest tests\test_scuirrel.py --headed

app = create_app_fixture("../accorns_app.py")

@pytest.fixture()
def start():
    print("HI")
    # If an accorns database is present, rename it temporarily so we can start with a clean database
    if os.path.exists("../appData/accorns.db"):
        os.rename("../appData/accorns.db", "../appData/accorns.db.bak")

    yield    

    # Rename the test database to accorns-test.db and the original database back to accorns.db
    #overwrite last test database if needed
    if os.path.exists("../appData/accorns-test.db"):
        os.remove("../appData/accorns-test.db")
        os.rename("../appData/accorns.db", "../appData/accorns-test.db")

    if os.path.exists("../appData/accorns.db.bak"):
        os.rename("../appData/accorns.db.bak", "../appData/accorns.db")

def test1(page: Page, app: ShinyAppProc):
    
    #Start
    page.goto(app.url)  
    controller.InputText(page, "login-lUsername").set("admin")
    controller.InputPassword(page, "login-lPassword").set("admin")
    controller.InputActionButton(page, "login-login").click()
    # Check if all the tabs are visible
    controller.NavsetPill(page, id = "postLoginTabs").expect_nav_values(["vTab", "gTab", "tTab", "qTab", "uTab"])
    # Go to the "Groups" tab
    controller.NavPanel(page, id = "postLoginTabs", data_value="gTab").click()
    controller.InputActionButton(page, "groups-newGroup").click()
    controller.InputText(page, "groups-ngGroup").set("testGroup")
    controller.InputText(page, "groups-ngDescr").set("testGroup description")
    controller.InputActionButton(page, "groups-ngAdd").click()

    





