# ******************************************
# ----------- ACCORNS: ADMIN APP -----------
# ******************************************

# Welcome to ACCORNS:
# Admin Control Center Overseeing RAG Needed for SCUIRREL

# See app_shared.py for variables and functions shared across sessions
import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# -- General
import os
from io import BytesIO
import pandas as pd
import json
import warnings
import traceback

# -- Llamaindex
from llama_index.core import VectorStoreIndex, ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore

# -- Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div

# The following is needed to prevent async issues when inserting new data in vector DB
# https://github.com/run-llama/llama_index/issues/9978
import nest_asyncio

nest_asyncio.apply()

# ----------- SHINY APP -----------
# *********************************

uID = 2  # if registered admins make reactive later

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

# --- RENDERING UI ---
# ********************

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
os.path.join(curDir, "ACCORNS")

ui.page_opts(fillable=True, window_title="ACCORNS")
ui.head_content(
    ui.include_css(os.path.join(curDir, "shared", "shared_css", "shared.css")),
    ui.include_css(os.path.join(curDir, "ACCORNS", "accorns_css", "accorns.css")),
    ui.include_js(os.path.join(curDir, "ACCORNS", "accorns_js", "accorns.js")),
    ui.include_js(os.path.join(curDir, "shared", "shared_js", "shared.js")),
)
# --- CUSTOM JS FUNCTIONS (Python side) ---


# This function allows you to hide/show/disable/enable elements by ID or data-value
# The latter is needed because tabs don't use ID's but data-value
def elementDisplay(id, effect):
    @reactive.effect
    async def _():
        await session.send_custom_message("hideShow", {"id": id, "effect": effect})


# --- UI LAYOUT ---

with ui.navset_pill(id="tab"):
    # TAB 1 - VECTOR DATABASE
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

    # TAB 2 - TOPICS
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
            with ui.panel_conditional("input.tID"):
                with ui.card():
                    ui.card_header("Concepts related to the topic")

                    @render.data_frame
                    def conceptsTable():
                        if concepts.get() is None:
                            return
                        return render.DataTable(
                            concepts.get()[["concept"]],
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

    # TAB 3 - QUIZ QUESTIONS
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
     # TAB 4 - USER MANAGEMENT
    with ui.nav_panel("User Management", value="uTab"):
        # Select a topic and a question with options to add or archive
        with ui.card():
            ui.card_header("Generate access codes")
            ui.input_numeric("numCodes", "Number of codes to generate", value=1, min=1, max=500)
            ui.input_select("role", "Role", choices={0: "User", 1: "Instructor", 2: "Admin"})
            ui.input_action_button("generateCodes", "Generate codes", width="180px")
            
            # Codes table
            @render.data_frame
            def codesTable():
                return render.DataTable(
                    accessCodes(),
                    width="100%",
                    selection_mode="row",
                )
            with ui.panel_conditional("input.generateCodes > 0"):
                #Option to export codes as CSV
                @render.download(label = "Download as CSV", filename = "hollow-tree_accessCodes.csv")
                def downloadCodes():
                    with BytesIO() as buf:
                        accessCodes().to_csv(buf, index=False)
                        yield buf.getvalue()
                 
# Customised feedback button (floating at right side of screen)
ui.input_action_button("feedback", "Provide Feedback")

# --- REACTIVE VARIABLES ---

sessionID = reactive.value(0)

conn = shared.vectorDBConn(accorns_shared.postgresUser)
files = shared.pandasQuery(conn, query='SELECT * FROM "file"')
conn.close()

# Hide the topic and question tab if the vector database is empty and show welcome message
if files.shape[0] == 0:
    elementDisplay("tTab", "h")
    elementDisplay("qTab", "h")
    elementDisplay("blankDBMsg", "s")

if files.shape[0] == 0:
    index = None
else:
    if shared.remoteAppDB:
        vectorStore = PGVectorStore.from_params(
            host=shared.postgresHost,
            port=shared.postgresPort,
            user=accorns_shared.postgresUser,
            password=os.environ.get("POSTGRES_PASS_ACCORNS"),
            database="vector_db",
            table_name="document",
            embed_dim=1536,  # openai embedding dimension
        )
        index = VectorStoreIndex.from_vector_store(vectorStore)
    else:
        index = VectorStoreIndex.from_vector_store(
            DuckDBVectorStore.from_local(shared.vectorDB)
        )

# Some of these could become reactive calls in future but for now we use
# reactive var until issue with reactive.calls is resolved
# https://github.com/posit-dev/py-shiny/issues/1271
index = reactive.value(index)
topics = reactive.value(None)
concepts = reactive.value(None)
files = reactive.value(files)


# --- REACTIVE FUNCTIONS ---

# Stuff to run once when the session has loaded
if hasattr(session, "_process_ui"):
    # Register the session start in the DB
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    # For now we only have anonymous users (appID 1 -> ACCORNS)
    sID = shared.executeQuery(
        cursor,
        'INSERT INTO "session" ("shinyToken", "uID", "appID", "start")'
        "VALUES(?, ?, 1, ?)",
        (session.id, uID, shared.dt()),
        lastRowId="sID",
    )
    # Get all active topics
    newTopics = shared.pandasQuery(
        conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
    )
    conn.commit()
    conn.close()
    sessionID.set(sID)
    # Set the topics
    ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])))
    topics.set(newTopics)

# Code to run at the END of the session (i.e. when user disconnects)
_ = session.on_ended(lambda: theEnd())


def theEnd():
    # Isolate so we can use the final values of reactive variables
    with reactive.isolate():
        # Add logs to the database after user exits
        sID = sessionID.get()
        conn = shared.appDBConn(accorns_shared.postgresUser)
        cursor = conn.cursor()
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
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    tID = shared.executeQuery(
        cursor,
        'INSERT INTO "topic"("topic", "created", "modified", "description")'
        "VALUES(?, ?, ?, ?)",
        (input.ntTopic(), shared.dt(), shared.dt(), input.ntDescr()),
        lastRowId="tID",
    )
    newTopics = shared.pandasQuery(
        conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
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
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    # Backup old value
    accorns_shared.backupQuery(
        cursor, sessionID.get(), "topic", input.tID(), "topic", False
    )
    # Update to new
    _ = shared.executeQuery(
        cursor,
        'UPDATE "topic" SET "topic" = ?, "modified" = ? WHERE "tID" = ?',
        (input.etInput(), shared.dt(), input.tID()),
    )
    newTopics = shared.pandasQuery(
        conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
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

    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'UPDATE "topic" SET "archived" = 1, "modified" = ? WHERE "tID" = ?',
        (shared.dt(), input.tID()),
    )
    newTopics = shared.pandasQuery(
        conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
    )

    # Empty the concept table is last topic was removed
    if topics.shape[0] == 0:
        conceptList = shared.pandasQuery(
            conn, 'SELECT * FROM "concept" WHERE "tID" = 0'
        )
        concepts.set(conceptList)

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
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'INSERT INTO "concept"("tID", "concept", "created", "modified") VALUES(?, ?, ?, ?)',
        (input.tID(), input.ncInput(), shared.dt(), shared.dt()),
    )
    conceptList = shared.pandasQuery(
        conn, f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "archived" = 0'
    )
    conn.commit()
    conn.close()
    # Update concept table
    concepts.set(conceptList)
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
    cID = concepts.get().iloc[conceptsTable.data_view(selected=True).index[0]]["cID"]
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    # Backup old value
    accorns_shared.backupQuery(
        cursor, sessionID.get(), "concept", int(cID), "concept", False
    )
    # Update to new
    _ = shared.executeQuery(
        cursor,
        'UPDATE "concept" SET "concept" = ?, "modified" = ? WHERE "cID" = ?',
        (input.ecInput(), shared.dt(), int(cID)),
    )
    conceptList = shared.pandasQuery(
        conn, f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "archived" = 0'
    )
    conn.commit()
    conn.close()
    # Update concept table
    concepts.set(conceptList)
    ui.modal_remove()


# --- delete a concept (archive)
@reactive.effect
@reactive.event(input.cArchive)
def _():
    if conceptsTable.data_view(selected=True).empty:
        return

    cID = concepts.get().iloc[conceptsTable.data_view(selected=True).index[0]]["cID"]
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'UPDATE "concept" SET "archived" = 1, "modified" = ? WHERE "cID" = ?',
        (shared.dt(), int(cID)),
    )
    conceptList = shared.pandasQuery(
        conn, f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "archived" = 0'
    )
    conn.commit()
    conn.close()

    concepts.set(conceptList)


@reactive.effect
@reactive.event(input.tID)
def _():
    tID = input.tID() if input.tID() else 0
    conn = shared.appDBConn(accorns_shared.postgresUser)
    conceptList = shared.pandasQuery(
        conn, f'SELECT * FROM "concept" WHERE "tID" = {tID} AND "archived" = 0'
    )
    conn.close()
    concepts.set(conceptList)


# ---- VECTOR DATABASE ----


@reactive.effect
@reactive.event(input.newFile, ignore_init=True)
def _():
    # Move the file to the uploadedFiles folder
    updateVectorDB(
        input.newFile()[0]["datapath"],
        shared.vectorDB,
        accorns_shared.storageFolder,
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
    return accorns_shared.addFileToDB(
        newFile=newFile,
        vectorDB=vectorDB,
        storageFolder=storageFolder,
        newFileName=newFileName,
    )


@reactive.effect
def _():
    insertionResult = updateVectorDB.result()[0]

    if insertionResult == 0:
        msg = "File successfully added to the vector database"
    elif insertionResult == 1:
        msg = "A file with the same name already exists. Skipping upload"
    else:
        msg = "Not a valid file type. Please upload a .csv, .pdf, .docx, .txt, .md, .epub, .ipynb, .ppt or .pptx file"

    ui.modal_show(ui.modal(msg, title="Success" if insertionResult == 0 else "Issue"))

    conn = shared.vectorDBConn(accorns_shared.postgresUser)

    getFiles = shared.pandasQuery(conn, 'SELECT * FROM "file"')
    files.set(getFiles)

    if shared.remoteAppDB:
        vectorStore = PGVectorStore.from_params(
            host=shared.postgresHost,
            user=accorns_shared.postgresUser,
            password=os.environ.get("POSTGRES_PASS_ACCORNS"),
            database="vector_db",
            table_name="document",
            embed_dim=1536,  # openai embedding dimension
        )
    else:
        vectorStore = DuckDBVectorStore.from_local(shared.vectorDB)

    conn.close()

    index.set(VectorStoreIndex.from_vector_store(vectorStore))

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

        conn = shared.vectorDBConn(accorns_shared.postgresUser)
        keywords = shared.pandasQuery(
            conn, f'SELECT "keyword" FROM "keyword" WHERE "fID" = {int(info.fID)}'
        )
        conn.close()
    keywords = "; ".join(keywords["keyword"])

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

    conn = shared.appDBConn(accorns_shared.postgresUser)
    topic = shared.pandasQuery(
        conn, f'SELECT "topic" FROM "topic" WHERE "tID" = {input.qtID()}'
    )
    conceptList = shared.pandasQuery(
        conn,
        'SELECT "cID", max("concept") as "concept", count(*) as n FROM '
        f'(SELECT "cID", "concept" FROM "concept" WHERE "tID" = {input.qtID()} '
        f'UNION ALL SELECT "cID", \'\' as concept FROM "question" where "tID" = {input.qtID()}) GROUP BY "cID"',
    )
    cID = int(
        conceptList[conceptList["n"] == min(conceptList["n"])].sample(1)["cID"].iloc[0]
    )
    prevQuestions = shared.pandasQuery(
        conn,
        f'SELECT "question" FROM "question" WHERE "cID" = {cID} AND "archived" = 0',
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

    botResponse(quizEngine(), info, cID)


# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def botResponse(quizEngine, info, cID):
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
    resp = botResponse.result()
    elementDisplay("qBusyMsg", "h")
    elementDisplay("qBtnSet", "s")

    if resp["resp"] is None:
        accorns_shared.modalMsg(
            "The generation of a question with the LLM failed, try again later", "Error"
        )
        return

    with reactive.isolate():
        q = resp["resp"].iloc[0]  # For now only processing one
        # Save the questions in the appAB
        conn = shared.appDBConn(accorns_shared.postgresUser)
        cursor = conn.cursor()
        # Insert question
        qID = shared.executeQuery(
            cursor,
            'INSERT INTO "question"("sID","tID","cID","question","answer","archived","created","modified",'
            '"optionA","explanationA","optionB","explanationB","optionC","explanationC","optionD","explanationD")'
            "VALUES(?,?,?,?,?,0,?,?,?,?,?,?,?,?,?,?)",
            (
                sessionID.get(),
                input.tID(),
                resp["cID"],
                q["question"],
                q["answer"],
                shared.dt(),
                shared.dt(),
                q["optionA"],
                q["explanationA"],
                q["optionB"],
                q["explanationB"],
                q["optionC"],
                q["explanationC"],
                q["optionD"],
                q["explanationD"],
            ),
            lastRowId="qID",
        )
        q = shared.pandasQuery(
            conn,
            f'SELECT "qID", "question" FROM "question" WHERE "tID" = {input.qtID()} AND "archived" = 0',
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
    conn = shared.appDBConn(accorns_shared.postgresUser)
    q = shared.pandasQuery(
        conn,
        f'SELECT "qID", "question" FROM "question" WHERE "tID" = {input.qtID()} AND "archived" = 0',
    )
    conn.close()
    # Update the UI
    ui.update_select("qID", choices=dict(zip(q["qID"], q["question"])))


@reactive.effect
@reactive.event(input.qID, input.qDiscardChanges)
def _():
    # Get the question info from the DB
    conn = shared.appDBConn(accorns_shared.postgresUser)
    q = shared.pandasQuery(
        conn, f'SELECT * FROM "question" WHERE "qID" = {input.qID()}'
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
    conn = shared.appDBConn(accorns_shared.postgresUser)
    cursor = conn.cursor()
    q = shared.pandasQuery(
        conn,
        'SELECT "qID","question","answer","optionA","explanationA","optionB","explanationB","optionC",'
        f'"explanationC","optionD","explanationD" FROM "question" WHERE "qID" = {input.qID()}',
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
            accorns_shared.backupQuery(
                cursor, sessionID.get(), "question", qID, q.index[i + 1], None, now
            )
            updates.append(f"\"{q.index[i+1]}\" = '{input[v].get()}'")
    # Update the question
    if updates != []:
        updates = ",".join(updates) + f", \"modified\" = '{now}'"
        _ = shared.executeQuery(
            cursor, f'UPDATE "question" SET {updates} WHERE "qID" = ?', (qID,)
        )
        conn.commit()
        accorns_shared.modalMsg("Your edits were successfully saved", "Update complete")
    else:
        accorns_shared.modalMsg("No changes were detected")

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
    conn = shared.appDBConn(accorns_shared.postgresUser)
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

@reactive.calc
@reactive.event(input.generateCodes)
def accessCodes():
    newCodes = accorns_shared.generate_access_codes(n = input.numCodes(), uID= uID, adminLevel=int(input.role()))
    role = ["user", "instructor", "admin"][int(input.role())]
    # create a pandas dataframe form the dictionary
    return pd.DataFrame({"accessCode": newCodes, "role": role})
