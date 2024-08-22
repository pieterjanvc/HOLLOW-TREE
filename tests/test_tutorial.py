# *************************************
# ----------- APP TUTORIALS -----------
# *************************************


# pytest tests\test_tutorial.py --headed --slowmo 200 --record

from shiny.playwright import controller
from shiny.run import ShinyAppProc
from playwright.sync_api import Page
from conftest import appDBConn, dbQuery
import pytest
import os
import re
from datetime import datetime

curDir = os.path.dirname(os.path.realpath(__file__))


def addSubtitle(page, text, avg_wpm=150, min_wait_seconds=3, maxChars=135):
    # Split the text into multiple pieces each no longer than 150 characters. Only split by sentence
    text = text.replace("\n", " ")
    text = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", text.strip())

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

        page.evaluate(
            (
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
                    background-color: rgba(0, 0, 0, 0.85);
                    color: white;
                    text-align: center;
                    padding: 10px;
                    font-size: 20px;
                    text-wrap: balance;
                    box-shadow: 0 -2px 5px rgba(0, 0, 0, 0.5);
                    z-index: 9999;
                        }
                    `;
            document.head.appendChild(style);
        """
            )
        )

        page.wait_for_timeout(wait_time * 1000)

        page.evaluate("document.getElementById('subtitles').remove()")


def test_accorns_tutorial(cmdopt, page, accornsApp):
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

        subt = """Let's start by creating an account. This will allow you access to both
        ACCORNS and SCUIRREL providing you have the right access code. You will receive 
        an access code via an administrator or other instructor.  
        Let's say we have an access code 'W4t-00k-gTR'. On the right side of the login page, 
        fill out the sign up form and provide the access code"""
        addSubtitle(page, subt)

        controller.InputText(page, "login-newUsername").set(
            "topInstructor", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-newPassword").set(
            "instr123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-newPassword2").set(
            "instr123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputText(page, "login-accessCode").set(
            "W4t-00k-gTR", timeout=10000
        )
        page.wait_for_timeout(1000)

        subt = """Click the 'Create Account' button to create your account"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "login-createAccount").click(timeout=10000)

        subt = """Let's now login with the new account details"""
        addSubtitle(page, subt)

        # LOGIN TAB
        controller.InputText(page, "login-username").set(
            "topInstructor", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-password").set(
            "instr123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "login-login").click(timeout=10000)

        subt = """The first thing to do when you are setting up ACCORNS is to add new 
        reference materials to the database. These files will be used by SCUIRREL to 
        guide students through the learning process by providing the AI with relevant 
        background information on topics you'll create later. 
        To upload a new file, simply click on the 'Pick a file' button and choose 
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
        After a file has been processed, you can view the file information by 
        clicking on the file name in the table at the top of the page"""
        addSubtitle(page, subt)

        controller.OutputDataFrame(page, "vectorDB-filesTable").select_rows([1])
        subt = """You can now see a summary of the file information being displayed. 
        Let's now start creating some new topics that can be reviewed
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

        subt = """You can compare a topic to a short book chapter you want SCUIRREL to 
        review with a student in a short conversation (e.g. about 5 minutes). 
        To create a new topic, select the group you want to add it to and 
        click the 'Add New' button"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "topics-tAdd").click(timeout=10000)
        subt = """Fill out the topic name and optional description and click the 'Add' button"""
        addSubtitle(page, subt)
        controller.InputText(page, "topics-ntTopic").set(
            "Mendelian inheritance", timeout=10000
        )
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
        facts or ideas listed in a book chapter. To add a new concept to the selected topic, 
        click the 'Add New' button in the concepts section"""
        addSubtitle(page, subt)

        # Add a new concept
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        subt = """Define the concept in a single sentence (e.g. as a fact). There is no need to provide
        context as this will be provided by the files you uploaded earlier into the database"""
        addSubtitle(page, subt)
        controller.InputText(page, "topics-ncInput").set(
            "Gregor Mendel, the father of modern genetics, was a nineteenth-century monk",
            timeout=10000,
        )
        subt = """Click the 'Add' button to add the concept to the topic"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)

        subt = (
            """Keep adding concepts until you feel you have enough to cover the topic"""
        )
        addSubtitle(page, subt)
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set(
            """We have two copies (alleles) of each gene, one from each parent""",
            timeout=10000,
        )
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set(
            """An organism with at least one dominant allele will display the effect of the dominant allele""",
            timeout=10000,
        )
        controller.InputActionButton(page, "topics-ncAdd").click(timeout=10000)
        controller.InputActionButton(page, "topics-cAdd").click(timeout=10000)
        controller.InputText(page, "topics-ncInput").set(
            """To display a recessive trait, an organism must have two copies of a recessive allele""",
            timeout=10000,
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

        subt = """Once you have setup a topic and related concepts, 
        you can now generate quiz questions to test the student's understanding of the topic. 
        Let's navigate to the 'Quiz Generation' tab"""
        addSubtitle(page, subt)

        # QUIZ GENERATION TAB
        controller.NavPanel(page, id="postLoginTabs", data_value="qTab").click(
            timeout=10000
        )

        subt = """Start by selecting the group and topic you want to generate quiz questions for.
        Then, click the 'Generate new' button"""
        addSubtitle(page, subt)
        # Add a new quiz question
        controller.InputActionButton(page, "quizGeneration-qGenerate").click(
            timeout=10000
        )
        subt = """Note that generating quiz questions may take some time and it's
        possible that the process may fail. In case of failure, you will be notified and 
        you can try again later. If successful, you will see a summary of the generated 
        questions along with the option to edit all parts of the question. 
        After you finished reviewing and editing the questions, you should save your changes"""
        addSubtitle(page, subt)

        subt = """Now you have setup new materials, it's time to invite students or other 
        instructors to create accounts and access what you have created. To start,
        navigate to the 'User management' tab"""
        addSubtitle(page, subt)
        controller.NavPanel(page, id="postLoginTabs", data_value="uTab").click(
            timeout=10000
        )

        subt = """Remember how you used an access code to create your account? 
        You can generate new access codes for other people to create accounts. 
        Let's start by generating a new access code for students to create an account 
        with SCUIRREL access. Set the number of codes to generate, choose 'User' as the role,
        and optionally add a note why you are generating the codes"""
        addSubtitle(page, subt)

        controller.InputNumeric(page, "userManagement-numCodes").set(
            "10", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputSelect(page, "userManagement-role").set("User", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputText(page, "userManagement-note").set(
            "Student accounts for GEN101", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "userManagement-generateCodes").click(
            timeout=10000
        )

        subt = """Once you generated the codes, you can copy or download them to share 
        with the intended users."""
        addSubtitle(page, subt)

        controller.DownloadLink(page, "userManagement-downloadCodes").click(
            timeout=10000
        )

        subt = """Let's also generate a new access code for a co-instructor to create an
        account with both ACCORNS and SCUIRREL access."""
        addSubtitle(page, subt)

        controller.InputNumeric(page, "userManagement-numCodes").set("1", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputSelect(page, "userManagement-role").set(
            "Instructor", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputText(page, "userManagement-note").set(
            "Instructor account for GEN101", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "userManagement-generateCodes").click(
            timeout=10000
        )
        page.wait_for_timeout(500)

        # Select first row in code table
        controller.OutputDataFrame(page, "userManagement-newCodesTable").select_rows(
            [0]
        )

        subt = """You can keep track of any unclaimed codes in the table on this page.
        IMPORTANT: access codes only give you access to the apps itself, but
        not to the topic groups created by you or other users. To join a group, you need
        to generate separate group access code. Let's do that now by navigating back 
        to the 'Groups' tab"""
        addSubtitle(page, subt)

        controller.NavPanel(page, id="postLoginTabs", data_value="gTab").click(
            timeout=10000
        )

        subt = """The process of generating group access codes is identical to generating
        user access codes. User codes can be used to join your group in SCUIRREL. 
        Admin codes can be used to join your group in ACCORNS and manage the group and
        all its topics."""
        addSubtitle(page, subt)

        # Generate a code for a group join by user and admin
        controller.InputSelect(page, "groups-role").set("User", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputNumeric(page, "groups-numCodes").set("5", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputText(page, "groups-note").set(
            "Student codes for GEN101", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "groups-generateCodes").click(timeout=10000)

        subt = """Once you generated the codes, users can use them to join your group in 
        SCUIRREL or ACCORNS depending on the role of the code. If you receive a code from
        another instructor or admin, you can click the 'Join Group' button and provide the code"""
        addSubtitle(page, subt)

        controller.InputActionButton(page, "groups-joinGroup-joinGroup").click(
            timeout=10000
        )
        page.wait_for_timeout(1000)
        page.click('button:text("Cancel")')

        subt = """Finally, you can close the app simply by refreshing or closing the page"""
        addSubtitle(page, subt)

        page.reload()

        subt = """You can continue where you left off by logging in again with your account 
        details. Should you ever forget your password or like to change it, you can 
        request a reset code by clicking the 'Reset Password' button on the login page"""
        addSubtitle(page, subt)

        controller.InputActionLink(page, "login-showReset").click(timeout=10000)
        subt = """Provide your username, then click the 'Request Reset Code' button."""
        addSubtitle(page, subt)
        controller.InputText(page, "login-loginReset-rUsername").set(
            "topInstructor", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "login-loginReset-request").click(
            timeout=10000
        )
        subt = """You should see a message that a reset code has been created.
        You now have to reach out to another instructor or admin to get the code.
        Given we still know our old password, let's login an see where to find the reset 
        codes"""
        addSubtitle(page, subt)
        page.locator('"Dismiss"').click(timeout=10000)  # Close the modal

        controller.InputText(page, "login-username").set(
            "topInstructor", timeout=10000
        )
        page.wait_for_timeout(300)
        controller.InputPassword(page, "login-password").set(
            "instr123ABC!", timeout=10000
        )
        page.wait_for_timeout(300)
        controller.InputActionButton(page, "login-login").click(timeout=10000)

        subt = """Navigate to the 'User management' tab"""
        addSubtitle(page, subt)
        controller.NavPanel(page, id="postLoginTabs", data_value="uTab").click(
            timeout=10000
        )
        page.wait_for_timeout(500)
        # Select first row in reset table
        controller.OutputDataFrame(page, "userManagement-resetTable").select_rows([0])
        subt = """You will now see a table with all requested reset codes you can 
        share with those who requested it."""
        addSubtitle(page, subt)

        page.wait_for_timeout(1000)
        page.reload()

        subt = """This concludes the ACCORNS tutorial. If you have any questions,
        please reach out to the app administrator or read the documentation"""
        addSubtitle(page, subt)

        accornsApp.close()

        # page.get_by_text("File info").scroll_into_view_if_needed()
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
        # controller.InputText(page, "login-username").set("testUser", timeout=10000)
        # controller.InputPassword(page, "login-password").set(
        #     "user123ABC!", timeout=10000
        # )
        # controller.InputActionButton(page, "login-login").click(timeout=10000)
        # page.get_by_text(
        #     "You do not have the required permissions to access this application"
        # ).wait_for(timeout=10000)

        # # Login with the instructor account and join the group
        # controller.InputText(page, "login-username").set(
        #     "testInstructor", timeout=10000
        # )
        # controller.InputPassword(page, "login-password").set(
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


def test_scuirrel_tutorial(cmdopt, page, scuirrelApp):
    # Start app
    page.goto(scuirrelApp.url)
    page.wait_for_load_state("networkidle")

    with appDBConn(remoteAppDB=cmdopt["publishPostgres"]) as conn:
        # Insert an access code for a new instructor into the database
        dbQuery(
            conn,
            (
                'INSERT INTO "accessCode" ("code", "codeType", "uID_creator", "adminLevel")'
                "VALUES ('4Xt-Bb4-487', 0, 2, 1);"
            ),
            insert=True,
        )

        subt = """Welcome! This application allows you to review important topics you are 
        interested in with the help of an AI named SCUIRREL. The topics have been 
        carefully curated by real humans, but SCUIRREL will try it's best to take the 
        time to review them with you at your own pace. In this tutorial, we will go 
        through the main features of the app."""
        addSubtitle(page, subt)

        subt = """Let's start by creating an account. You will receive an access code 
        via an administrator or instructor in order to be able to create an account.  
        Let's say we have an access code 'W4t-00k-gTR'. On the right side of the login page, 
        fill out the sign up form and provide the access code"""
        addSubtitle(page, subt)

        controller.InputText(page, "login-newUsername").set("topStudent", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-newPassword").set(
            "user123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-newPassword2").set(
            "user123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputText(page, "login-accessCode").set(
            "4Xt-Bb4-487", timeout=10000
        )
        page.wait_for_timeout(1000)

        subt = """Click the 'Create Account' button to create your account"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "login-createAccount").click(timeout=10000)

        subt = """Let's now login with the new account details"""
        addSubtitle(page, subt)

        # LOGIN TAB
        controller.InputText(page, "login-username").set("topStudent", timeout=10000)
        page.wait_for_timeout(1000)
        controller.InputPassword(page, "login-password").set(
            "user123ABC!", timeout=10000
        )
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "login-login").click(timeout=10000)

        groupCode = dbQuery(
            conn, ('SELECT * FROM "accessCode" WHERE "codeType" = 2 AND "used" IS NULL')
        )

        groupCode = groupCode["code"].iloc[0]

        subt = f"""After successfully logging in, you will be taken to the main page 
        where you can see the topics available for review. If you have been given an 
        additional group access code, you can join this group to see new topics. 
        Let's start by joining a group for a genetics course with the access code 
        '{groupCode}' by clicking the 'Join Group' button"""
        addSubtitle(page, subt)

        # Join a group
        controller.InputActionButton(page, "chat-joinGroup-joinGroup").click(
            timeout=10000
        )
        subt = """Fill in the access code and join the group"""
        addSubtitle(page, subt)
        controller.InputText(page, "chat-joinGroup-accessCode").set(groupCode)
        page.wait_for_timeout(1000)
        controller.InputActionButton(page, "chat-joinGroup-submitJoin").click(
            timeout=10000
        )
        subt = """We can now select any of the topics available in the new group to review
        and start the conversation with SCUIRREL"""
        addSubtitle(page, subt)
        controller.InputSelect(page, "chat-gID").set("2", timeout=10000)
        page.wait_for_timeout(2000)
        # Chat with SCUIRREL
        controller.InputActionButton(page, "chat-startConversation").click(
            timeout=10000
        )
        page.wait_for_timeout(2000)

        # Bring the send button into view3
        page.locator("#chat-send").scroll_into_view_if_needed()

        subt = """SCUIRREL will initiate and guide the conversation as it had been set
        up by instructors to only cover specific concepts related to the topic relevant 
        to your learning"""
        addSubtitle(page, subt)
        page.get_by_text(
            re.compile(r"What do you already know about this?"), exact=False
        ).wait_for(timeout=15000)
        subt = """Simply type in your response and click the 'Send' button to chat"""
        addSubtitle(page, subt)
        controller.InputTextArea(page, "chat-newChat").set(
            "Gregor Mendel was a nineteenth-century monk", timeout=10000
        )
        controller.InputActionButton(page, "chat-send").click(timeout=10000)
        page.get_by_text("Scuirrel is foraging for an answer ...").wait_for(
            timeout=15000
        )
        page.locator('[onclick="chatSelection(this,2)"]').wait_for(
            state="visible", timeout=10000
        )
        subt = """You can continue the conversation and monitor you progress in the bar 
        at the top of the conversation window"""
        addSubtitle(page, subt)

        subt = """If available, you can also take a quiz to test your understanding of 
        the topic. Simply click the 'Take a quiz question' button to start"""
        addSubtitle(page, subt)

        # Take a quiz question
        q = dbQuery(conn, 'SELECT * FROM "question" WHERE "qID" = 1')
        controller.InputActionButton(page, "chat-quiz-quizQuestion").click(
            timeout=10000
        )
        subt = """Read the question and select the correct answer from the options"""
        addSubtitle(page, subt, min_wait_seconds=4)
        controller.InputRadioButtons(page, "chat-quiz-quizOptions").set(
            q["answer"].iloc[0], timeout=10000
        )
        subt = """Then check your answer"""
        addSubtitle(page, subt)
        controller.InputActionButton(page, "chat-quiz-checkAnswer").click(timeout=10000)
        page.get_by_text(q["explanation" + q["answer"].iloc[0]].iloc[0]).wait_for(
            timeout=10000
        )
        subt = """You can close the quiz window when finished"""
        addSubtitle(page, subt)
        page.locator('"Return"').click(timeout=10000)

        subt = """When you have finished, you can simply reload or close the browser 
        to log out."""
        addSubtitle(page, subt)

        page.reload()
        page.wait_for_timeout(1000)

        subt = """This concludes the brief introduction to SCUIRREL.  
        If you have any questions, please reach out to the app administrator or 
        read the documentation"""
        addSubtitle(page, subt)

        scuirrelApp.close()
