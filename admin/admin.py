# **************************************
# ----------- TUTORBOT ADMIN -----------
# **************************************

# ----------- FUNCTIONS -----------
# *********************************

# General
import os
import sqlite3
from datetime import datetime
import pandas as pd
import regex as re
# Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore
# Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div

def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def inputCheck(input):
    if re.search(r"(?=(.*[a-zA-Z0-9]){6,}).*", input):
        return True
    else:
        False

# Database to store app data (this is not the vector database!)
if not os.path.exists('appData/tutorBot.db'):
    #Create a new database 
    with open('appData/createDB.sql', 'r') as file:
        query = file.read().replace('\n', ' ').replace('\t', '').split(";")

    conn = sqlite3.connect('appData/tutorBot.db')
    cursor = conn.cursor()
    
    for x in query:
        _ = cursor.execute(x)
    
    #Add the anonymous user and main admin
    _ = cursor.execute('INSERT INTO user(username, isAdmin, created)' 
                       f'VALUES("anonymous", 0, "{dt()}"), ("admin", 1, "{dt()}")')
    
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

# --- Global variables

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = "gpt-3.5-turbo-0125" # use gpt-3.5-turbo-0125 or gpt-4

conn = sqlite3.connect('appData/tutorBot.db')
topics = pd.read_sql_query("SELECT * FROM topic", conn)
conn.close()

# TUTORIAL Llamaindex
# https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb

# Use OpenAI LLM 
llm = OpenAI(model=gptModel) # use gpt-3.5-turbo-0125	or gpt-4

if not os.path.exists("appData/vectorStore.duckdb"):
    # Build the vector store https://docs.llamaindex.ai/en/stable/module_guides/loading/simpledirectoryreader/   
    data = SimpleDirectoryReader(input_dir= "appData/uploadedFiles").load_data()
    vector_store = DuckDBVectorStore(1536, "vectorStore.duckdb", persist_dir= "appData/")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    #Generate the first index
    index = VectorStoreIndex.from_documents(data, storage_context=storage_context,
                                            transformations=[TitleExtractor(), KeywordExtractor()])
else:
    # Load the exisiting index from storage
    #vector_store = DuckDBVectorStore(embed_dim=1536).from_local("appData/vectorStore.duckdb")
    vector_store = DuckDBVectorStore(1536, "vectorStore.duckdb", persist_dir= "appData/")
    index = VectorStoreIndex.from_vector_store(vector_store)

# ----------- SHINY APP -----------
# *********************************

uID = 2 #if registered users update later

# --- REACTIVE VARIABLES ---

sessionID = reactive.value(0)

# Workaround until issue with reactive.cals is resolved
# https://github.com/posit-dev/py-shiny/issues/1271
conn = sqlite3.connect('appData/tutorBot.db')
concepts = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = 0", conn)
conn.close()
concepts = reactive.value(concepts)

# --- REACTIVE FUNCTIONS ---

# Code to run at the start of the session (i.e. user connects)
@reactive.effect
def _():
    #Register the session in the DB at start
    conn = sqlite3.connect('appData/tutorBot.db')
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
    conn = sqlite3.connect('appData/tutorBot.db')
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
    conn = sqlite3.connect('appData/tutorBot.db')
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
#     conn = sqlite3.connect('appData/tutorBot.db')
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

    conn = sqlite3.connect('appData/tutorBot.db')
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
    conn = sqlite3.connect('appData/tutorBot.db')
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
    conn = sqlite3.connect('appData/tutorBot.db')
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
    conn = sqlite3.connect('appData/tutorBot.db')
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
    conn = sqlite3.connect('appData/tutorBot.db')
    conceptList = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = {tID} AND archived = 0", conn)
    conn.close()
    concepts.set(conceptList)

# --- RENDERING UI ---
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
        "test"
