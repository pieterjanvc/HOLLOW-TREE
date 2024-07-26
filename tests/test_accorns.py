# *************************************
# ----------- TEST ACCORNS -----------
# *************************************
# https://shiny.posit.co/py/docs/end-to-end-testing.html
# https://shiny.posit.co/py/api/testing/

from shiny.playwright import controller
from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from shiny.pytest import create_app_fixture
from conftest import appDBConn, dbQuery
import pytest

# Run the test with the following commands:
#   pytest tests\test_accorns.py 
#       Optional arguments:
#       --headed (browser is visible)
#       --save (save timestamped database, otherwise overwrite previous test database)

# Initialise Shiny app
app = create_app_fixture("../accorns_app.py")

def test_accorns(page: Page, app: ShinyAppProc):
    
    #Start app
    page.goto(app.url)
    with appDBConn() as conn:
        #LOGIN TAB      
        controller.InputText(page, "login-lUsername").set("admin")
        controller.InputPassword(page, "login-lPassword").set("admin")
        controller.InputActionButton(page, "login-login").click()
        # Check if all the tabs are visible
        controller.NavsetPill(page, id = "postLoginTabs").expect_nav_values(["vTab", "gTab", "tTab", "qTab", "uTab"])

        # USER MANAGEMENT TAB
        controller.NavPanel(page, id = "postLoginTabs", data_value="uTab").click()
        # Generate a code for a user, instructor and admin
        for user in ["User", "Instructor", "Admin"]:
            controller.InputNumeric(page, "userManagement-numCodes").set("1")
            controller.InputSelect(page, "userManagement-role").set(user)
            controller.InputText(page, "userManagement-note").set(f"test: add {user}")
            controller.InputActionButton(page, "userManagement-generateCodes").click()
        
        controller.DownloadLink(page, "userManagement-downloadCodes").click()
        controller.OutputDataFrame(page, "userManagement-newCodesTable").expect_nrow(1)
        controller.OutputDataFrame(page, "userManagement-codesTable").expect_nrow(3)

        # Check DB
        q = dbQuery(conn, 'SELECT * FROM "accessCode"')
        assert q.shape[0] == 3
        assert q["codeType"].iloc[0] == 0
        assert q["uID_creator"].iloc[0] == 2
        assert q["adminLevel"].tolist() == [1, 2, 3]

        # GROUPS TAB
        controller.NavPanel(page, id = "postLoginTabs", data_value="gTab").click()
        controller.InputActionButton(page, "groups-newGroup").click()
        controller.InputText(page, "groups-ngGroup").set("testGroup")
        controller.InputText(page, "groups-ngDescr").set("testGroup description")
        controller.InputActionButton(page, "groups-ngAdd").click()
        
        # End the session
        page.reload()

        # Check the DB for correct session info
        q = dbQuery(conn, 'SELECT * FROM "session"')
        assert q["uID"].iloc[0] == 2
        assert not q.loc[:, q.columns != 'error'].iloc[0].isna().any()

        





