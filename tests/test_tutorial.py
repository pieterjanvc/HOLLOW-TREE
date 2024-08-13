# *************************************
# ----------- TEST ACCORNS -----------
# *************************************
# https://shiny.posit.co/py/docs/end-to-end-testing.html
# https://shiny.posit.co/py/api/testing/

from shiny.playwright import controller
from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from conftest import appDBConn, dbQuery
import pytest
import os
import re
import pysrt
from datetime import datetime

curDir = os.path.dirname(os.path.realpath(__file__))

def addSubtitle(page, text, avg_wpm=150, min_wait_seconds=3, maxChars=135):

    # Split the text into multiple pieces each no longer than 150 characters. Only split by sentence
    text = text.replace("\n", " ")
    text = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text.strip())

    # Loop through the result and merge the text into longer strings as long as the length is less than 150
    newText = []
    tempText = ""
    for i in range(len(text)):
        if len(tempText) + len(text[i]) < maxChars:
            tempText += (" " if tempText != "" else "") + text[i].strip()
        else:
            newText.append(tempText)
            tempText = text[i].strip()

    newText.append(tempText)

    for text in newText:

        word_count = len(text.split())
        
        # Estimate reading time in seconds
        reading_time_seconds = (word_count / avg_wpm) * 60
        
        # Ensure the wait time is at least the minimum wait time
        wait_time = max(reading_time_seconds, min_wait_seconds)

        page.evaluate((
            f"const customHtml = `<div id='subtitles'>{text}</div>`;"
            """
            document.body.insertAdjacentHTML('beforeend', customHtml);
                        
            const style = document.createElement('style');
            style.textContent = `
                #subtitles {
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    background-color: rgba(0, 0, 0, 0.85); /* Semi-transparent background */
                    color: white;
                    text-align: center;
                    padding: 10px;
                    font-size: 20px;
                    box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.5);
                    z-index: 9999;
                        }
                    `;
            document.head.appendChild(style);
        """))

        page.wait_for_timeout(wait_time*1000)

        page.evaluate("document.getElementById('subtitles').remove()")


def test_accorns(cmdopt, page, accornsApp):
    # Ignore this test if the scuirrelOnly flag is set
    if cmdopt["scuirrelOnly"] and not cmdopt["publishPostgres"]:
        return

    # Start app
    page.goto(accornsApp.url)
    page.wait_for_load_state("networkidle")         

    with appDBConn(remoteAppDB=cmdopt["publishPostgres"]) as conn:

        # Insert an access code for a new instructor into the database
        dbQuery(
            conn,
            (
                'INSERT INTO "accessCode" ("code", "codeType", "uID_creator", "adminLevel")'
                "VALUES ('W4t-00k-gTR', 0, 2, 2);"
            ),
            insert=True,
        )
        
        subt = """Welcome to ACCORNS! In this tutorial, we will go through the main 
        features of the app."""
        addSubtitle(page, subt)

        subt = """Let's start by creating an account"""
        addSubtitle(page, subt) 

        subt = """Before you can create an account, you need an access code provided by
          an administrator. Let's say we have an access code 'W4t-00k-gTR'. 
          On the right side of the login page, fill out the sigh up form and provide the access code"""
        addSubtitle(page, subt) 

        controller.InputText(page, "login-cUsername").set("topInstructor", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-cPassword").set(
            "instr123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-cPassword2").set(
            "instr123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputText(page, "login-cAccessCode").set(
            'W4t-00k-gTR', timeout=10000
        )
        page.wait_for_timeout(1000)

        subt = """Click the 'Create Account' button to create your account"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "login-createAccount").click(timeout=10000)

        subt = """Let's now login with the new account details"""
        addSubtitle(page, subt)        

        # LOGIN TAB
        controller.InputText(page, "login-lUsername").set("topInstructor", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-lPassword").set("instr123ABC!", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "login-login").click(timeout=10000)

        subt = """ACCORNS is used to manage SCUIRREL. Please refer to the SCUIRREL tutorial if needed. 
        The first thing to do in ACCORNS is to add new course materials to the database.
        These files will be used by SCUIRREL to guide students through the learning process
        by providing the AI with relevant background information. 
        To upload a new file, simply click on the 'New file' button and choose 
        a file from your computer. You can upload different types of text files like PDF, DOCX, and TXT files."""
        addSubtitle(page, subt)    
       
        # VECTOR DB TAB
        # A a new file to the database
        # controller.NavPanel(page, id="postLoginTabs", data_value="vTab").click(
        #     timeout=10000
        # )        

        controller.InputFile(page, "vectorDB-newFile").set(
            os.path.join(curDir, "testData", "MendelianInheritance.txt"),
            expect_complete_timeout=10000,
        )
        subt = """Depending on the size of the file, uploading and processing may take some time. 
        After a file is uploaded, you can view the file information by 
        clicking on the file name in the table at the top of the page"""
        addSubtitle(page, subt)          
        
        controller.OutputDataFrame(page, "vectorDB-filesTable").select_rows([1])
        subt = """You can now see a summary of the file information being displayed. 
        Let's now start creating some new topics that can reviewed
         by students in SCUIRREL based on the uploaded materials"""
        addSubtitle(page, subt)

        subt = """Before we get started with this, we need to create a new group to 
        organize the topics"""
        addSubtitle(page, subt)

        subt = """Navigate to the 'Groups' tab"""
        addSubtitle(page, subt)
        controller.NavPanel(page, id="postLoginTabs", data_value="gTab").click(
            timeout=10000
        )
        subt = """Create a new group by clicking on the 'New Group' button"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "groups-newGroup").click(timeout=10000)
        subt = """Set the group name, an optional group description and click the 'Add Group' button"""
        addSubtitle(page, subt)
        controller.InputText(page, "groups-ngGroup").set("Genetics101", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputText(page, "groups-ngDescr").set(
            "Topics from the GEN101 course", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "groups-ngAdd").click(timeout=10000)

        subt = """Now that we have a group, let's add a new topic. Navigate to the 'Topics' tab"""
        addSubtitle(page, subt)  
        controller.NavPanel(page, id="postLoginTabs", data_value="tTab").click(
            timeout=10000
        )

        subt = """You can compare a topic to a short bookchapter you want SCUIRREL to 
        review with a student in a short conversation (e.g. about 5 minutes). 
        To create a new topic, select the group you want to add it to and 
        click the 'Add New' button"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "topics-tAdd").click(timeout=10000)
        subt = """Fill out the topic name and optional description and click the 'Add' button"""
        addSubtitle(page, subt)
        controller.InputText(page, "topics-ntTopic").set("Mendelian inheritance", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputText(page, "topics-ntDescr").set(
            "Basics about genetic inheritance", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "topics-ntAdd").click(timeout=10000)        

        # controller.InputActionButton(page, "topics-tEdit").click(timeout=10000)
        # controller.InputText(page, "topics-etInput").set(
        #     "Mendelian Inheritance", timeout=10000
        # )
        # controller.InputActionButton(page, "topics-etEdit").click(timeout=10000)
        # controller.InputSelect(page, "topics-tID").expect_selected("2", timeout=10000)

        subt = """Each topic is broken down into concepts that SCUIRREL will use to 
        guide the conversation with the student. You can think of concepts as list of 
        facts or ideas listed in a bookchapter. To add a new concept to the selected topic, 
        click the 'Add New' button in the concepts section"""
        addSubtitle(page, subt)

        # Add a new concept
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        subt = """Define the concept in a single sentence (e.g. as a fact). There is no need to provide
        context as this will be provided by the files you uploaded earlier into teh database"""
        addSubtitle(page, subt)       
        controller.InputText(page, "topics-ncInput").set(
            "Gregor Mendel, the father of modern genetics, was a nineteenth-century monk", timeout=10000
        )
        subt = """Click the 'Add' button to add the concept to the topic"""
        addSubtitle(page, subt)   
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)

        subt = """Keep adding concepts until you feel you have enough to cover the topic"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set(
            """We have two copies (alleles) of each gene, one from each parent""", 
            timeout=10000
        )
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set(
            """An organism with at least one dominant allele will display the effect of the dominant allele""", 
            timeout=10000
        )
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set(
            """To display a recessive trait, an organism must have two copies of a recessive allele""", 
            timeout=10000
        )
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)

        # controller.OutputDataFrame(page, "topics-conceptsTable").select_rows([0])

        # controller.InputActionButton(page, "topics-cEdit").click(timeout=10000)
        # controller.InputText(page, "topics-ecInput").set(
        #     "Gregor Mendel was a nineteenth-century monk", timeout=10000
        # )
        # controller.InputActionButton(page, "topics-ncEdit").click(timeout=10000)
        # controller.OutputDataFrame(page, "topics-conceptsTable").expect_cell(
        #     "Gregor Mendel was a nineteenth-century monk", row=0, col=0
        # )

        # # QUIZ GENERATION TAB
        # controller.NavPanel(page, id="postLoginTabs", data_value="qTab").click(
        #     timeout=10000
        # )

        # # Add a new quiz question
        # if cmdopt["newVectorDB"]:
        #     controller.InputActionButton(page, "quizGeneration-qGenerate").click(
        #         timeout=10000
        #     )
        #     page.get_by_text(re.compile("Correct answer:"), exact=False).wait_for(
        #         timeout=10000
        #     )
        #     q = dbQuery(conn, 'SELECT "optionA" FROM "question"')
        #     controller.InputText(page, "quizGeneration-rqOA").expect_value(
        #         q["optionA"].iloc[0]
        #     )
        # else:
        #     dbQuery(
        #         conn,
        #         (
        #             'INSERT INTO "question" ("qID", "sID", "tID", "cID", "question",'
        #             '"answer", "archived", "created", "modified", "optionA", "explanationA",'
        #             '"optionB", "explanationB", "optionC", "explanationC", "optionD", "explanationD")'
        #             "VALUES ('1', '1', '2', '11',"
        #             "'What was Gregor Mendel''s occupation in the nineteenth century?',"
        #             "'A', '0', '2024-07-30 10:27:34', '2024-07-30 10:27:34',"
        #             "'Monk','Correct! Gregor Mendel was a nineteenth-century Moravian monk who"
        #             "conducted hybridization experiments with pea plants.', 'Scientist',"
        #             "'Incorrect. While Gregor Mendel is known for his scientific work, his occupation"
        #             "was actually a monk.', 'Farmer', 'Incorrect. Gregor Mendel was not a farmer;"
        #             "he was a monk who conducted experiments with pea plants.', 'Politician',"
        #             "'Incorrect. Gregor Mendel was not a politician; he was a monk who made significant"
        #             "contributions to the field of genetics.');"
        #         ),
        #         insert=True,
        #     )

        # # End the session and start new one
        # page.reload()

        

        # # wait 1 second
        # page.wait_for_timeout(1000)

        # # Check the DB
        # q = dbQuery(conn, 'SELECT * FROM "user"')
        # assert q.shape[0] == 4
        # assert q["username"].tolist() == [
        #     "anonymous",
        #     "admin",
        #     "testUser",
        #     "testInstructor",
        # ]
        # assert q["adminLevel"].tolist() == [0, 3, 1, 2]

        # # Reset the admin password
        # controller.InputActionLink(page, "login-showReset").click(timeout=10000)
        # controller.InputText(page, "login-loginReset-rUsername").set(
        #     "admin", timeout=10000
        # )
        # controller.InputPassword(page, "login-loginReset-rPassword").set(
        #     "admin123ABC!", timeout=10000
        # )
        # controller.InputPassword(page, "login-loginReset-rPassword2").set(
        #     "admin123ABC!", timeout=10000
        # )
        # controller.InputText(page, "login-loginReset-rAccessCode").set(
        #     accessCodes["code"].iloc[0]
        # )
        # controller.InputActionButton(page, "login-loginReset-reset").click(
        #     timeout=10000
        # )
        # page.locator('"Dismiss"').click(timeout=10000)  # Close the modal

        # # Try to login with user account
        # controller.InputText(page, "login-lUsername").set("testUser", timeout=10000)
        # controller.InputPassword(page, "login-lPassword").set(
        #     "user123ABC!", timeout=10000
        # )
        # controller.InputActionButton(page, "login-login").click(timeout=10000)
        # page.get_by_text(
        #     "You do not have the required permissions to access this application"
        # ).wait_for(timeout=10000)

        # # Login with the instructor account and join the group
        # controller.InputText(page, "login-lUsername").set(
        #     "testInstructor", timeout=10000
        # )
        # controller.InputPassword(page, "login-lPassword").set(
        #     "instr123ABC!", timeout=10000
        # )
        # controller.InputActionButton(page, "login-login").click(timeout=10000)

        # controller.NavPanel(page, id="postLoginTabs", data_value="gTab").click(
        #     timeout=10000
        # )
        # controller.InputActionButton(page, "groups-joinGroup-joinGroup").click(
        #     timeout=10000
        # )
        # controller.InputText(page, "groups-joinGroup-accessCode").set(
        #     accessCodes["code"].iloc[4], timeout=10000
        # )
        # controller.InputActionButton(page, "groups-joinGroup-submitJoin").click(
        #     timeout=10000
        # )
        # page.get_by_text(
        #     "This access code only allows you to join this group as a user in SCUIRREL"
        # ).wait_for(timeout=10000)
        # controller.InputText(page, "groups-joinGroup-accessCode").set(
        #     accessCodes["code"].iloc[5], timeout=10000
        # )
        # controller.InputActionButton(page, "groups-joinGroup-submitJoin").click(
        #     timeout=10000
        # )
        # controller.InputSelect(page, "groups-gID").expect_selected("2", timeout=10000)

        # page.reload()

        # # Check the DB for correct session info
        # q = dbQuery(conn, 'SELECT * FROM "session"')
        # assert q["uID"].iloc[0] == 2
        # assert not q.loc[:, q.columns != "error"].iloc[0].isna().any()

         # # USER MANAGEMENT TAB
        # controller.NavPanel(page, id="postLoginTabs", data_value="uTab").click(
        #     timeout=10000
        # )
        # # Generate a code for a user, instructor and admin
        # for user in ["User", "Instructor", "Admin"]:
        #     controller.InputNumeric(page, "userManagement-numCodes").set(
        #         "1", timeout=10000
        #     )
        #     controller.InputSelect(page, "userManagement-role").set(user, timeout=10000)
        #     controller.InputText(page, "userManagement-note").set(
        #         f"test: add {user}", timeout=10000
        #     )
        #     controller.InputActionButton(page, "userManagement-generateCodes").click(
        #         timeout=10000
        #     )

        # controller.DownloadLink(page, "userManagement-downloadCodes").click(
        #     timeout=10000
        # )
        # controller.OutputDataFrame(page, "userManagement-newCodesTable").expect_nrow(1)
        # controller.OutputDataFrame(page, "userManagement-codesTable").expect_nrow(3)

        # # Request reset admin password
        # controller.InputActionLink(page, "login-showReset").click(timeout=10000)
        # controller.InputText(page, "login-loginReset-rUsername").set(
        #     "admin", timeout=10000
        # )
        # controller.InputActionButton(page, "login-loginReset-request").click(
        #     timeout=10000
        # )
        # page.get_by_text("SUCCESS: Contact an admin to get your reset code").wait_for(
        #     timeout=10000
        # )
        # page.locator('"Dismiss"').click(timeout=10000)  # Close the modal

        # # Generate a code for a group join by user and admin
        # controller.InputText(page, "groups-note").set("test: add user", timeout=10000)
        # controller.InputActionButton(page, "groups-generateCodes").click(timeout=10000)

        # controller.InputSelect(page, "groups-role").set("Admin", timeout=10000)
        # controller.InputNumeric(page, "groups-numCodes").set("1", timeout=10000)
        # controller.InputText(page, "groups-note").set("test: add admin", timeout=10000)
        # controller.InputActionButton(page, "groups-generateCodes").click(timeout=10000)
        # controller.DownloadLink(page, "groups-downloadGroupCodes").click(timeout=10000)