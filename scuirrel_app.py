# ******************************************
# ----------- SCUIRREL: MAIN APP -----------
# ******************************************

# Welcome to SCUIRREL:
# Science Concept Understanding with Interactive Research RAG Educational LLM

# See app_shared.py for variables and functions shared across sessions
import shared.shared as shared
import SCUIRREL.scuirrel_shared as scuirrel_shared

# General
import os
from html import escape
import json
import traceback
import bcrypt
from regex import search as re_search

# Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div


# ----------- SHINY APP -----------
# *********************************

if shared.remoteAppDB:
    _ = shared.checkRemoteDB()


conn = shared.appDBConn(scuirrel_shared.postgresUser)
topics = shared.pandasQuery(
    conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
)
conn.close()

# --- RENDERING UI ---
# ********************

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
os.path.join(curDir, "SCUIRREL")

ui.page_opts(fillable=True, window_title="SCUIRREL")
ui.head_content(
    ui.include_css(os.path.join(curDir, "shared", "shared_css", "shared.css")),
    ui.include_css(os.path.join(curDir, "SCUIRREL", "scuirrel_css", "scuirrel.css")),
    ui.include_js(os.path.join(curDir, "SCUIRREL", "scuirrel_js", "scuirrel.js")),
    ui.include_js(os.path.join(curDir, "shared", "shared_js", "shared.js")),
)

# --- CUSTOM JS FUNCTIONS (Python side) ---


# This function allows you to hide/show/disable/enable elements by ID or data-value
# The latter is needed because tabs don't use ID's but data-value
def elementDisplay(id, effect):
    @reactive.effect
    async def _():
        await session.send_custom_message("hideShow", {"id": id, "effect": effect})


# Update a custom, simple progress bar
def progressBar(id, percent):
    @reactive.effect
    async def _():
        await session.send_custom_message("progressBar", {"id": id, "percent": percent})


# --- UI LAYOUT ---
# Add some JS so that pressing enter can send the message too
demoInfo = "If you don't have an account, you can still try the demo" if shared.addDemo else ""

with ui.navset_pill(id="tab"):
    # HOME TAB
    with ui.nav_panel("Home"):
        with ui.layout_columns(col_widths=12):
            with ui.card():
                ui.card_header("Welcome to SCUIRREL")
                HTML(f"""
<p>To access the full SCUIRREL functionality, please login first. If this is the first time you are accessing the 
application, please use the access code provided by your administrator to create an account. {demoInfo}</p>""")
        with ui.layout_columns(col_widths=6):
            with ui.card():
                ui.card_header("Login")
                ui.input_text("lUsername", "Username")
                ui.input_password("lPassword", "Password")
                ui.input_action_button("login", "Login", width="200px")
                ui.input_action_link("showReset", "Reset password", width="250px")
            with ui.card():               
                ui.card_header("Create an account")                
                HTML("""<i>NOTE: This application has been built for research purposes 
                     and has not been extensively tested for security. We recommend
                     you create a unique password for this you are not using anywhere else</i>""")
                ui.input_text("cUsername", "Username")
                ui.input_password("cPassword", "Password")
                ui.input_password("cPassword2", "Repeat password")
                ui.input_text("cAccessCode", "Access code")
                ui.input_action_button("createAccount", "Create", width="200px")
            with ui.panel_conditional("input.showReset > 0"):
                with ui.card():
                    ui.card_header("Reset password")
                    HTML("""<p><i>You will need to request a new access code from your 
                         administrator before resetting your password.</i></p>""")
                    ui.input_text("rUsername", "Username")
                    ui.input_password("rPassword", "New password")
                    ui.input_password("rPassword2", "Repeat new password")
                    ui.input_text("rAccessCode", "Access code")
                    ui.input_action_button("reset", "Reset password", width="250px")
    # MAIN CHAT TAB
    with ui.nav_panel("SCUIRREL"):
        # Render the chat window
        with ui.layout_columns(col_widths=12):
            with ui.card(id="about"):
                HTML("""<p>Hello, I'm Scuirrel (Science Concept Understanding with Interactive Research RAG Educational LLM). 
                     I'm here to help you test your knowledge on specific concepts
                     related to topics relevant to your coursework. I will guide you though these concepts by asking you
                     a series of questions. Note that I will try and make you think for yourself, and not simply
                     provide answers. However, I sometimes go nuts so please talk to your course instructors / teaching 
                     fellows if you have questions or concerns.<br><br><i>NOTE:
                     Though this app is anonymous, I still like to collect data acorns (including chat history) for 
                     research purposes so don't share any personal information and keep to the topic at hand.</i></p>""")
            with ui.card(id="topicSelection"):
                ui.card_header("Pick a topic")
                (ui.input_select("selTopic", None, choices=[], width="600px"),),
                ui.input_action_button("startConversation", "Start conversation", width="200px")
                ui.input_action_button(
                    "quiz",
                    "Give me a quiz question",
                    width="250px",
                    style="display:none;",
                )
            with ui.panel_conditional("input.startConversation > 0"):
                with ui.card(id="chatWindow", height="45vh"):
                    x = (
                        '<div class="progress-bar"><span id="chatProgress" class="progress-bar-fill" style="width: 0%;">Topic Progress</span></div>'
                        + str(
                            ui.input_action_button("chatFeedback", "Provide chat feedback")
                        )
                    )
                    ui.card_header(HTML(x), id="chatHeader")
                    div(id="conversation")

                # User input, send button and wait message
                (
                    div(
                        ui.input_text_area(
                            "newChat", "", value="", width="100%", spellcheck=True, resize=False
                        ),
                        ui.input_action_button("send", "Send"),
                        id="chatIn",
                    ),
                )
                div(
                    HTML(
                        "<p style='color: white'><i>Scuirrel is foraging for an answer ...</i></p>"
                    ),
                    id="waitResp",
                    style="display: none;",
                )

    # USER PROGRESS TAB
    with ui.nav_panel("Profile"):
        with ui.layout_columns(col_widths=12):
            with ui.card():
                ui.card_header("User Progress")
                "TODO"

# Customised feedback button (floating at right side of screen)
ui.input_action_button("feedback", "General Feedback")

# --- REACTIVE VARIABLES & FUNCTIONS ---
uID = reactive.value(1)  # User ID (default is anonymous)
sessionID = reactive.value(0)  # Current Shiny Session
discussionID = reactive.value(0)  # Current conversation
conceptIndex = reactive.value(0)  # Current concept index to discuss
messages = reactive.value(None)  # Raw chat messages
botLog = reactive.value(None)  # Chat sent to the LLM

# Stuff to run once when the session has loaded
if hasattr(session, "_process_ui"):
    # Register the session start in the DB
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    # When loading the app, we start with the anonymous user (uID 1)
    sID = shared.executeQuery(
        cursor,
        'INSERT INTO "session" ("shinyToken", "uID", "appID", "start")'
        "VALUES(?, 1, 0, ?)",
        (session.id, shared.dt()),
        lastRowId="sID",
    )
    conn.commit()
    conn.close()
    sessionID.set(sID)
    # Set the topics
    ui.update_select("selTopic", choices=dict(zip(topics["tID"], topics["topic"])))


# Code to run at the END of the session (i.e. when user disconnects)
_ = session.on_ended(lambda: theEnd())


def theEnd():
    # Isolate so we can use the final values of reactive variables
    with reactive.isolate():
        dID = discussionID.get()
        msg = messages.get()
        sID = sessionID.get()
        # Update the database
        conn = shared.appDBConn(scuirrel_shared.postgresUser)
        cursor = conn.cursor()
        # Log current discussion if one was started
        if dID != 0:
            scuirrel_shared.endDiscussion(cursor, dID, msg)
        # Register the end of the session and if an error occurred, log it
        errMsg = traceback.format_exc().strip()

        if errMsg == "NoneType: None":
            _ = shared.executeQuery(
                cursor,
                'UPDATE "session" SET "end" = ? WHERE "sID" = ?',
                (shared.dt(), sID),
            )
        else:
            _ = shared.executeQuery(
                cursor,
                'UPDATE "session" SET "end" = ?, "error" = ? WHERE "sID" = ?',
                (shared.dt(), errMsg, sID),
            )

        conn.commit()
        conn.close()

# LOGIN AND ACCOUNT CREATION
@reactive.effect
@reactive.event(input.login)
def _():
    username = input.lUsername()
    password = input.lPassword().encode("utf-8")
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    user = shared.pandasQuery(
        conn,
        'SELECT * FROM "user" WHERE "username" = ? AND "username" != "anonymous"',
        (username,),
    )
    
    if user.shape[0] == 1:
        if bcrypt.checkpw(password, user.password.iloc[0]):
            ui.notification_show("Logged in successfully")
            cursor = conn.cursor()
            # For now we only have anonymous users (appID 0 -> SCUIRREL)
            _ = shared.executeQuery(
                cursor,
                'UPDATE "session" SET "uID" = ? WHERE sID = ?',
                (int(user.uID.iloc[0]), sessionID.get())
            )
            conn.commit()
        else:
            ui.notification_show("Incorrect password")
    else:
        ui.notification_show("Invalid username")

    conn.close()
    # Clear the input fields
    ui.update_text_area("lUsername", value="")
    ui.update_text_area("lPassword", value="")

    uID.set(user.uID.iloc[0])

@reactive.effect
@reactive.event(input.createAccount)
def _():
    username = input.cUsername()
    accessCode = input.cAccessCode()

    # Check if the password is strong enough
    if re_search(r"^\w{6,20}$", username) is None:
        ui.notification_show("Username must be between 6 and 20 characters")
        return
    
    # Check if the username already exists
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    user = shared.pandasQuery(
        conn,
        'SELECT * FROM "user" WHERE "username" = ?',
        (username,),
    )

    if user.shape[0] > 0:
        ui.notification_show("Username already exists")
        return

    # Check the password
    pCheck = shared.passCheck(input.cPassword(), input.cPassword2())
    if pCheck:
        ui.notification_show(pCheck)
        return    

    code = shared.accessCodeCheck(conn, accessCode)

    if code is None:
        ui.notification_show("Invalid access code")
        return    

    # Create the user
    hashed = bcrypt.hashpw(input.cPassword().encode("utf-8"), bcrypt.gensalt())
    newuID = shared.executeQuery(
        cursor,
        'INSERT INTO "user" ("username", "password", "adminLevel", "created", "modified")'
        "VALUES(?, ?, ?, ?, ?)",
        (username, hashed, int(code["adminLevel"].iloc[0]), shared.dt(), shared.dt()),
        lastRowId="uID",
    )

    newuID = int(newuID)

    # Update the access code to show it has been used
    _ = shared.executeQuery(
        cursor,
        'UPDATE "accessCode" SET "uID_user" = ?, "used" = ? WHERE "code" = ?',
        (newuID, shared.dt(), accessCode),
    )
    conn.commit()
    conn.close()

    uID.set(newuID)

    # Clear the input fields
    ui.update_text_area("cUsername", value="")
    ui.update_text_area("cPassword", value="")
    ui.update_text_area("cPassword2", value="")
    ui.update_text_area("cAccessCode", value="")

    ui.notification_show("Account created successfully")

@reactive.effect
@reactive.event(input.reset)
def _():
    username = input.rUsername()
    accessCode = input.rAccessCode()

    # Check if the username already exists
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    user = shared.pandasQuery(
        conn,
        'SELECT * FROM "user" WHERE "username" = ?',
        (username,),
    )    

    if user.shape[0] == 0:
        ui.notification_show("This username does not exist")
        return
    
    uID = int(user["uID"].iloc[0])

    # Check the password
    pCheck = shared.passCheck(input.rPassword(), input.rPassword2())
    if pCheck:
        ui.notification_show(pCheck)
        return
    
    # Check the access code
    code = shared.accessCodeCheck(conn, accessCode)

    if code is None:
        ui.notification_show("Invalid access code")
        return
    
    # Update the password
    hashed = bcrypt.hashpw(input.rPassword().encode("utf-8"), bcrypt.gensalt())
    _ = shared.executeQuery(
        cursor,
        'UPDATE "user" SET "password" = ?, "modified" = ? WHERE "uID" = ?',
        (hashed, shared.dt(), uID),
    )

     # Update the access code to show it has been used
    _ = shared.executeQuery(
        cursor,
        'UPDATE "accessCode" SET "uID_user" = ?, "used" = ? WHERE "code" = ?',
        (uID, shared.dt(), accessCode),
    )
    conn.commit()
    conn.close()

    # Clear the input fields
    ui.update_text_area("rUsername", value="")
    ui.update_text_area("rPassword", value="")
    ui.update_text_area("rPassword2", value="")
    ui.update_text_area("rAccessCode", value="")
    
    ui.notification_show("Password reset successfully, please login again")
    

@reactive.effect
@reactive.event(input.startConversation)
def _():
    tID = int(topics[topics["tID"] == int(input.selTopic())].iloc[0]["tID"])
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    # Save the logs for the previous discussion (if any)
    if messages.get():
        scuirrel_shared.endDiscussion(cursor, discussionID.get(), messages.get())
        elementDisplay("chatIn", "s")  # In case hidden if previous finished

    # Register the start of the  new topic discussion
    dID = shared.executeQuery(
        cursor,
        'INSERT INTO "discussion" ("tID", "sID", "start")' "VALUES(?, ?, ?)",
        (tID, sessionID.get(), shared.dt()),
        lastRowId="dID",
    )
    discussionID.set(int(dID))
    # Only show the quiz button if there are any questions
    _ = shared.executeQuery(
        cursor,
        'SELECT "qID" FROM "question" WHERE "tID" = ? AND "archived" = 0',
        (tID,),
    )
    if cursor.fetchone():
        elementDisplay("quiz", "s")
    else:
        elementDisplay("quiz", "h")

    conn.commit()
    conn.close()
    # The first message is not generated by the bot
    firstWelcome = (
        'Hello, I\'m here to help you get a basic understanding of the following topic: '
        f'{topics.iloc[0]["topic"]}. What do you already know about this?'
    )

    msg = scuirrel_shared.Conversation()
    msg.add_message(
        isBot=1,
        cID=int(concepts().iloc[conceptIndex.get()]["cID"]),
        content=firstWelcome,
    )
    messages.set(msg)
    ui.insert_ui(
        HTML(f"""<div id='welcome' class='botChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'>
                            <p>Hello, I'm here to help you get a basic understanding of 
                            the following topic: <b>{topics.iloc[0]["topic"]}</b>. 
                            What do you already know about this?</p></div>"""),
        "#conversation",
    )
    botLog.set(f"---- PREVIOUS CONVERSATION ----\n--- MENTOR:\n{firstWelcome}")
    return tID


# Get the concepts related to the topic
@reactive.calc
def concepts():
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    concepts = shared.pandasQuery(
        conn,
        f'SELECT * FROM "concept" WHERE "tID" = {int(input.selTopic())} AND "archived" = 0',
    )
    conn.close()
    return concepts


# When the send button is clicked...
@reactive.effect
@reactive.event(input.send)
def _():
    newChat = input.newChat()
    # Ignore empty chat
    if (newChat == "") | (newChat.isspace()):
        return

    # Prevent new chat whilst LLM is working and show waiting message
    elementDisplay("waitResp", "s")
    elementDisplay("chatIn", "h")
    # Add the user message
    msg = messages.get()
    msg.add_message(
        isBot=0, cID=int(concepts().iloc[conceptIndex.get()]["cID"]), content=newChat
    )
    messages.set(msg)
    # Generate chat logs
    conversation = botLog.get() + "\n---- NEW RESPONSE FROM STUDENT ----\n" + newChat
    ui.insert_ui(
        HTML(
            f"<div class='userChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'><p>{escape(newChat)}</p></div>"
        ),
        "#conversation",
    )
    botLog.set(botLog.get() + f"\n--- STUDENT:\n{newChat}")
    topic = topics[topics["tID"] == int(input.selTopic())].iloc[0]["topic"]
    # Send the message to the LLM for processing
    botResponse(topic, concepts(), conceptIndex.get(), conversation)


# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def botResponse(topic, concepts, cIndex, conversation):
    # Check the student's progress on the current concept based on the last reply (other engine)
    engine = scuirrel_shared.progressCheckEngine(conversation, topic, concepts, cIndex)
    eval = json.loads(str(engine.query(conversation)))
    # See if the LLM thinks we can move on to the next concept or or not
    if int(eval["score"]) > 2:
        cIndex += 1
    # Check if all concepts have been covered successfully
    if cIndex >= concepts.shape[0]:
        resp = f"Well done! It seems you have demonstrated understanding of everything we wanted you to know about: {topic}"
    else:
        engine = scuirrel_shared.chatEngine(topic, concepts, cIndex, eval)
        resp = str(engine.query(conversation))

    return {"resp": resp, "eval": eval}


# Processing LLM responses
@reactive.effect
def _():
    result = botResponse.result()
    eval = result["eval"]  # Evaluation of last response and progress
    resp = result["resp"]  # New response to student

    with reactive.isolate():
        # Check the topic progress and move on to next concept if current one scored well
        i = conceptIndex.get()
        finished = False
        if int(eval["score"]) > 2:
            if i < (concepts().shape[0] - 1):
                i = i + 1
            else:
                finished = True

            progressBar("chatProgress", int(100 * i / concepts().shape[0]))

        # Add the evaluation of the student's last reply to the log
        msg = messages.get()
        msg.addEval(eval["score"], eval["comment"])
        msg.add_message(isBot=1, cID=int(concepts().iloc[i]["cID"]), content=resp)
        messages.set(msg)
        conceptIndex.set(i)
        ui.insert_ui(
            HTML(
                f"<div class='botChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'><p>{escape(resp)}</p></div>"
            ),
            "#conversation",
        )
        botLog.set(botLog.get() + "\n--- MENTOR:\n" + resp)

        # Now the LLM has finished the user can send a new response
        elementDisplay("waitResp", "h")
        ui.update_text_area("newChat", value="")
        # If conversation is over don't show new message box
        if not finished:
            elementDisplay("chatIn", "s")
        else:
            ui.insert_ui(HTML("<hr>"), "#conversation")


# -- QUIZ

quizQuestion = reactive.value()


# Clicking the quiz button shows a modal
@reactive.effect
@reactive.event(input.quiz)
def _():
    # Get a random question on the topic from the DB
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    q = shared.pandasQuery(
        conn,
        f'SELECT * FROM "question" WHERE "tID" = {int(input.selTopic())} AND "archived" = 0',
    )
    conn.close()
    q = q.sample(1).iloc[0].to_dict()
    q["start"] = shared.dt()

    # UI for the quiz question popup (saved as a variable)
    @render.express
    def quizUI():
        HTML(f'<b>{q["question"]}</b><br><br>')
        ui.input_radio_buttons(
            "quizOptions",
            None,
            width="100%",
            choices={
                "X": HTML("<i>Select an option below:</i>"),
                "A": q["optionA"],
                "B": q["optionB"],
                "C": q["optionC"],
                "D": q["optionD"],
            },
        )
        ui.input_action_button("checkAnswer", "Check answer")

        @render.ui
        def _():
            return checkAnswer()

    # The modal
    m = ui.modal(
        quizUI,
        title="Test your knowledge",
        easy_close=False,
        size="l",
        footer=ui.TagList(ui.input_action_button("qClose", "Return")),
    )
    ui.modal_show(m)
    quizQuestion.set(q)


# Clicking the check answer button will show result + explanation
@reactive.calc
@reactive.event(input.checkAnswer)
def checkAnswer():
    # User must select a valid option
    if input.quizOptions() == "X":
        return HTML("<hr><i>Select an option first!</i>")

    # Check Answer
    q = quizQuestion.get()
    correct = input.quizOptions() == q["answer"]
    q["response"] = input.quizOptions()
    q["correct"] = correct + 0  # Convert to integer
    # Add the response to the database

    # Hide the answer button (don't allow for multiple guessing)
    if not scuirrel_shared.allowMultiGuess:
        elementDisplay("checkAnswer", "h")

    # Add the timestamp the answer was checked
    q["check"] = shared.dt()
    quizQuestion.set(q)

    return HTML(
        f'<hr><h3>{"Correct!" if correct else "Incorrect..."}</h3>'
        f'{q["explanation" + input.quizOptions()]}'
    )


@reactive.effect
@reactive.event(input.qClose)
def _():
    q = quizQuestion.get()

    # Handle the case where user returns before checking an answer
    if "check" not in q:
        q["check"] = None
        q["response"] = None
        q["correct"] = None

    # Add the response to the DB
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'INSERT INTO "response" ("sID", "qID", "response", "correct", "start", "check", "end")'
        "VALUES(?, ?, ?, ?, ?, ?, ?)",
        (
            sessionID(),
            q["qID"],
            q["response"],
            q["correct"],
            q["start"],
            q["check"],
            shared.dt(),
        ),
    )
    conn.commit()
    conn.close()
    ui.modal_remove()


# When the chat feedback button is clicked
@reactive.effect
@reactive.event(input.chatFeedback)
def _():
    sel = json.loads(input.selectedMsg())  # Custom JS input selectedMsg
    if sel == []:
        # With no messages selected
        ui.notification_show(
            "Please select all chat messages relevant to your feedback report"
        )
    else:
        # Ask for more details
        m = ui.modal(
            ui.input_radio_buttons(
                "feedbackChatCode",
                " Pick a category",
                choices={
                    1: "Incorrect",
                    2: "Inappropriate",
                    3: "Not helpful",
                    4: "Not able to proceed",
                    5: "Other",
                },
                inline=True,
            ),
            ui.input_text_area(
                "feedbackChatDetails", "Please provide more details", width="100%"
            ),
            title="Please provide some more information",
            size="l",
            footer=[
                ui.input_action_button("feedbackChatSubmit", "Submit"),
                ui.modal_button("Cancel"),
            ],
        )
        ui.modal_show(m)


# Insert the issue into the DB
@reactive.effect
@reactive.event(input.feedbackChatSubmit)
def _():
    # Because multiple issues can be submitted for a single conversation, we have to commit to the
    # DB immediately or it would become harder to keep track of TODO
    # This means we add a temp mID which will be updated in the end
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    fcID = shared.executeQuery(
        cursor,
        'INSERT INTO "feedback_chat"("dID","code","created","details") '
        "VALUES(?,?,?,?)",
        (
            discussionID.get(),
            int(input.feedbackChatCode()),
            shared.dt(),
            input.feedbackChatDetails(),
        ),
        lastRowId="fcID",
    )
    tempID = json.loads(input.selectedMsg())
    tempID.sort()
    _ = shared.executeQuery(
        cursor,
        f'INSERT INTO "feedback_chat_msg"("fcID","mID") VALUES({fcID},?)',
        [(x,) for x in tempID],
    )
    conn.commit()
    conn.close()
    # Remove modal and show confirmation
    ui.modal_remove()
    ui.notification_show("Feedback successfully submitted!", duration=3)


# General feedback button click
@reactive.effect
@reactive.event(input.feedback)
def _():
    # Show a modal asking for more details
    m = ui.modal(
        ui.input_radio_buttons(
            "feedbackCode",
            "Pick a feedback category",
            choices={
                1: "User experience (overall functionality, intuitiveness)",
                2: "Content (descriptions, labels, messages, ...)",
                3: "Design (layout, accessibility)",
                4: "Performance (speed, crashes, unexpected behavior)",
                5: "Suggestion for improvement / new feature",
                6: "Other",
            },
            inline=False,
            width="100%",
        ),
        ui.tags.p(
            "Please note that if you have chat specific feedback to use the dedicated button instead!",
            style="color:red;",
        ),
        ui.input_text_area(
            "feedbackDetails", "Please provide more details", width="100%"
        ),
        ui.input_text(
            "feedbackContact", "(optional) Contact email address", width="100%"
        ),
        ui.tags.i(
            "Please note that providing your email address will link all session details "
            "to this feedback report (no longer anonymous)"
        ),
        title="Please provide some more information",
        size="l",
        footer=[
            ui.input_action_button("feedbackSubmit", "Submit"),
            ui.modal_button("Cancel"),
        ],
    )
    ui.modal_show(m)


# Register feedback in the appDB
@reactive.effect
@reactive.event(input.feedbackSubmit)
def _():
    conn = shared.appDBConn(scuirrel_shared.postgresUser)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'INSERT INTO "feedback_general"("sID","code","created","email","details") VALUES(?,?,?,?,?)',
        (
            sessionID(),
            input.feedbackCode(),
            shared.dt(),
            input.feedbackContact(),
            input.feedbackDetails(),
        ),
    )
    conn.commit()
    conn.close()
    ui.modal_remove()
    ui.notification_show("Thank you for sharing feedback", duration=3)
