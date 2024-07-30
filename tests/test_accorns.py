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
import os
import re

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

# Run the test with the following commands:
#   pytest tests\test_accorns.py 
#       Optional arguments:
#       --headed (browser is visible)
#       --slowmo 200 (slow down every action by 500ms to see what's happening)
#       --save (save timestamped database, otherwise overwrite previous test database)
#       --testVectorDB (test the vector database, uses more GPT tokens)


# Initialise Shiny app
app = create_app_fixture("../accorns_app.py")

def test_accorns(page: Page, app: ShinyAppProc, cmdopt):
    
    #Start app
    page.goto(app.url)
    page.wait_for_load_state("networkidle")

    with appDBConn() as conn:

        # Request reset admin password
        controller.InputActionLink(page, "login-showReset").click(timeout=10000)
        controller.InputText(page, "login-loginReset-rUsername").set("admin", timeout=10000)
        controller.InputActionButton(page, "login-loginReset-request").click(timeout=10000)
        page.get_by_text("SUCCESS: Contact an admin to get your reset code").wait_for(timeout=10000)
        page.locator('"Dismiss"').click(timeout=10000) # Close the modal

        #LOGIN TAB      
        controller.InputText(page, "login-lUsername").set("admin", timeout=10000)
        controller.InputPassword(page, "login-lPassword").set("admin", timeout=10000)
        controller.InputActionButton(page, "login-login").click(timeout=10000)
        # Check if all the tabs are visible
        controller.NavsetPill(page, id = "postLoginTabs").expect_nav_values(["vTab", "gTab", "tTab", "qTab", "uTab"])

        # USER MANAGEMENT TAB
        controller.NavPanel(page, id = "postLoginTabs", data_value="uTab").click(timeout=10000)
        # Generate a code for a user, instructor and admin
        for user in ["User", "Instructor", "Admin"]:
            controller.InputNumeric(page, "userManagement-numCodes").set("1", timeout=10000)
            controller.InputSelect(page, "userManagement-role").set(user, timeout=10000)
            controller.InputText(page, "userManagement-note").set(f"test: add {user}", timeout=10000)
            controller.InputActionButton(page, "userManagement-generateCodes").click(timeout=10000)
        
        controller.DownloadLink(page, "userManagement-downloadCodes").click(timeout=10000)
        controller.OutputDataFrame(page, "userManagement-newCodesTable").expect_nrow(1)
        controller.OutputDataFrame(page, "userManagement-codesTable").expect_nrow(3)

        # GROUPS TAB
        controller.NavPanel(page, id = "postLoginTabs", data_value="gTab").click(timeout=10000)
        controller.InputActionButton(page, "groups-newGroup").click(timeout=10000)
        controller.InputText(page, "groups-ngGroup").set("testGroup", timeout=10000)
        controller.InputText(page, "groups-ngDescr").set("testGroup description", timeout=10000)
        controller.InputActionButton(page, "groups-ngAdd").click(timeout=10000)
        controller.InputSelect(page, "groups-gID").expect_selected("2", timeout=10000)

        # Generate a code for a group join by user and admin
        controller.InputText(page, "groups-note").set("test: add user", timeout=10000)
        controller.InputActionButton(page, "groups-generateCodes").click(timeout=10000)

        controller.InputSelect(page, "groups-role").set("Admin", timeout=10000)
        controller.InputNumeric(page, "groups-numCodes").set("1", timeout=10000)
        controller.InputText(page, "groups-note").set("test: add admin", timeout=10000)
        controller.InputActionButton(page, "groups-generateCodes").click(timeout=10000)
        controller.DownloadLink(page, "groups-downloadGroupCodes").click(timeout=10000)

        # Check DB
        q = dbQuery(conn, 'SELECT * FROM "group"')
        assert q.shape[0] == 2
        assert q["group"].iloc[1] == "testGroup"
        assert q["description"].iloc[1] == "testGroup description"
        assert not q.iloc[1].isna().any()

        # Check DB
        accessCodes = dbQuery(conn, 'SELECT * FROM "accessCode"')
        assert accessCodes.shape[0] == 6
        assert accessCodes["codeType"].tolist() == [1,0,0,0,2,2]
        assert accessCodes["uID_creator"].iloc[0] == 2
        assert accessCodes["adminLevel"].tolist()[1:6] == [1.0, 2.0, 3.0, 1.0, 2.0]       

        # VECTOR DB TAB
        # A a new file to the database
        controller.NavPanel(page, id = "postLoginTabs", data_value="vTab").click(timeout=10000)
        controller.OutputDataFrame(page, "vectorDB-filesTable").select_rows([0])
        controller.OutputUi(page, "vectorDB-fileInfo").expect_container_tag("div")
        
        if cmdopt["testVectorDB"]:
            controller.InputFile(page, "vectorDB-newFile").set(os.path.join(curDir, "testData", "MendelianInheritance.txt"),
                                                    expect_complete_timeout=10000)
            # If successful, the file will be added to the table
            controller.OutputDataFrame(page, "vectorDB-filesTable").expect_nrow(2, timeout=10000)
        
        # TOPICS TAB
        controller.NavPanel(page, id = "postLoginTabs", data_value="tTab").click(timeout=10000)
        
        # Add a new topic
        controller.InputActionButton(page, "topics-tAdd").click(timeout=10000)
        controller.InputText(page, "topics-ntTopic").set("Mend", timeout=10000)
        controller.InputText(page, "topics-ntDescr").set("Basics about genetic inheritance", timeout=10000)
        controller.InputActionButton(page, "topics-ntAdd").click(timeout=10000)
        assert page.get_by_text("New topic must be at least 6 characters").count() == 1        
        controller.InputText(page, "topics-ntTopic").set("Mendelain Inheritance", timeout=10000)
        controller.InputActionButton(page, "topics-ntAdd").click(timeout=10000)

        controller.InputActionButton(page, "topics-tEdit").click(timeout=10000)
        controller.InputText(page, "topics-etInput").set("Mendelian Inheritance", timeout=10000)
        controller.InputActionButton(page, "topics-etEdit").click(timeout=10000)
        controller.InputSelect(page, "topics-tID").expect_selected("2", timeout=10000)

        # Check DB
        q = dbQuery(conn, 'SELECT * FROM "topic"')
        assert q.shape[0] == 2
        assert q["topic"].iloc[1] == "Mendelian Inheritance"
        assert q["description"].iloc[1] == "Basics about genetic inheritance"
        assert not q.iloc[1].isna().any()

        # Add a new concept
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set("Info", timeout=10000)
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)
        assert page.get_by_text("New concept must be at least 6 characters").count() == 1        
        controller.InputText(page, "topics-ncInput").set("Gregor Johann Mendel was a nineteenth-century Moravian monk", timeout=10000)
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)
        controller.OutputDataFrame(page, "topics-conceptsTable").select_rows([0])
        
        controller.InputActionButton(page, "topics-cEdit").click(timeout=10000)
        controller.InputText(page, "topics-ecInput").set("Gregor Mendel was a nineteenth-century monk", timeout=10000)
        controller.InputActionButton(page, "topics-ncEdit").click(timeout=10000)
        controller.OutputDataFrame(page, "topics-conceptsTable").expect_cell(
            "Gregor Mendel was a nineteenth-century monk", row = 0, col = 0
        )
        
        # Check DB
        q = dbQuery(conn, 'SELECT * FROM "concept" WHERE "sID" IS NOT NULL')
        assert q.shape[0] == 1
        assert q["concept"].iloc[0] == "Gregor Mendel was a nineteenth-century monk"
        assert not q.loc[:, q.columns != 'description'].iloc[0].isna().any()

        # QUIZ GENERATION TAB
        controller.NavPanel(page, id = "postLoginTabs", data_value="qTab").click(timeout=10000)
        
        # Add a new quiz question
        if cmdopt["testVectorDB"]:
            controller.InputActionButton(page, "quizGeneration-qGenerate").click(timeout=10000)
            page.get_by_text(re.compile("Correct answer:"), exact=False).wait_for(timeout=10000) 
            q = dbQuery(conn, 'SELECT "optionA" FROM "question"')
            controller.InputText(page, "quizGeneration-rqOA").expect_value(q["optionA"].iloc[0])

        # End the session and start new one
        page.reload()

        # Create new accounts

        # User
        controller.InputText(page, "login-cUsername").set("testUser", timeout=10000)
        # controller.InputText(page, "login-cFirstName").set("user")
        # controller.InputText(page, "login-cLastName").set("test")
        # controller.InputText(page, "login-cEmail").set("user@test.com")
        controller.InputPassword(page, "login-cPassword").set("user123ABC!", timeout=10000)
        controller.InputPassword(page, "login-cPassword2").set("user123ABC!", timeout=10000)
        controller.InputText(page, "login-cAccessCode").set(accessCodes["code"].iloc[1], timeout=10000)
        controller.InputActionButton(page, "login-createAccount").click(timeout=10000)

        # Instructor
        controller.InputText(page, "login-cUsername").set("testInstructor", timeout=10000)
        controller.InputPassword(page, "login-cPassword").set("instr123ABC!", timeout=10000)
        controller.InputPassword(page, "login-cPassword2").set("instr23ABC!", timeout=10000)
        controller.InputText(page, "login-cAccessCode").set(accessCodes["code"].iloc[2], timeout=10000)
        controller.InputActionButton(page, "login-createAccount").click(timeout=10000)
        page.get_by_text("Passwords do not match").wait_for(timeout=10000)
        controller.InputPassword(page, "login-cPassword2").set("instr123ABC!", timeout=10000)        
        controller.InputActionButton(page, "login-createAccount").click(timeout=10000)

        # wait 1 second
        page.wait_for_timeout(1000)
        
        # Check the DB
        q = dbQuery(conn, 'SELECT * FROM "user"')
        assert q.shape[0] == 4
        assert q["username"].tolist() == ["anonymous", "admin", "testUser", "testInstructor"]
        assert q["adminLevel"].tolist() == [0, 3, 1, 2]

        # Reset the admin password
        controller.InputActionLink(page, "login-showReset").click(timeout=10000)
        controller.InputText(page, "login-loginReset-rUsername").set("admin", timeout=10000)
        controller.InputPassword(page, "login-loginReset-rPassword").set("admin123ABC!", timeout=10000)
        controller.InputPassword(page, "login-loginReset-rPassword2").set("admin123ABC!", timeout=10000)
        controller.InputText(page, "login-loginReset-rAccessCode").set(accessCodes["code"].iloc[0])
        controller.InputActionButton(page, "login-loginReset-reset").click(timeout=10000)
        page.locator('"Dismiss"').click(timeout=10000)  # Close the modal

        # Try to login with user account
        controller.InputText(page, "login-lUsername").set("testUser", timeout=10000)
        controller.InputPassword(page, "login-lPassword").set("user123ABC!", timeout=10000)
        controller.InputActionButton(page, "login-login").click(timeout=10000)
        page.get_by_text("You do not have the required permissions to access this application").wait_for(timeout=10000)

        # Login with the instructor account and join the group
        controller.InputText(page, "login-lUsername").set("testInstructor", timeout=10000)
        controller.InputPassword(page, "login-lPassword").set("instr123ABC!", timeout=10000)
        controller.InputActionButton(page, "login-login").click(timeout=10000)
        
        controller.NavPanel(page, id = "postLoginTabs", data_value="gTab").click(timeout=10000)
        controller.InputActionButton(page, "groups-joinGroup-joinGroup").click(timeout=10000)
        controller.InputText(page, "groups-joinGroup-accessCode").set(accessCodes["code"].iloc[4], timeout=10000)
        controller.InputActionButton(page, "groups-joinGroup-submitJoin").click(timeout=10000)
        page.get_by_text("This access code only allows to join groups as a user in SCUIRREL").wait_for(timeout=10000)
        controller.InputText(page, "groups-joinGroup-accessCode").set(accessCodes["code"].iloc[5], timeout=10000)
        controller.InputActionButton(page, "groups-joinGroup-submitJoin").click(timeout=10000)
        controller.InputSelect(page, "groups-gID").expect_selected("2", timeout=10000)

        page.reload()

        # Check the DB for correct session info
        q = dbQuery(conn, 'SELECT * FROM "session"')
        assert q["uID"].iloc[0] == 2
        assert not q.loc[:, q.columns != 'error'].iloc[0].isna().any()

        





