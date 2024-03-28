# *********************************
# ----------- TUTORBOT -----------
# *********************************

# ----------- FUNCTIONS -----------
# *********************************

# General
import os
import sqlite3
from datetime import datetime
from html import escape
import pandas as pd
# Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate
# Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div

# Data Path (to be updated later)
dataPath = 'dataStores/test/' #Path do the folder for this Bot

def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Database to store app data (this is not the vector database!)
if not os.path.exists('appData/tutorBot.db'):
    #Create a new database 
    with open('appData/createDB.sql', 'r') as file:
        query = file.read().replace('\n', ' ').replace('\t', '').split(";")

    conn = sqlite3.connect('appData/tutorBot.db')
    cursor = conn.cursor()
    
    for x in query:
        _ = cursor.execute(x)
    
    #Add the anonymous user
    _ = cursor.execute('INSERT INTO user(username, creationDate)' 
                       f'VALUES("anonymous", "{dt()}")')
    
    #Add a test topic (to be removed later)
    topic = "The central dogma of molecular biology"
    _ = cursor.execute('INSERT INTO topic(topic)' 
                       f'VALUES("{topic}")')
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
    _ = cursor.executemany('INSERT INTO concept(tID, concept) ' 
                           f'VALUES({tID}, ?)', concepts)
    conn.commit()
    conn.close()

# --- Global variables

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = "gpt-3.5-turbo-0125" # use gpt-3.5-turbo-0125 or gpt-4

conn = sqlite3.connect('appData/tutorBot.db')
#cursor = conn.cursor()
topics = pd.read_sql_query("SELECT * FROM topic", conn)
conn.close()

# TUTORIAL Llamaindex
# https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb

# Use OpenAI LLM 
llm = OpenAI(model=gptModel) # use gpt-3.5-turbo-0125	or gpt-4

if not os.path.exists(dataPath + "vectorStore/default__vector_store.json"):
    # Build the vector store    
    data = SimpleDirectoryReader(input_dir= dataPath + "original").load_data()
    index = VectorStoreIndex.from_documents(data)
    index.storage_context.persist(persist_dir = dataPath + "vectorStore")
else:
    # Load the index from storage
    storage_context = StorageContext.from_defaults(persist_dir= dataPath + "vectorStore")
    index = load_index_from_storage(storage_context)

# ----------- SHINY APP -----------
# *********************************

# --- REACTIVE VARIABLES ---

sessionID = reactive.value(0)
discussionID = reactive.value(0)

@reactive.calc
def tID():
    return topics[topics["tID"] == 1].iloc[0]["tID"] # todo make user select topic

@reactive.calc
def concepts():
    conn = sqlite3.connect('appData/tutorBot.db')
    #cursor = conn.cursor()
    concepts = pd.read_sql_query(f"SELECT * FROM concept WHERE tID = {tID()}", conn)
    conn.close()
    return concepts


@reactive.calc
def welcome():
    return(('Hello, I\'m here to help you get a basic understanding of the following topic: '
           f'{topics[topics["tID"] == tID()].iloc[0]["topic"]}. Have you heard about this before?'))


with reactive.isolate():
    messages = reactive.value([(1, dt(), welcome())])
    userLog = reactive.value(f"""<div class='botChat talk-bubble tri'>
                            <p>Hello, I'm here to help you get a basic understanding of 
                            the following topic: <b>{topics[topics["tID"] == tID()].iloc[0]["topic"]}</b>. 
                            Have you heard about this before?</p></div>""")
    botLog = reactive.value(f"""---- PREVIOUS CONVERSATION ----\n--- YOU:\n{welcome()}""")

chatInput = reactive.value(ui.TagList(
    ui.input_text_area("newChat", "", value="", width="100%", 
                       spellcheck=True, resize=False), 
    ui.input_action_button("send", "Send")))


# --- REACTIVE FUNCTIONS ---

uID = 1 #if registered users update later

@reactive.calc
def chatEngine():

    # Prompt engineering
    # https://docs.llamaindex.ai/en/stable/examples/customization/prompts/chat_prompts/

    # The two strings below have not been altered from the defaults set by llamaindex, 
    # but can be if needed
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

    topicList = "* "+"\n* ".join([x[0] for x in concepts()["concept"]]) 

    # System prompt
    chat_text_qa_msgs = ([
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                f"""
                Your goal is to check wether the user (a student) has an understanding of the following topic: 
                {topics[topics["tID"] == tID()].iloc[0]["topic"]}
                ----
                These are the sub-concepts that the user should understand:
                {topicList}
                ----
                Remember that you are not lecturing, i.e. giving definitions or giving away all the concepts.
                Rather, you will ask a series of questions (or generate a multiple choice question if it fits) and look
                at the answers to refine your next question according to the current understanding of the user.
                Try to make the user think and reason critically, but do help out if they get stuck. 
                You will adapt the conversation until you feel all sub-concepts are understood.
                Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
                message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!
                """
            ),
    ),
    ChatMessage(role=MessageRole.USER, content=qa_prompt_str),
    ])
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                """
                Remember that you are not lecturing, i.e. giving definitions or giving away all the concepts.
                Rather, you will ask a series of questions (or generate a multiple choice question if it fits) and look
                at the answers to refine your next question according to the current understanding of the user.
                Try to make the user think and reason critically, but do help out if they get stuck. 
                You will adapt the conversation until you feel all sub-concepts are understood.
                Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
                message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!
                Finally, your output will be rendered as HTML, so format accordinly. Examples:
                    * Make important concepts bold using <b> </b> tags 
                    * Make a list of multiple choice questions using <ul> and <li> tags
                """
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return(
        index.as_query_engine(
            text_qa_template=text_qa_template,
            refine_template=refine_template,
            llm=llm,
            streaming = True
    )
    )

#When the send button is clicked...
@reactive.effect
@reactive.event(input.send, ignore_init=True)
def _():
    newChat = escape(input.newChat()) #prevent HTML injection from user
    if newChat == "": return
    msg = messages.get()    
    msg.append((False,dt(), newChat))
    messages.set(msg)
    botIn = botLog.get() + "\n---- NEW RESPONSE FROM USER ----\n" + newChat    
    userLog.set(userLog.get() + "<div class='userChat talk-bubble tri'><p>" + newChat + "</p></div>")
    botLog.set(botLog.get() + f"\n--- USER:\n{newChat}")   
    chatInput.set(HTML("<hr><i>The BioBot is thinking hard ...</i>"))
    botResponse(chatEngine(), botIn)

# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def botResponse(chatEngine, botIn):
    return str(chatEngine.query(botIn))

# Processing LLM response
@reactive.effect
def _():
    resp = botResponse.result()
    with reactive.isolate():
        userLog.set(userLog.get() +  
                    "<div class='botChat talk-bubble tri'><p>" + 
                    resp + "</p></div>")
        botLog.set(botLog.get() + "\n--- YOU:\n" + resp) 
    chatInput.set(ui.TagList(
        ui.input_text_area("newChat", "", value="", width="100%", 
                       spellcheck=True, resize=False),
        ui.input_action_button("send", "Send")))
    msg = messages.get()
    msg.append((True,dt(), resp))
    messages.set(msg)

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
    cursor.execute('INSERT INTO discussion (tID, sID, start)'
                   f'VALUES({tID()}, {sID}, "{dt()}")')
    dID = cursor.lastrowid
    sessionID.set(sID)
    discussionID.set(dID)
    conn.commit()
    conn.close()

    #Set the function to be called when the session ends
    dID = discussionID.get()
    msg = messages.get()
    _ = session.on_ended(lambda: theEnd(sID, dID, msg))

# Code to run at the end of the session (i.e. user disconnects)
def theEnd(sID, dID, msg):
    #Add logs to the database after user exits
    conn = sqlite3.connect('appData/tutorBot.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE session SET end = "{dt()}" WHERE sID = {sID}')
    cursor.execute(f'UPDATE discussion SET end = "{dt()}" WHERE dID = {dID}')
    cursor.executemany(f'INSERT INTO messages(dID,isBot,timeStamp,message)' 
                   f'VALUES({dID}, ?, ?, ?)', msg)
    conn.commit()
    conn.close()


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
    
    with ui.nav_panel("BMIbot"):

        # Render the chat window
        with ui.layout_columns():  
            with ui.card(id="chatWindow", height="70vh"):
                ui.card_header("Conversation")
                @render.ui
                def chatLog():    
                    return div(HTML(userLog.get()))

        #Render the text input (send button generated above)
        @render.ui
        def chatButton():
            return chatInput.get()

    with ui.nav_panel("Settings"):
        with ui.layout_columns(col_widths= 12):  
            with ui.card():
                ui.card_header("Concepts related to the topic")
                @render.data_frame
                def conceptsTable():
                    return render.DataTable(
                        concepts()[["concept"]], width="100%", row_selection_mode="single")
            
            div(ui.input_action_button("cAdd", "Add new", width= "180px"),
            ui.input_action_button("cEdit", "Edit selected", width= "180px"),
            ui.input_action_button("cDel", "Delete selected", width= "180px"), style = "display:inline")

@render.ui
def rows():
    rows = input.conceptsTable_selected_rows()  
    selected = ", ".join(str(i) for i in sorted(rows)) if rows else "None"
    print(f"Rows selected: {selected}")
