# **************************************
# ----------- TUTORBOT ADMIN -----------
# **************************************
import shared

# -- General
import sqlite3
import pandas as pd

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

# Make new app DB if needed
print(shared.createAppDB(shared.appDB, addDemo=True))

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
# **********************

ui.page_opts(fillable=True)

# Add some JS so that pressing enter can send the message too
ui.head_content(
    HTML("""<script>
         $(document).keyup(function(event) {
            if ($("#newChat").is(":focus") && (event.key == "Enter")) {
                $("#send").click();
            }
        });
         </script>""")
)
ui.include_css("www/styles.css")

with ui.navset_pill(id="tab"):
    with ui.nav_panel("Topics"):
        with ui.layout_columns(col_widths=12):
            with ui.card():
                ui.card_header("Topic")
                div(
                    ui.input_action_button("tAdd", "Add new", width="180px"),
                    ui.input_action_button(
                        "tArchive", "Archive selected", width="180px"
                    ),
                )
                ui.input_select("tID", "Pick a topic", choices=[], width="400px")

            with ui.card():
                ui.card_header("Concepts related to the topic")
                HTML(
                    "<i>Concepts are facts or pieces of information you want the Bot to check with your students."
                    "You can be very brief, as all context will be retrieved from the database of documents. "
                    "Don't be too broad, as this might cause confusion (you'll have to test it). "
                    "Try to limit the number of concepts to 4 - 8 as the AI might preform worse with a large number</i>"
                )
                div(
                    ui.input_action_button("cAdd", "Add new", width="180px"),
                    ui.input_action_button("cEdit", "Edit selected", width="180px"),
                    ui.input_action_button(
                        "cArchive", "Archive selected", width="180px"
                    ),
                    style="display:inline",
                )

                @render.data_frame
                def conceptsTable():
                    return render.DataTable(
                        concepts.get()[["concept"]],
                        width="100%",
                        row_selection_mode="single",
                    )

    with ui.nav_panel("Vector Database"):
        with ui.card():
            ui.card_header("Vector database files")

            @render.data_frame
            def filesTable():
                return render.DataTable(
                    files.get(), width="100%", row_selection_mode="single"
                )

        with ui.card():
            ui.card_header("Upload a new file")
            uiUploadFile


# --- REACTIVE VARIABLES ---

sessionID = reactive.value(0)

# Workaround until issue with reactive.cals is resolved
# https://github.com/posit-dev/py-shiny/issues/1271
conn = sqlite3.connect(shared.appDB)
concepts = pd.read_sql_query("SELECT * FROM concept WHERE tID = 0", conn)
files = pd.read_sql_query("SELECT * FROM file", conn)
conn.close()

concepts = reactive.value(concepts)
files = reactive.value(files)

# --- REACTIVE FUNCTIONS ---


# Code to run at the start of the session (i.e. user connects)
@reactive.effect
def _():
    # Register the session in the DB at start
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    # For now we only have anonymous users
    cursor.execute(
        "INSERT INTO session (shinyToken, uID, start)"
        f'VALUES("{session.id}", {uID}, "{shared.dt()}")'
    )
    sID = cursor.lastrowid
    sessionID.set(sID)
    topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()
    # Update the topics select input
    ui.update_select("tID", choices=dict(zip(topics["tID"], topics["topic"])))

    # Set the function to be called when the session ends
    _ = session.on_ended(lambda: theEnd(sID))


# Code to run at the end of the session (i.e. user disconnects)
def theEnd(sID):
    # Add logs to the database after user exits
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(f'UPDATE session SET end = "{shared.dt()}" WHERE sID = {sID}')
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
        ui.input_action_button("ntAdd", "Add"),
        title="Add a topic",
        easy_close=True,
        size="l",
        footer=None,
    )
    ui.modal_show(m)


@reactive.effect
@reactive.event(input.ntAdd)
def addNewTopic():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.ntTopic()):
        ui.remove_ui("#notGood")
        ui.insert_ui(
            HTML(
                "<div id=notGood style='color: red'>New topic must be at least 6 characters</div>"
            ),
            "#ntAdd",
            "afterEnd",
        )
        return

    # Add new topic to DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO topic(topic, created, description)"
        f'VALUES("{input.ntTopic()}", "{shared.dt()}", "{input.ntDescr()}")'
    )
    tID = cursor.lastrowid
    topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()
    # Update the topic list
    ui.update_select(
        "tID", choices=dict(zip(topics["tID"], topics["topic"])), selected=tID
    )
    ui.modal_remove()


# # --- Edit an existing concepts
# @reactive.effect
# @reactive.event(input.cEdit)
# def show_login_modal():
#     if input.conceptsTable_selected_rows() is None: return
#     concept = concepts().iloc[input.conceptsTable_selected_rows()]["concept"]
#     m = ui.modal(
#         ui.tags.p(HTML('<i>Make sure to only make edits that do not change the concept. '
#                        'Otherwise add or delete instead</i>')),
#         ui.input_text("ecInput", "New concept:", width="100%", value = concept),
#         ui.input_action_button("ncEdit", "Update"),
#         title="Edit and existing topic",
#         easy_close=True,
#         size = "l",
#         footer=None,
#     )
#     ui.modal_show(m)

# @reactive.effect
# @reactive.event(input.ncEdit)
# def addNewConcept():
#     cID = concepts().iloc[input.conceptsTable_selected_rows()]["cID"]
#     conn = sqlite3.connect(shared.appDB)
#     cursor = conn.cursor()
#     cursor.execute(f'UPDATE concept SET concept = "{input.ecInput()}", '
#                    f'modified = "{shared.dt()}" WHERE cID = {cID}')
#     conn.commit()
#     conn.close()

#     ui.modal_remove()


# --- Archive a topic
@reactive.effect
@reactive.event(input.tArchive)
def _():
    if input.tID() is None:
        return

    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE topic SET archived = 1, "
        f'modified = "{shared.dt()}" WHERE tID = {input.tID()}'
    )
    topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)

    ui.update_select("tID", choices=dict(zip(topics["tID"], topics["topic"])))

    # Empty the concept table is last topic was removed
    if topics.shape[0] == 0:
        conceptList = pd.read_sql_query("SELECT * FROM concept WHERE tID = 0", conn)
        concepts.set(conceptList)

    conn.commit()
    conn.close()


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
        ui.input_action_button("ncAdd", "Add"),
        title="Add a new concept to the topic",
        easy_close=True,
        size="l",
        footer=None,
    )
    ui.modal_show(m)


@reactive.effect
@reactive.event(input.ncAdd)
def _():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.ncInput()):
        ui.remove_ui("#notGood")
        ui.insert_ui(
            HTML(
                "<div id=notGood style='color: red'>New concept must be at least 6 characters</div>"
            ),
            "#ncAdd",
            "afterEnd",
        )
        return

    # Add new topic to DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO concept(tID, concept, created)"
        f'VALUES({input.tID()}, "{input.ncInput()}", "{shared.dt()}")'
    )
    conceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn
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
    if input.conceptsTable_selected_rows() != ():
        concept = concepts.get().iloc[input.conceptsTable_selected_rows()]["concept"]
        m = ui.modal(
            ui.tags.p(
                HTML(
                    "<i>Make sure to only make edits that do not change the concept. "
                    "Otherwise add or delete instead</i>"
                )
            ),
            ui.input_text("ecInput", "New concept:", width="100%", value=concept),
            ui.input_action_button("ncEdit", "Update"),
            title="Edit and existing topic",
            easy_close=True,
            size="l",
            footer=None,
        )
        ui.modal_show(m)


@reactive.effect
@reactive.event(input.ncEdit)
def _():
    # Only proceed if the input is valid
    if not shared.inputCheck(input.ecInput()):
        ui.remove_ui("#notGood")
        ui.insert_ui(
            HTML(
                "<div id=notGood style='color: red'>A concept must be at least 6 characters</div>"
            ),
            "#ncEdit",
            "afterEnd",
        )
        return

    # Edit topic in DB
    cID = concepts.get().iloc[input.conceptsTable_selected_rows()]["cID"]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(
        f'UPDATE concept SET concept = "{input.ecInput()}", '
        f'modified = "{shared.dt()}" WHERE cID = {cID}'
    )
    conceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn
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
    if input.conceptsTable_selected_rows() == ():
        return

    cID = concepts.get().iloc[input.conceptsTable_selected_rows()]["cID"]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE concept SET archived = 1, "
        f'modified = "{shared.dt()}" WHERE cID = {cID}'
    )
    conceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn
    )
    conn.commit()
    conn.close()

    concepts.set(conceptList)


@reactive.effect
@reactive.event(input.tID)
def _():
    tID = input.tID() if input.tID() else 0
    conn = sqlite3.connect(shared.appDB)
    conceptList = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {tID} AND archived = 0", conn
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
        shared.appDB,
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
async def updateVectorDB(newFile, vectorDB, appDB, storageFolder, newFileName):
    print("Start adding file...")
    return shared.addFileToDB(newFile, vectorDB, appDB, storageFolder, newFileName)


@reactive.effect
def _():
    insertionResult = updateVectorDB.result()[0]
    msg = (
        "File succesfully added to the vector database"
        if insertionResult == 0
        else "A file with the same name already exists. Skipping upload"
    )
    ui.modal_show(ui.modal(msg, title="Success" if insertionResult == 0 else "Issue"))
    conn = sqlite3.connect(shared.appDB)
    getFiles = pd.read_sql_query("SELECT * FROM file", conn)
    files.set(getFiles)
    conn.close()
    ui.insert_ui(uiUploadFile, "#processFile", "afterEnd")
    ui.remove_ui("#processFile")
