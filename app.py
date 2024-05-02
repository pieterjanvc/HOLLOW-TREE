# ******************************************
# ----------- SCUIRREL + ACCORNS -----------
# ******************************************

# Welcome to SCUIRREL & ACCORNS:
# Science Concept Understanding with Interactive Research RAG Educational LLM
# Admin Control Center Overseeing RAG Needed for SCUIRREL

# See app_shared.py for variables and functions shared across sessions
import app_shared as shared

# --- IMPORTS ---

# General
import sqlite3
from html import escape
import pandas as pd
import json
import duckdb
import warnings

# -- Llamaindex
from llama_index.core import VectorStoreIndex, ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.vector_stores.duckdb import DuckDBVectorStore

# Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div

# The following is needed to prevent async issues when inserting new data in vector DB
# https://github.com/run-llama/llama_index/issues/9978
import nest_asyncio

nest_asyncio.apply()

# ----------- SHINY APP -----------
# *********************************

# --- NON-REACTIVE VARIABLES ---
# Non-reactive session variables are loaded before a session starts
uID = 1  # if registered users update later

# conn = sqlite3.connect(shared.appDB)
# topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
# conn.close()

# --- RENDERING UI ---
# ********************

ui.page_opts(fillable=True)
ui.head_content(
    ui.include_css("www/styles.css"), ui.include_js("www/custom.js", method="inline")
)

# --- UI COMPONENTS ---
uiUploadFile = div(
    ui.input_file(
        "newFile",
        "Pick a file",
        width="100%",
        accept=[
            ".csv",
            ".pdf",
            ".docx",
            ".txt",
            ".md",
            ".epub",
            ".ipynb",
            ".ppt",
            ".pptx",
        ],
    ),
    id="uiUploadFile",
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

with ui.navset_pill(id="tab"):
    # SCUIRREL - MAIN CHAT
    with ui.nav_panel("WELCOME"):
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
    # SCUIRREL - MAIN CHAT
    with ui.nav_panel("SCUIRREL"):
        # Render the chat window
        with ui.layout_columns(col_widths=12):
            with ui.card(id="topicSelection"):
                ui.card_header("Pick a topic")
                (ui.input_select("selTopic", None, choices=[], width="600px"),)
                ui.input_action_button(
                    "quiz",
                    "Give me a quiz question",
                    width="250px",
                    style="display:none;",
                )

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

    # SCUIRREL - USER PROGRESS TAB
    with ui.nav_panel("Profile"):
        with ui.layout_columns(col_widths=12):
            with ui.card():
                ui.card_header("User Progress")
                "TODO"

    # ACCORNS - VECTOR DATABASE
    with ui.nav_panel("Vector Database", value="vTab"):
        with ui.card(id="blankDBMsg", style="display: none;"):
            HTML(
                "<i>Welcome to ACCORNS, the Admin Control Center Overseeing RAG Needed for SCUIRREL!<br>"
                "In order to get started, please add at least one file to the vector database</i>"
            )
        # Tables of the files that are in the DB
        with ui.card():
            ui.card_header("Vector database files")

            @render.data_frame
            def filesTable():
                return render.DataTable(
                    files.get()[["title", "fileName"]],
                    width="100%",
                    selection_mode="row",
                )

        with ui.card(id="fileInfoCard"):
            ui.card_header("File info")

            @render.ui
            def fileDetailsUI():
                return fileInfo()

        # Option to add bew files
        with ui.card():
            ui.card_header("Upload a new file")
            uiUploadFile

    # ACCORNS - TOPICS
    with ui.nav_panel("Topics", value="tTab"):
        with ui.layout_columns(col_widths=12):
            # Select, add or archive a topic
            with ui.card():
                ui.card_header("Topic")
                ui.input_select("tID", "Pick a topic", choices=[], width="400px")
                div(
                    ui.input_action_button("tAdd", "Add new", width="180px"),
                    ui.input_action_button("tEdit", "Edit selected", width="180px"),
                    ui.input_action_button(
                        "tArchive", "Archive selected", width="180px"
                    ),
                )
            # Table of concepts per topic with option to add, edit or archive
            with ui.card():
                ui.card_header("Concepts related to the topic")

                @render.data_frame
                def conceptsTable():
                    return render.DataTable(
                        conceptsList.get()[["concept"]],
                        width="100%",
                        selection_mode="row",
                    )

                div(
                    ui.input_action_button("cAdd", "Add new", width="180px"),
                    ui.input_action_button("cEdit", "Edit selected", width="180px"),
                    ui.input_action_button(
                        "cArchive", "Archive selected", width="180px"
                    ),
                    style="display:inline",
                )
                HTML(
                    "<i>Concepts are specific facts or pieces of information you want SCUIRREL to check with your students. "
                    "You can be very brief, as all context will be retrieved from the database of documents. "
                    "Don't be too broad, split into multiple topics if needed. "
                    "SCUIRREL will walk through the concepts in order, so kep that in mind</i>"
                )
    # ACCORNS - QUIZ QUESTIONS
    with ui.nav_panel("Quiz Questions", value="qTab"):
        # Select a topic and a question with options to add or archive
        with ui.card():
            ui.card_header("Questions by Topic")
            # Dropdown of topics and questions per topic
            ui.input_select(
                "qtID", "Pick a topic", choices={1: "Central Dogma"}, width="400px"
            )
            ui.input_select("qID", "Question", choices=[], width="400px")
            # Buttons to add or archive questions and message when busy generating
            div(
                ui.input_action_button("qGenerate", "Generate new", width="180px"),
                ui.input_action_button("qArchive", "Archive selected", width="180px"),
                id="qBtnSet",
                style="display:inline",
            )
            div(
                HTML("<i>Generating a new question...</i>"),
                id="qBusyMsg",
                style="display: none;",
            )

        # Only show this panel if there is at least one question
        with ui.panel_conditional("input.qID"):
            with ui.card():
                ui.card_header("Review question")

                # Show a preview of the question
                @render.ui
                def quizQuestionPreview():
                    return HTML(
                        f"<b>{input.rqQuestion()}</b><ol type='A'><li>{input.rqOA()}</li>"
                        f"<li>{input.rqOB()}</li><li>{input.rqOC()}</li>"
                        f"<li>{input.rqOD()}</li></ol><i>Correct answer: {input.rqCorrect()}</i><hr>"
                    )

                # Save updates
                div(
                    ui.input_action_button("qSaveChanges", "Save Changes"),
                    ui.input_action_button("qDiscardChanges", "Discard Changes"),
                )
                # Fields to edit any part of the question
                ui.input_text_area(
                    "rqQuestion", "Question", width="100%", autoresize=True
                )
                ui.input_radio_buttons(
                    "rqCorrect",
                    "Correct answer",
                    choices=["A", "B", "C", "D"],
                    inline=True,
                )
                ui.input_text("rqOA", "Option A", width="100%")
                ui.input_text_area(
                    "rqOAexpl", "Explanation A", width="100%", autoresize=True
                )
                ui.input_text("rqOB", "Option B", width="100%")
                ui.input_text_area(
                    "rqOBexpl", "Explanation B", width="100%", autoresize=True
                )
                ui.input_text("rqOC", "Option C", width="100%")
                ui.input_text_area(
                    "rqOCexpl", "Explanation C", width="100%", autoresize=True
                )
                ui.input_text("rqOD", "Option D", width="100%")
                ui.input_text_area(
                    "rqODexpl", "Explanation D", width="100%", autoresize=True
                )
# Customised feedback button (floating at right side of screen)
ui.input_action_button("feedback", "General Feedback")

# --- REACTIVE VARIABLES + START / END ACTION ---

conn = duckdb.connect(shared.vectorDB)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    files = pd.read_sql_query("SELECT * FROM file", conn)
conn.close()

# Hide the topic and question tab if the vector database is empty and show welcome message
if files.shape[0] == 0:
    elementDisplay("tTab", "h")
    elementDisplay("qTab", "h")
    elementDisplay("blankDBMsg", "s")

if files.shape[0] == 0:
    index = None
else:
    index = VectorStoreIndex.from_vector_store(
        DuckDBVectorStore.from_local(shared.vectorDB)
    )

# Some of these could become reactive calls in future but for now we use
# reactive var until issue with reactive.calls is resolved
# https://github.com/posit-dev/py-shiny/issues/1271
sessionID = reactive.value(0)  # Current Shiny Session
discussionID = reactive.value(0)  # Current conversation
conceptIndex = reactive.value(0)  # Current concept index to discuss
messages = reactive.value(None)  # Raw chat messages
botLog = reactive.value(None)  # Chat sent to the LLM
index = reactive.value(index)
topics = reactive.value(None)
conceptsList = reactive.value(None)
files = reactive.value(files)

# Stuff to run once when the session has loaded
if hasattr(session, "_process_ui"):
    # Register the session start in the DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    # For now we only have anonymous users (appID 0 -> SCUIRREL)
    _ = cursor.execute(
        "INSERT INTO session (shinyToken, uID, appID, start)"
        f'VALUES("{session.id}", {uID}, 0, "{shared.dt()}")'
    )
    sID = int(cursor.lastrowid)
    newTopics = pd.read_sql_query(
        "SELECT tID, topic FROM topic WHERE archived = 0", conn
    )
    conn.commit()
    conn.close()
    sessionID.set(sID)
    # Set the topics in SCUIRREL
    ui.update_select(
        "selTopic", choices=dict(zip(newTopics["tID"], newTopics["topic"]))
    )
    # Set the topics in ACCORNS
    ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])))
    topics.set(newTopics)


# Code to run at the END of the session (i.e. when user disconnects)
_ = session.on_ended(lambda: theEnd())


def theEnd():
    # Isolate so we can use the final values of reactive variables
    with reactive.isolate():
        dID = discussionID.get()
        msg = messages.get()
        sID = sessionID.get()
        # AUpdate the database
        conn = sqlite3.connect(shared.appDB)
        cursor = conn.cursor()
        # Log current discussion
        shared.endDiscussion(cursor, dID, msg)
        # Register the end of the session
        _ = cursor.execute(
            f'UPDATE session SET end = "{shared.dt()}" WHERE sID = {sID}'
        )
        conn.commit()
        conn.close()


### ---- SCUIRREL APP LOGIC ----
### ----------------------------


@reactive.effect
@reactive.event(input.selTopic)
def _():
    tID = topics.get()[topics.get()["tID"] == int(input.selTopic())].iloc[0]["tID"]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    # Save the logs for the previous discussion (if any)
    if messages.get():
        shared.endDiscussion(cursor, discussionID.get(), messages.get())
        elementDisplay("chatIn", "s")  # In case hidden if previous finished

    # Register the start of the  new topic discussion
    _ = cursor.execute(
        "INSERT INTO discussion (tID, sID, start)"
        f'VALUES({tID}, {sessionID.get()}, "{shared.dt()}")'
    )
    discussionID.set(int(cursor.lastrowid))
    # Only show the quiz button if there are any questions
    if cursor.execute(
        f"SELECT qID FROM question where tID = {tID} AND archived = 0"
    ).fetchone():
        elementDisplay("quiz", "s")
    else:
        elementDisplay("quiz", "h")

    conn.commit()
    conn.close()
    # The first message is not generated by the bot
    firstWelcome = (
        'Hello, I\'m here to help you get a basic understanding of the following topic: '
        f'{topics.get()[topics.get()["tID"] == tID].iloc[0]["topic"]}. What do you already know about this?'
    )
    msg = shared.Conversation()
    msg.add_message(
        isBot=1,
        cID=int(concepts().iloc[0]["cID"]),
        content=firstWelcome,
    )
    messages.set(msg)
    ui.insert_ui(
        HTML(f"""<div id='welcome' class='botChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'>
                            <p>Hello, I'm here to help you get a basic understanding of 
                            the following topic: <b>{topics.get()[topics.get()["tID"] == tID].iloc[0]["topic"]}</b>. 
                            What do you already know about this?</p></div>"""),
        "#conversation",
    )
    botLog.set(f"---- PREVIOUS CONVERSATION ----\n--- MENTOR:\n{firstWelcome}")
    conceptIndex.set(0)
    return tID


# Get the concepts related to the topic
@reactive.calc
def concepts():
    conn = sqlite3.connect(shared.appDB)
    concepts = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {int(input.selTopic())} AND archived = 0",
        conn,
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
    topic = topics.get()[topics.get()["tID"] == int(input.selTopic())].iloc[0]["topic"]
    # Send the message to the LLM for processing
    chatBotResponse(topic, concepts(), conceptIndex.get(), conversation)


# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def chatBotResponse(topic, concepts, cIndex, conversation):
    # Check the student's progress on the current concept based on the last reply (other engine)
    engine = shared.progressCheckEngine(conversation, topic, concepts, cIndex)
    eval = json.loads(str(engine.query(conversation)))
    # See if the LLM thinks we can move on to the next concept or or not
    if int(eval["score"]) > 2:
        cIndex += 1
    # Check if all concepts have been covered successfully
    if cIndex >= concepts.shape[0]:
        resp = f"Well done! It seems you have demonstrated understanding of everything we wanted you to know about: {topic}"
    else:
        engine = shared.chatEngine(topic, concepts, cIndex, eval)
        resp = str(engine.query(conversation))

    return {"resp": resp, "eval": eval}


# Processing LLM responses
@reactive.effect
def _():
    result = chatBotResponse.result()
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
    conn = sqlite3.connect(shared.appDB)
    q = pd.read_sql_query(
        f"SELECT * FROM question WHERE tID = {int(input.selTopic())} AND archived = 0",
        conn,
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
    if not shared.allowMultiGuess:
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
        q["check"] = "NULL"
        q["response"] = "NULL"
        q["correct"] = "NULL"
    else:
        q["check"] = f'"{q["check"]}"'
        q["response"] = f'"{q["response"]}"'

    # Add the response to the DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        'INSERT INTO response (sID, qID, "response", "correct", "start", "check", "end") '
        f'VALUES({sessionID()}, {q["qID"]}, {q["response"]}, {q["correct"]},'
        f'"{q["start"]}",{q["check"]},"{shared.dt()}")'
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
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "INSERT INTO feedback_chat(dID,code,created,details) VALUES(?,?,?,?)",
        (
            discussionID.get(),
            int(input.feedbackChatCode()),
            shared.dt(),
            input.feedbackChatDetails(),
        ),
    )
    fcID = cursor.lastrowid
    tempID = json.loads(input.selectedMsg())
    tempID.sort()
    _ = cursor.executemany(
        f"INSERT INTO feedback_chat_msg(fcID,mID) VALUES({fcID},?)",
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
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "INSERT INTO feedback_general(sID,code,created,email,details) VALUES(?,?,?,?,?)",
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


### ---- ACCORNS APP LOGIC ----
### ----------------------------

# ---- TOPICS ----


# --- Add a new topic
@reactive.effect
@reactive.event(input.tAdd)
def addTopic_modal():
    m = ui.modal(
        ui.tags.p(
            HTML(
                "<i>Keep the topic name short.<br>"
                "Make sure the topic can be covered by ~ 4-8 concepts, otherwise split it up."
                "The AI might struggle with broad topics that cover many concepts</i>"
            )
        ),
        ui.input_text("ntTopic", "New topic:", width="100%"),
        ui.input_text("ntDescr", "Description (optional):", width="100%"),
        title="Add a topic",
        easy_close=True,
        size="l",
        footer=ui.TagList(
            ui.input_action_button("ntAdd", "Add"), ui.modal_button("Cancel")
        ),
    )
    ui.modal_show(m)


@reactive.effect
@reactive.event(input.ntAdd)
def addNewTopic():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.ntTopic()):
        ui.remove_ui("#noGoodTopic")
        ui.insert_ui(
            HTML(
                "<div id=noGoodTopic style='color: red'>New topic must be at least 6 characters</div>"
            ),
            "#ntDescr",
            "afterEnd",
        )
        return

    # Add new topic to DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "INSERT INTO topic(topic, created, modified, description)"
        f'VALUES("{input.ntTopic()}", "{shared.dt()}", "{shared.dt()}", "{input.ntDescr()}")'
    )
    tID = cursor.lastrowid
    newTopics = pd.read_sql_query(
        "SELECT tID, topic FROM topic WHERE archived = 0", conn
    )
    conn.commit()
    conn.close()

    # Update the topics select input
    ui.update_select(
        "tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])), selected=tID
    )
    topics.set(newTopics)
    ui.modal_remove()


# --- Edit an existing topic
@reactive.effect
@reactive.event(input.tEdit)
def _():
    if input.tID() is not None:
        topic = topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["topic"]
        m = ui.modal(
            ui.tags.p(
                HTML(
                    "<i>Make sure to only make small edits that do not change the topic. "
                    "Otherwise add or delete instead</i>"
                )
            ),
            ui.input_text("etInput", "Updated topic:", width="100%", value=topic),
            title="Edit an existing topic",
            easy_close=True,
            size="l",
            footer=ui.TagList(
                ui.input_action_button("etEdit", "Update"), ui.modal_button("Cancel")
            ),
        )
        ui.modal_show(m)


@reactive.effect
@reactive.event(input.etEdit)
def _():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.etInput()):
        ui.remove_ui("#noGoodTopic")
        ui.insert_ui(
            HTML(
                "<div id=noGoodTopic style='color: red'>A topic must be at least 6 characters</div>"
            ),
            "#etInput",
            "afterEnd",
        )
        return

    if (
        topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["topic"]
        == input.etInput()
    ):
        ui.remove_ui("#noGoodTopic")
        ui.insert_ui(
            HTML("<div id=noGoodTopic style='color: red'>No change detected</div>"),
            "#etInput",
            "afterEnd",
        )
        return

    # Update the DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    # Backup old value
    shared.backupQuery(cursor, sessionID.get(), "topic", input.tID(), "topic", False)
    # Update to new
    _ = cursor.execute(
        f'UPDATE topic SET topic = "{input.etInput()}", '
        f'modified = "{shared.dt()}" WHERE tID = {input.tID()}'
    )
    newTopics = pd.read_sql_query(
        "SELECT tID, topic FROM topic WHERE archived = 0", conn
    )
    conn.commit()
    conn.close()

    # Update the topics select input
    ui.update_select(
        "tID",
        choices=dict(zip(newTopics["tID"], newTopics["topic"])),
        selected=input.tID(),
    )
    topics.set(newTopics)
    ui.modal_remove()


# --- Archive a topic
@reactive.effect
@reactive.event(input.tArchive)
def _():
    if input.tID() is None:
        return

    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "UPDATE topic SET archived = 1, "
        f'modified = "{shared.dt()}" WHERE tID = {input.tID()}'
    )
    newTopics = pd.read_sql_query(
        "SELECT tID, topic FROM topic WHERE archived = 0", conn
    )

    # Empty the concept table is last topic was removed
    if topics.shape[0] == 0:
        newConceptList = pd.read_sql_query("SELECT * FROM concept WHERE tID = 0", conn)
        conceptsList.set(newConceptList)

    conn.commit()
    conn.close()

    # Update the topics select input
    ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])))
    topics.set(newTopics)


# ---- CONCEPTS ----


# --- Add a new concepts
@reactive.effect
@reactive.event(input.cAdd)
def _():
    m = ui.modal(
        ui.tags.p(
            HTML(
                "<i>Concepts are single facts that a student should understand<br>"
                "There is no need to provide context as this will come from the database</i>"
            )
        ),
        ui.input_text("ncInput", "New concept:", width="100%"),
        title="Add a new concept to the topic",
        easy_close=True,
        size="l",
        footer=ui.TagList(
            ui.input_action_button("ncAdd", "Add"), ui.modal_button("Cancel")
        ),
    )
    ui.modal_show(m)


@reactive.effect
@reactive.event(input.ncAdd)
def _():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.ncInput()):
        ui.remove_ui("#noGoodConcept")
        ui.insert_ui(
            HTML(
                "<div id=noGoodConcept style='color: red'>New concept must be at least 6 characters</div>"
            ),
            "#ncInput",
            "afterEnd",
        )
        return

    # Add new topic to DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "INSERT INTO concept(tID, concept, created, modified)"
        f'VALUES({input.tID()}, "{input.ncInput()}", "{shared.dt()}", "{shared.dt()}")'
    )
    newConceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn
    )
    conn.commit()
    conn.close()
    # Update concept table
    conceptsList.set(newConceptList)
    ui.modal_remove()


# --- Edit an existing concepts
@reactive.effect
@reactive.event(input.cEdit)
def _():
    if not conceptsTable.data_view(selected=True).empty:
        concept = conceptsTable.data_view(selected=True).iloc[0]["concept"]
        m = ui.modal(
            ui.tags.p(
                HTML(
                    "<i>Make sure to only make edits that do not change the concept. "
                    "Otherwise add or delete instead</i>"
                )
            ),
            ui.input_text("ecInput", "Edit concept:", width="100%", value=concept),
            title="Edit and existing topic",
            easy_close=True,
            size="l",
            footer=ui.TagList(
                ui.input_action_button("ncEdit", "Update"), ui.modal_button("Cancel")
            ),
        )
        ui.modal_show(m)


@reactive.effect
@reactive.event(input.ncEdit)
def _():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.ecInput()):
        ui.remove_ui("#noGoodConcept")
        ui.insert_ui(
            HTML(
                "<div id=noGoodConcept style='color: red'>A concept must be at least 6 characters</div>"
            ),
            "#ecInput",
            "afterEnd",
        )
        return
    concept = conceptsTable.data_view(selected=True).iloc[0]["concept"]
    if concept == input.ecInput():
        ui.remove_ui("#noGoodConcept")
        ui.insert_ui(
            HTML("<div id=noGoodConcept style='color: red'>No change detected</div>"),
            "#ecInput",
            "afterEnd",
        )
        return

    # Update the DB
    cID = conceptsList.get().iloc[conceptsTable.data_view(selected=True).index[0]][
        "cID"
    ]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    # Backup old value
    shared.backupQuery(cursor, sessionID.get(), "concept", cID, "concept", False)
    # Update to new
    _ = cursor.execute(
        f'UPDATE concept SET concept = "{input.ecInput()}", '
        f'modified = "{shared.dt()}" WHERE cID = {cID}'
    )
    newConceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn
    )
    conn.commit()
    conn.close()
    # Update concept table
    conceptsList.set(newConceptList)
    ui.modal_remove()


# --- delete a concept (archive)
@reactive.effect
@reactive.event(input.cArchive)
def _():
    if conceptsTable.data_view(selected=True).empty:
        return

    cID = conceptsList.get().iloc[conceptsTable.data_view(selected=True).index[0]][
        "cID"
    ]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "UPDATE concept SET archived = 1, "
        f'modified = "{shared.dt()}" WHERE cID = {cID}'
    )
    newConceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn
    )
    conn.commit()
    conn.close()

    conceptsList.set(newConceptList)


@reactive.effect
@reactive.event(input.tID)
def _():
    tID = input.tID() if input.tID() else 0
    conn = sqlite3.connect(shared.appDB)
    newConceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {tID} AND archived = 0", conn
    )
    conn.close()
    conceptsList.set(newConceptList)


# ---- VECTOR DATABASE ----


@reactive.effect
@reactive.event(input.newFile, ignore_init=True)
def _():
    # Move the file to the uploadedFiles folder
    updateVectorDB(
        input.newFile()[0]["datapath"],
        shared.vectorDB,
        shared.storageFolder,
        input.newFile()[0]["name"],
    )
    ui.insert_ui(
        HTML(
            f'<div id=processFile><i>Processing {input.newFile()[0]["name"]}</i></div>'
        ),
        "#uiUploadFile",
        "afterEnd",
    )
    ui.remove_ui("#uiUploadFile")


@reactive.extended_task
async def updateVectorDB(newFile, vectorDB, storageFolder, newFileName):
    print("Start adding file...")
    return shared.addFileToDB(newFile, vectorDB, storageFolder, newFileName)


@reactive.effect
def _():
    insertionResult = updateVectorDB.result()[0]
    msg = (
        "File succesfully added to the vector database"
        if insertionResult == 0
        else "A file with the same name already exists. Skipping upload"
    )
    ui.modal_show(ui.modal(msg, title="Success" if insertionResult == 0 else "Issue"))
    with warnings.catch_warnings():
        conn = duckdb.connect(shared.vectorDB)
        getFiles = pd.read_sql_query("SELECT * FROM file", conn)
        files.set(getFiles)
        conn.close()
    index.set(
        VectorStoreIndex.from_vector_store(
            DuckDBVectorStore.from_local(shared.vectorDB)
        )
    )
    elementDisplay("blankDBMsg", "h")
    elementDisplay("tTab", "s")
    elementDisplay("qTab", "s")
    ui.insert_ui(uiUploadFile, "#processFile", "afterEnd")
    ui.remove_ui("#processFile")


# Get file details
@reactive.calc
def fileInfo():
    if filesTable.data_view(selected=True).empty:
        # elementDisplay("fileInfoCard", "h")
        return

    info = files().iloc[filesTable.data_view(selected=True).index[0]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        conn = duckdb.connect(shared.vectorDB)
        keywords = pd.read_sql_query(
            f"SELECT keyword FROM keyword WHERE fID = {info.fID}", conn
        )
        conn.close()
    keywords = "; ".join(keywords["keyword"])
    # elementDisplay("fileInfoCard", "s")

    return HTML(
        f"<h4>{info.fileName}</h4><ul>"
        f"<li><b>Summary title</b> <i>(AI generated)</i>: {info.title}</li>"
        f"<li><b>Summary subtitle</b> <i>(AI generated)</i>: {info.subtitle}</li>"
        f"<li><b>Uploaded</b>: {info.created}</li></ul>"
        "<p><b>Top-10 keywords extracted from document</b> <i>(AI generated)</i></p>"
        f"{keywords}"
    )


# ---- QUIZ QUESTIONS ----


# LLM engine for generation
@reactive.calc
def quizEngine():
    qa_prompt_str = (
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Given the context information and not prior knowledge, "
        "answer the question: {query_str}\n"
    )

    refine_prompt_str = (
        "We have the opportunity to refine the original answer "
        "(only if needed) with some more context below.\n"
        "------------\n"
        "{context_msg}\n"
        "------------\n"
        "Given the new context, refine the original answer to better "
        "answer the question: {query_str}. "
        "If the context isn't useful, output the original answer again.\n"
        "Original Answer: {existing_answer}"
    )

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                """
Generate a question focused on the highlighted concept and take the following into account:
* If possible integrate across multiple concepts. 
* Do NOT mention the topic as part of the question (that's inferred) 
* Try to generate a question that that forces the student to think critically (not just a short definition).
* Generate 4 possible answers, with only ONE correct option, and an explanation why each option is correct or incorrect.

You will output a python dictionary string according to this template:
{{"question":"<add question>","answer":"<e.g. A>","optionA":"","explanationA":"","optionB":"","explanationB":"","optionC":"","explanationC":"","optionD":"","explanationD":""}}"""
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=qa_prompt_str),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                "Make sure the provided response is a Python dictionary. Double check correct use of quotes"
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return index.get().as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=shared.llm,
    )


# When the generate button is clicked...
@reactive.effect
@reactive.event(input.qGenerate)
def _():
    elementDisplay("qBusyMsg", "s")
    elementDisplay("qBtnSet", "h")

    conn = sqlite3.connect(shared.appDB)
    topic = pd.read_sql_query(
        f"SELECT topic FROM topic WHERE tID = {input.qtID()}", conn
    )
    conceptList = pd.read_sql_query(
        f"SELECT cID, max(concept) as concept, count() as n FROM (SELECT cID, concept FROM concept WHERE tID = {input.qtID()} "
        f"UNION ALL SELECT cID, '' as concept FROM question where tID = {input.qtID()}) GROUP BY cID",
        conn,
    )
    cID = int(conceptList[conceptList["n"] == min(conceptList["n"])].sample(1)["cID"])
    prevQuestions = pd.read_sql_query(
        f"SELECT question FROM question WHERE cID = {cID} AND archived = 0", conn
    )
    conn.close()

    focusConcept = "* ".join(conceptList[conceptList["cID"] == cID]["concept"])
    conceptList = "* " + "\n* ".join(conceptList["concept"])
    if prevQuestions.shape[0] == 0:
        prevQuestions = ""
    else:
        prevQuestions = (
            "The following questions have already been generated so try to focus on a different aspect "
            "related to the concept if possible:\n"
            "* " + "\n* ".join(prevQuestions["question"])
        )

    info = f"""Generate a multiple choice question to test a student who just learned about the following topic: 
{topic.iloc[0]["topic"]}.\n
The following concepts were covered in this topic:
{conceptList}\n
The question should center around the following concept:
{focusConcept}\n
{prevQuestions}"""

    print(info)

    quizBotResponse(quizEngine(), info, cID)


# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def quizBotResponse(quizEngine, info, cID):
    # Given the LLM output might not be correct format (or fails to convert to a DF, try again if needed)
    valid = False
    tries = 0
    while not valid:
        try:
            resp = str(quizEngine.query(info))
            resp = pd.json_normalize(json.loads(resp))
            valid = True
        except Exception:
            print(("Failed to generate quiz question"))
            if tries > 1:
                return {"resp": None, "cID": cID}
            tries += 1

    return {"resp": resp, "cID": cID}


# Processing LLM response
@reactive.effect
def _():
    # Populate the respective UI outputs with the questions details
    resp = quizBotResponse.result()
    elementDisplay("qBusyMsg", "h")
    elementDisplay("qBtnSet", "s")

    if resp["resp"] is None:
        shared.modalMsg(
            "The generation of a question with the LLM failed, try again later", "Error"
        )
        return

    with reactive.isolate():
        q = resp["resp"].iloc[0]  # For now only processing one
        # Save the questions in the appAB
        conn = sqlite3.connect(shared.appDB)
        cursor = conn.cursor()
        # Insert question
        _ = cursor.execute(
            'INSERT INTO question(sID,tID,cID,question,answer,archived,created,modified,'
            'optionA,explanationA,optionB,explanationB,optionC,explanationC,optionD,explanationD)'
            f'VALUES({sessionID.get()},{input.tID()},{resp["cID"]},"{q["question"]}","{q["answer"]}",0,"{shared.dt()}","{shared.dt()}",'
            f'"{q["optionA"]}","{q["explanationA"]}","{q["optionB"]}","{q["explanationB"]}","{q["optionC"]}",'
            f'"{q["explanationC"]}","{q["optionD"]}","{q["explanationD"]}")'
        )
        qID = cursor.lastrowid
        q = pd.read_sql_query(
            f"SELECT qID, question FROM question WHERE tID = {input.qtID()} AND archived = 0",
            conn,
        )
        conn.commit()
        conn.close()
        # Update the UI
        ui.update_select(
            "qID", choices=dict(zip(q["qID"], q["question"])), selected=qID
        )


@reactive.effect
@reactive.event(input.qtID)
def _():
    # Get the question info from the DB
    conn = sqlite3.connect(shared.appDB)
    q = pd.read_sql_query(
        f"SELECT qID, question FROM question WHERE tID = {input.qtID()} AND archived = 0",
        conn,
    )
    conn.close()
    # Update the UI
    ui.update_select("qID", choices=dict(zip(q["qID"], q["question"])))


@reactive.effect
@reactive.event(input.qID, input.qDiscardChanges)
def _():
    # Get the question info from the DB
    conn = sqlite3.connect(shared.appDB)
    q = pd.read_sql_query(
        f"SELECT * FROM question WHERE qID = {input.qID()}", conn
    ).iloc[0]
    conn.close()
    # Update the UI
    ui.update_text_area("rqQuestion", value=q["question"])
    ui.update_text("rqOA", value=q["optionA"])
    ui.update_text_area("rqOAexpl", value=q["explanationA"])
    ui.update_text("rqOB", value=q["optionB"])
    ui.update_text_area("rqOBexpl", value=q["explanationB"])
    ui.update_text("rqOC", value=q["optionC"])
    ui.update_text_area("rqOCexpl", value=q["explanationC"])
    ui.update_text("rqOD", value=q["optionD"])
    ui.update_text_area("rqODexpl", value=q["explanationD"])
    ui.update_radio_buttons("rqCorrect", selected=q["answer"])


# Save question edits
@reactive.effect
@reactive.event(input.qSaveChanges)
def _():
    # Get the original question
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    q = pd.read_sql_query(
        "SELECT qID,question,answer,optionA,explanationA,optionB,explanationB,optionC,"
        f"explanationC,optionD,explanationD FROM question WHERE qID = {input.qID()}",
        conn,
    ).iloc[0]
    qID = int(q.iloc[0])
    fields = [
        "rqQuestion",
        "rqCorrect",
        "rqOA",
        "rqOAexpl",
        "rqOB",
        "rqOBexpl",
        "rqOC",
        "rqOCexpl",
        "rqOD",
        "rqODexpl",
    ]
    now = shared.dt()

    # Backup any changes
    updates = []
    for i, v in enumerate(fields):
        if input[v].get() != q.iloc[i + 1]:
            shared.backupQuery(
                cursor, sessionID.get(), "question", qID, q.index[i + 1], None, now
            )
            updates.append(f'{q.index[i+1]} = "{input[v].get()}"')
    # Update the question
    if updates != []:
        updates = ",".join(updates) + f', modified = "{now}"'
        _ = cursor.execute(f"UPDATE question SET {updates} WHERE qID = {qID}")
        conn.commit()
        shared.modalMsg("Your edits were successfully saved", "Update complete")
    else:
        shared.modalMsg("No changes were detected")

    conn.close()


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
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        "INSERT INTO feedback_general(sID,code,created,email,details) VALUES(?,?,?,?,?)",
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
