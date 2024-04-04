# **************************************
# ----------- TUTORBOT ADMIN -----------
# **************************************

# -- General
import os
import sqlite3
from datetime import datetime
import pandas as pd
import regex as re
import duckdb
import json
from shutil import move
# -- Llamaindex
# pip install llama-index
# pip install llama-index-vector-stores-duckdb
# pip install llama-index-llms-openai
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore
# -- Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div

# The following is needed to prevent async issues when inserting new data in vector DB
# https://github.com/run-llama/llama_index/issues/9978
import nest_asyncio 
nest_asyncio.apply()

# --- Global variables

appDB = "appData/tutorBot.db"
vectorDB = "appData/vectorStore.duckdb"
storageFolder = "appData/uploadedFiles/" #keep files user uploads, if set to None, original not kept
uID = 2 #if registered admins make reactive later

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = "gpt-3.5-turbo-0125" # use gpt-3.5-turbo-0125 or gpt-4

# Use OpenAI LLM from Llamaindex 
llm = OpenAI(model=gptModel)

# ----------- FUNCTIONS -----------
# *********************************

def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def inputCheck(input):
    if re.search(r"(?=(.*[a-zA-Z0-9]){6,}).*", input):
        return True
    else:
        False

# Database to store app data (this is not the vector database!)
def createAppDB(DBpath, sqlFile = "appData/createDB.sql", addDemo = True):
    
    if os.path.exists(DBpath):
        return (1, "Database already exists. Skipping")
    
    #Create a new database from the SQL file
    with open(sqlFile, 'r') as file:
        query = file.read().replace('\n', ' ').replace('\t', '').split(";")

    conn = sqlite3.connect(DBpath)
    cursor = conn.cursor()
    
    for x in query:
        _ = cursor.execute(x)
    
    #Add the anonymous user and main admin
    _ = cursor.execute('INSERT INTO user(username, isAdmin, created)' 
                       f'VALUES("anonymous", 0, "{dt()}"), ("admin", 1, "{dt()}")')
    
    if not addDemo:
        conn.commit()
        conn.close()
        return
    
    #Add a test topic (to be removed later)
    topic = "The central dogma of molecular biology"
    _ = cursor.execute('INSERT INTO topic(topic, created)' 
                       f'VALUES("{topic}", "{dt()}")')
    tID = cursor.lastrowid
    
    #Add topic concepts (to be removed later)
    concepts = [
        ('DNA is made up of 4 bases that encode all information needed for life',),
        ('A protein is encoded in the DNA as a seqeunce of bases',),
        ('To create a protein, you first have to transcribe the DNA into RNA',),
        ('RNA is similar to DNA but instead of ACTG it has ACUG and is single stranded',),
        ('RNA is processed by removing introns, keeping only exons',),
        ('RNA is translated into protein. 3 RNA bases form a codon, and each codon)' 
        'represents an amino acid, or the start / stop of the seqeunce',),
        ('Based on RNA codons, amino acids are chained together into a single protrein strand',),
        ('The protein will fold into a 3D shape to become functional,' 
        'with optional post-translational processing',)
    ]
    _ = cursor.executemany('INSERT INTO concept(tID, concept, created) ' 
                           f'VALUES({tID}, ?, "{dt()}")', concepts)
    conn.commit()
    conn.close()

    return (0, "Creation completed")

# newFile = "appData/Central_dogma_of_molecular_biology.pdf"
# newFile = "appData/Mendelian inheritance.txt"
# vectorDB = "appData/testDB.duckdb"
# appDB = "appData/appDB.db"
# storageFolder = "appData/uploadedFiles"
# newFileName = None

# Create DuckDB vector database and add files
def addFileToDB(newFile, vectorDB, appDB, storageFolder = None, newFileName = None):

    if not os.path.exists(appDB):
        raise ConnectionError("The appDB was not found")
    
    if not os.path.exists(newFile):
        raise ConnectionError(f"The newFile was not found at {newFile}")
    
    # Move the file to permanent storage if requested
    if storageFolder is not None:
        if not os.path.exists(storageFolder):
            os.makedirs(storageFolder)
        
        newFileName = os.path.basename(newFile) if newFileName is None else newFileName        
        newFilePath = os.path.join(storageFolder, '') + newFileName

        if os.path.exists(newFilePath):
            return (1, "A file with this name already exists. Skipping")

        move(newFile, newFilePath)
        newFile = newFilePath
    
    newData = SimpleDirectoryReader(input_files=[newFile]).load_data()

    # Build the vector store https://docs.llamaindex.ai/en/stable/examples/vector_stores/DuckDBDemo/?h=duckdb
    if os.path.exists(vectorDB):
        vector_store = DuckDBVectorStore.from_local(vectorDB)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(newData, storage_context = storage_context, 
                                                transformations=[TitleExtractor(), KeywordExtractor()])
    else:                  
        vector_store = DuckDBVectorStore(os.path.basename(vectorDB), persist_dir = os.path.dirname(vectorDB))
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(newData, storage_context = storage_context, 
                                                transformations=[TitleExtractor(), KeywordExtractor()])
    
    #Get the metadata out of the DB excerpt_keywords document_title
    fileName = newData[0].metadata["file_name"]
    #vectorDB = "appData/vectorstore.duckdb"
    con = duckdb.connect(vectorDB)
    #con.query("SELECT metadata_ FROM documents").fetchall()
    x = con.query(f'SELECT metadata_ ->> [\'document_title\', \'excerpt_keywords\'] FROM documents WHERE CAST(json_extract(metadata_, \'$.file_name\') as VARCHAR) = \'"{fileName}"\'').fetchall()
    con.close()

    chunkTitles = "* " + "\n* ".join(set([y[0][0] for y in x]))
    chunkKeywords = ", ".join(set((", ".join([y[0][1] for y in x])).split(", ")))    

    #Summarise everything using the LLM and add it to the DB
    docSum = ("Below is a list of subheadings belonging to the same document."
          f"Note that many of them might be near identical:\n\n{chunkTitles}"
          f"\n\nYou also get a list of keywords describing the same content:\n\n{chunkKeywords}"
          "\n\nAgain note that some key words are very related.\n"
          "Your task is to summarize all of this into a single, succinct short title, a subtitle, "
          "and a list of the top-10 keywords. Stay as close to the original titles as possible."
          " The output should be in the following valid JSON format: \n\n"
          '{"title": "", "subtitle": "", "keywords": []}')
    docSum = json.loads(str(index.as_query_engine().query(docSum)))

    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    _ = cursor.execute(('INSERT INTO file(fileName, title, subtitle, created) '
                       f'VALUES("{fileName}", "{docSum["title"]}", "{docSum["subtitle"]}", "{dt()}")'))
    fID = cursor.lastrowid
    _ = cursor.executemany('INSERT INTO keyword(fID, keyword) ' 
                           f'VALUES("{fID}", ?)', [(item,) for item in docSum["keywords"]])
    conn.commit()
    conn.close()

    return (0, "Completed")

# ----------- SHINY APP -----------
# *********************************

#Make new app DB if needed
print(createAppDB(appDB, addDemo = True))

# --- UI COMPONENTS ---
uiUploadFile = div(ui.input_file(
    "newFile", "Pick a file", width="100%",
    accept=[".csv", ".pdf", ".docx", ".txt", ".md", ".epub", ".ipynb", ".ppt", ".pptx"]), id="uiUploadFile")

# --- REACTIVE VARIABLES ---

sessionID = reactive.value(0)

# Workaround until issue with reactive.cals is resolved
# https://github.com/posit-dev/py-shiny/issues/1271
conn = sqlite3.connect(appDB)
concepts = pd.read_sql_query("SELECT * FROM concept WHERE tID = 0", conn)
files = pd.read_sql_query("SELECT * FROM file", conn)
conn.close()

concepts = reactive.value(concepts)
files = reactive.value(files)

# --- REACTIVE FUNCTIONS ---

# Code to run at the start of the session (i.e. user connects)
@reactive.effect
def _():

    #Register the session in the DB at start    
    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    #For now we only have anonymous users
    cursor.execute('INSERT INTO session (shinyToken, uID, start)'
                   f'VALUES("{session.id}", {uID}, "{dt()}")')
    sID = cursor.lastrowid
    sessionID.set(sID)
    topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()
    #Update the topics select input
    ui.update_select("tID", choices= dict(zip(topics["tID"], topics["topic"])))

    #Set the function to be called when the session ends
    _ = session.on_ended(lambda: theEnd(sID))

# Code to run at the end of the session (i.e. user disconnects)
def theEnd(sID):
    #Add logs to the database after user exits
    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    cursor.execute(f'UPDATE session SET end = "{dt()}" WHERE sID = {sID}')
    conn.commit()
    conn.close()

# ---- TOPICS ----

# --- Add a new topic
@reactive.effect
@reactive.event(input.tAdd)
def addTopic_modal():
    m = ui.modal(  
        ui.tags.p(HTML('<i>Keep the topic name short.<br>'
                  'Make sure the topic can be covered by ~ 4-8 concepts, otherwise split it up.'
                  'The AI might struggle with broad topics that cover many concepts</i>')),
        ui.input_text("ntTopic", "New topic:", width="100%"),
        ui.input_text("ntDescr", "Description (optional):", width="100%"),
        ui.input_action_button("ntAdd", "Add"),
        title="Add a topic",  
        easy_close=True,
        size = "l",  
        footer=None,  
    )  
    ui.modal_show(m)

@reactive.effect  
@reactive.event(input.ntAdd)  
def addNewTopic():
    #Only proceed if the input is valid
    if not inputCheck(input.ntTopic()):
        ui.remove_ui("#notGood")
        ui.insert_ui(HTML("<div id=notGood style='color: red'>New topic must be at least 6 characters</div>"), 
                     "#ntAdd", "afterEnd")
        return
    
    #Add new topic to DB
    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO topic(topic, created, description)'
                   f'VALUES("{input.ntTopic()}", "{dt()}", "{input.ntDescr()}")')
    tID = cursor.lastrowid
    topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    conn.commit()
    conn.close()
    # Update the topic list
    ui.update_select("tID", choices=dict(zip(topics["tID"], topics["topic"])), selected= tID)
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
#     conn = sqlite3.connect(appDB)
#     cursor = conn.cursor()
#     cursor.execute(f'UPDATE concept SET concept = "{input.ecInput()}", '
#                    f'modified = "{dt()}" WHERE cID = {cID}')
#     conn.commit()
#     conn.close()

#     ui.modal_remove()    

# --- Archive a topic
@reactive.effect
@reactive.event(input.tArchive)
def _():
    if input.tID() is None: return

    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    cursor.execute('UPDATE topic SET archived = 1, '
                   f'modified = "{dt()}" WHERE tID = {input.tID()}')
    topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
    
    ui.update_select("tID", choices=dict(zip(topics["tID"], topics["topic"])))

    #Empty the concept table is last topic was removed
    if topics.shape[0] == 0:
        conceptList = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = 0", conn)        
        concepts.set(conceptList)
    
    conn.commit()
    conn.close()


# ---- CONCEPTS ----
    
# --- Add a new concepts
@reactive.effect
@reactive.event(input.cAdd)
def _():
    m = ui.modal(  
        ui.tags.p(HTML('<i>Concepts are single facts that a student should understand<br>'
                  'There is no need to provide context as this will come from the database</i>')),
        ui.input_text("ncInput", "New concept:", width="100%"),
        ui.input_action_button("ncAdd", "Add"),
        title="Add a new concept to the topic",  
        easy_close=True,
        size = "l",  
        footer=None,  
    )  
    ui.modal_show(m)

@reactive.effect  
@reactive.event(input.ncAdd)  
def _():
    #Only proceed if the input is valid
    if not inputCheck(input.ncInput()):
        ui.remove_ui("#notGood")
        ui.insert_ui(HTML("<div id=notGood style='color: red'>New concept must be at least 6 characters</div>"), 
                     "#ncAdd", "afterEnd")
        return
    
    #Add new topic to DB
    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO concept(tID, concept, created)'
                   f'VALUES({input.tID()}, "{input.ncInput()}", "{dt()}")')
    conceptList = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn) 
    conn.commit()       
    conn.close()
    #Update concept table
    concepts.set(conceptList)
    ui.modal_remove()


# --- Edit an existing concepts
@reactive.effect
@reactive.event(input.cEdit)
def _():
    if input.conceptsTable_selected_rows() != ():   
        concept = concepts.get().iloc[input.conceptsTable_selected_rows()]["concept"]
        m = ui.modal(  
            ui.tags.p(HTML('<i>Make sure to only make edits that do not change the concept. '
                        'Otherwise add or delete instead</i>')),
            ui.input_text("ecInput", "New concept:", width="100%", value = concept),
            ui.input_action_button("ncEdit", "Update"),
            title="Edit and existing topic",  
            easy_close=True,
            size = "l",  
            footer=None,  
        )  
        ui.modal_show(m)

@reactive.effect  
@reactive.event(input.ncEdit)  
def _():
    #Only proceed if the input is valid
    if not inputCheck(input.ecInput()):
        ui.remove_ui("#notGood")
        ui.insert_ui(HTML("<div id=notGood style='color: red'>A concept must be at least 6 characters</div>"), 
                     "#ncEdit", "afterEnd")
        return
    
    #Edit topic in DB
    cID = concepts.get().iloc[input.conceptsTable_selected_rows()]["cID"]
    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    cursor.execute(f'UPDATE concept SET concept = "{input.ecInput()}", '
                   f'modified = "{dt()}" WHERE cID = {cID}')
    conceptList = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn)
    conn.commit()
    conn.close()
    #Update concept table
    concepts.set(conceptList)
    ui.modal_remove()  

# --- delete a concept (archive)
@reactive.effect
@reactive.event(input.cArchive)
def _():
    if input.conceptsTable_selected_rows() == (): return

    cID = concepts.get().iloc[input.conceptsTable_selected_rows()]["cID"]
    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    cursor.execute('UPDATE concept SET archived = 1, '
                   f'modified = "{dt()}" WHERE cID = {cID}')
    conceptList = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = {input.tID()} AND archived = 0", conn)
    conn.commit()
    conn.close()

    concepts.set(conceptList)

@reactive.effect
@reactive.event(input.tID)
def _():
    
    tID = input.tID() if input.tID() else 0
    conn = sqlite3.connect(appDB)
    conceptList = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = {tID} AND archived = 0", conn)
    conn.close()
    concepts.set(conceptList)


# ---- VECTOR DATABASE ----

@reactive.effect
@reactive.event(input.newFile, ignore_init=True)
def _():
    #Move the file to the uploadedFiles folder
    updateVectorDB(input.newFile()[0]["datapath"], vectorDB, appDB, storageFolder, 
                input.newFile()[0]["name"])
    ui.insert_ui(HTML(f'<div id=processFile><i>Processing {input.newFile()[0]["name"]}</i></div>'), 
                 "#uiUploadFile", "afterEnd")
    ui.remove_ui("#uiUploadFile")



@reactive.extended_task
async def updateVectorDB(newFile, vectorDB, appDB, storageFolder, newFileName):
    print("Start adding file...")
    return addFileToDB(newFile, vectorDB, appDB, storageFolder, newFileName)

@reactive.effect
def _():
    insertionResult = updateVectorDB.result()[0]
    msg = "File succesfully added to the vector database" if \
        insertionResult == 0 else "A file with the same name already exists. Skipping upload"
    ui.modal_show(
        ui.modal(msg, title="Success" if insertionResult == 0 else "Issue")
    )
    conn = sqlite3.connect(appDB)
    getFiles = pd.read_sql_query("SELECT * FROM file", conn)
    files.set(getFiles)
    conn.close()
    ui.insert_ui(uiUploadFile, "#processFile", "afterEnd")
    ui.remove_ui("#processFile")


# --- RENDERING UI ---
#**********************
    
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

        with ui.layout_columns(col_widths= 12): 
            with ui.card():
                ui.card_header("Topic")
                div(
                    ui.input_action_button("tAdd", "Add new", width= "180px"),
                    ui.input_action_button("tArchive", "Archive selected", width= "180px")
                )
                ui.input_select("tID", "Pick a topic", choices=[], width="400px")                
            
            with ui.card():
                ui.card_header("Concepts related to the topic")
                HTML('<i>Concepts are facts or pieces of information you want the Bot to check with your students.'
                     'You can be very brief, as all context will be retrieved from the database of documents. '
                     'Don\'t be too broad, as this might cause confusion (you\'ll have to test it). '
                     'Try to limit the number of concepts to 4 - 8 as the AI might preform worse with a large number</i>')
                div(ui.input_action_button("cAdd", "Add new", width= "180px"),
                ui.input_action_button("cEdit", "Edit selected", width= "180px"),
                ui.input_action_button("cArchive", "Archive selected", width= "180px"), style = "display:inline")
                @render.data_frame
                def conceptsTable():
                    return render.DataTable(
                        concepts.get()[["concept"]], width="100%", row_selection_mode="single")                

    with ui.nav_panel("Vector Database"):
        with ui.card():
                ui.card_header("Vector database files")
                @render.data_frame
                def filesTable():
                    return render.DataTable(
                        files.get(), width="100%", row_selection_mode="single")
                
        with ui.card():
                ui.card_header("Upload a new file")
                uiUploadFile

