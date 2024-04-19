# ******************************************
# ----------- ACCORNS: ADMIN APP -----------
# ******************************************

# Welcome to ACCORNS:
# Admin Control Center Overseeing RAG Needed for SCUIRREL

# See app_shared.py for variables and functions shared across sessions
import app_shared as shared

# -- General
import sqlite3
import pandas as pd
import json

# -- Llamaindex
from llama_index.core import VectorStoreIndex, ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.vector_stores.duckdb import DuckDBVectorStore

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

ui.page_opts(fillable=True)
ui.include_css("www/styles.css")

# --- CUSTOM JS FUNCTIONS (move to separate file later) ---

# This function allows you to hide/show/disable/enable elements by ID or data-value
# The latter is needed because tabs don't use ID's but data-value
ui.tags.script(
    """
    Shiny.addCustomMessageHandler("hideShow", function(x) {

        if (document.getElementById(x.id)) {
            var element = document.getElementById(x.id);
        } else if (document.querySelector('[data-value="' + x.id + '"]')) {
            var element = document.querySelector('[data-value="' + x.id + '"]');
        } else {
            alert("No element found with an ID or data-value of:" + x.id);
            return;
        }

        switch(x.effect) {
            case "d":
                element.setAttribute("disabled", true);
                break;
            case "e":
                element.setAttribute("disabled", false);
                break;
            case "h":
                element.style.display = "none";
                break;
            case "s":
                element.style.display = "";
                break;
        }
        
    });
    """
)


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
                "<i>Welcome to ACCORNS, the Admin Control Center Overseeing RAG Needed for SCUIRREL!"
                "In order to get started, please add at least one file to the vector database</i>"
            )
        # Tables of the files that are in the DB
        with ui.card():
            ui.card_header("Vector database files")

            @render.data_frame
            def filesTable():
                return render.DataTable(
                    files.get(), width="100%", row_selection_mode="single"
                )

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
            with ui.card():
                ui.card_header("Concepts related to the topic")

                @render.data_frame
                def conceptsTable():
                    return render.DataTable(
                        concepts.get()[["concept"]],
                        width="100%",
                        row_selection_mode="single",
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
                    "<i>Concepts are facts or pieces of information you want SCUIRREL to check with your students. "
                    "You can be very brief, as all context will be retrieved from the database of documents. "
                    "Don't be too broad, as this might cause confusion (you'll have to test it). "
                    "Try to limit the number of concepts to 4 - 8 as the AI might preform worse with a large number</i>"
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
                div(ui.input_action_button("qSaveChanges", "Save Changes"),
                    ui.input_action_button("qDiscardChanges", "Discard Changes"))
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

# --- REACTIVE VARIABLES ---

sessionID = reactive.value(0)

# Workaround until issue with reactive.calls is resolved
# https://github.com/posit-dev/py-shiny/issues/1271
conn = sqlite3.connect(shared.appDB)
topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
concepts = pd.read_sql_query("SELECT * FROM concept WHERE tID = 0", conn) # get empty df
files = pd.read_sql_query("SELECT * FROM file", conn)

# Hide the topic and question tab if the vector database is empty and show welcome message
if files.shape[0] == 0:
    elementDisplay("tTab", "h")
    elementDisplay("qTab", "h")
    elementDisplay("blankDBMsg", "s")

conn.close()

if files.shape[0] == 0:
    index = None
else:
    index = VectorStoreIndex.from_vector_store(
        DuckDBVectorStore.from_local(shared.vectorDB)
    )

index = reactive.value(index)
topics = reactive.value(topics)
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
    newTopics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()

    # Update the topics select input
    ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])))
    topics.set(newTopics)
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
        title="Add a topic",
        easy_close=True,
        size="l",
        footer=ui.TagList(ui.input_action_button("ntAdd", "Add"),ui.modal_button("Cancel")),
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
    cursor.execute(
        "INSERT INTO topic(topic, created, modified, description)"
        f'VALUES("{input.ntTopic()}", "{shared.dt()}", "{shared.dt()}", "{input.ntDescr()}")'
    )
    tID = cursor.lastrowid
    newTopics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()

    # Update the topics select input
    ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])), selected=tID)
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
            footer=ui.TagList(ui.input_action_button("etEdit", "Update"),ui.modal_button("Cancel")),
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

    if topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["topic"] == input.etInput():
        ui.remove_ui("#noGoodTopic")
        ui.insert_ui(
            HTML(
                "<div id=noGoodTopic style='color: red'>No change detected</div>"
            ),
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
    cursor.execute(
        f'UPDATE topic SET topic = "{input.etInput()}", '
        f'modified = "{shared.dt()}" WHERE tID = {input.tID()}'
    )
    newTopics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()

    # Update the topics select input
    ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])), selected=input.tID())
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
    cursor.execute(
        "UPDATE topic SET archived = 1, "
        f'modified = "{shared.dt()}" WHERE tID = {input.tID()}'
    )
    newTopics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)

    # Empty the concept table is last topic was removed
    if topics.shape[0] == 0:
        conceptList = pd.read_sql_query("SELECT * FROM concept WHERE tID = 0", conn)
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
        footer=ui.TagList(ui.input_action_button("ncAdd", "Add"),ui.modal_button("Cancel")),
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
    cursor.execute(
        "INSERT INTO concept(tID, concept, created, modified)"
        f'VALUES({input.tID()}, "{input.ncInput()}", "{shared.dt()}", "{shared.dt()}")'
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
            title="Edit and existing topic",
            easy_close=True,
            size="l",
            footer=ui.TagList(ui.input_action_button("ncEdit", "Update"),ui.modal_button("Cancel")),
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
    
    if concepts.get().iloc[input.conceptsTable_selected_rows()]["concept"] == input.ecInput():
        ui.remove_ui("#noGoodConcept")
        ui.insert_ui(
            HTML(
                "<div id=noGoodConcept style='color: red'>No change detected</div>"
            ),
            "#ecInput",
            "afterEnd",
        )
        return

    # Update the DB
    cID = concepts.get().iloc[input.conceptsTable_selected_rows()]["cID"]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()   
    # Backup old value
    shared.backupQuery(cursor, sessionID.get(), "concept", cID, "concept", False)
    # Update to new 
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
    topic = pd.read_sql_query(f"SELECT topic FROM topic WHERE tID = {input.qtID()}", conn)    
    conceptList = pd.read_sql_query(f"SELECT cID, max(concept) as concept, count() as n FROM (SELECT cID, concept FROM concept WHERE tID = {input.qtID()} "
                                    f"UNION ALL SELECT cID, '' as concept FROM question where tID = {input.qtID()}) GROUP BY cID", conn)  
    cID = int(conceptList[conceptList["n"] == min(conceptList["n"])].sample(1)["cID"])
    prevQuestions = pd.read_sql_query(f"SELECT question FROM question WHERE cID = {cID} AND archived = 0", conn)
    conn.close()

    focusConcept = "* ".join(conceptList[conceptList["cID"] == cID]["concept"])
    conceptList = "* " + "\n* ".join(conceptList["concept"])
    if  prevQuestions.shape[0] == 0:
        prevQuestions = ""
    else:        
        prevQuestions = ("The following questions have already been generated so try to focus on a different aspect "
                         "related to the concept if possible:\n"
                         "* " + "\n* ".join(prevQuestions["question"]))

    info = f"""Generate a multiple choice question to test a student who just learned about the following topic: 
{topic.iloc[0]["topic"]}.\n
The following concepts were covered in this topic:
{conceptList}\n
The question should center around the following concept:
{focusConcept}\n
{prevQuestions}"""
    
    print(info)

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
        shared.modalMsg("The generation of a question with the LLM failed, try again later", "Error")       
        return
    
    with reactive.isolate():
        q = resp["resp"].iloc[0]  # For now only processing one
        #Save the questions in the appAB
        conn = sqlite3.connect(shared.appDB)
        cursor = conn.cursor()   
        # Insert question 
        cursor.execute(
            'INSERT INTO question(sID,tID,cID,question,answer,archived,created,modified,'
            'optionA,explanationA,optionB,explanationB,optionC,explanationC,optionD,explanationD)'
            f'VALUES({sessionID.get()},{input.tID()},{resp["cID"]},"{q["question"]}","{q["answer"]}",0,"{shared.dt()}","{shared.dt()}",'
            f'"{q["optionA"]}","{q["explanationA"]}","{q["optionB"]}","{q["explanationB"]}","{q["optionC"]}",'
            f'"{q["explanationC"]}","{q["optionD"]}","{q["explanationD"]}")'
        )
        qID = cursor.lastrowid
        q = pd.read_sql_query(f"SELECT qID, question FROM question WHERE tID = {input.qtID()} AND archived = 0", conn)
        conn.commit()
        conn.close()
        #Update the UI    
        ui.update_select("qID", choices=dict(zip(q["qID"], q["question"])), selected=qID)


@reactive.effect
@reactive.event(input.qtID)
def _():  
    #Get the question info from the DB
    conn = sqlite3.connect(shared.appDB)
    q = pd.read_sql_query(f"SELECT qID, question FROM question WHERE tID = {input.qtID()} AND archived = 0", conn)
    conn.close() 
    #Update the UI
    ui.update_select("qID", choices=dict(zip(q["qID"], q["question"])))

@reactive.effect
@reactive.event(input.qID, input.qDiscardChanges)
def _():  
    #Get the question info from the DB
    conn = sqlite3.connect(shared.appDB)
    q = pd.read_sql_query(f"SELECT * FROM question WHERE qID = {input.qID()}",conn).iloc[0]
    conn.close() 
    #Update the UI
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
    #Get the original question
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    q = pd.read_sql_query("SELECT qID,question,answer,optionA,explanationA,optionB,explanationB,optionC,"
                          f"explanationC,optionD,explanationD FROM question WHERE qID = {input.qID()}",conn).iloc[0]
    qID = int(q.iloc[0])
    fields = ["rqQuestion", "rqCorrect","rqOA","rqOAexpl","rqOB","rqOBexpl","rqOC","rqOCexpl","rqOD","rqODexpl"]
    now = shared.dt()

    # Backup any changes
    updates = []
    for i, v in enumerate(fields):
        if input[v].get() != q.iloc[i+1]:
            shared.backupQuery(cursor, sessionID.get(), "question", qID, q.index[i+1], None, now)
            updates.append(f'{q.index[i+1]} = "{input[v].get()}"')
    # Update the question
    if updates != []:
        updates = ",".join(updates) + f', modified = "{now}"'
        cursor.execute(f"UPDATE question SET {updates} WHERE qID = {qID}")
        conn.commit()
        shared.modalMsg("Your edits were successfully saved", "Update complete")
    else:
        shared.modalMsg("No changes were detected")
    
    conn.close()
