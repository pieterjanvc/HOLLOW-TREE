#------ BOT LOGIC
# TUTORIAL
# https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb

import os
import sqlite3
from datetime import datetime
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI

# DATA
dataPath = 'dataStores/test/' #Path do the folder for this Bot

def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Database to store app data (this is not the vector database!)
if not os.path.exists('tutorBot.db'):
    #Create a new database 
    with open('createDB.sql', 'r') as file:
        query = file.read().replace('\n', ' ').replace('\t', '').split(";")

    conn = sqlite3.connect('tutorBot.db')
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

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")

# Use OpenAI LLM 
llm = OpenAI(model="gpt-3.5-turbo-0125") # use gpt-3.5-turbo-0125	or gpt-4

if not os.path.exists(dataPath + "vectorStore/default__vector_store.json"):
    # Build the vector store    
    data = SimpleDirectoryReader(input_dir= dataPath + "original").load_data()
    index = VectorStoreIndex.from_documents(data)
    index.storage_context.persist(persist_dir = dataPath + "vectorStore")
else:
    # Load the index from storage
    storage_context = StorageContext.from_defaults(persist_dir= dataPath + "vectorStore")
    index = load_index_from_storage(storage_context)

# Prompt engineering
# https://docs.llamaindex.ai/en/stable/examples/customization/prompts/chat_prompts/

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate

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

# Get the topic and concepts form the DB
conn = sqlite3.connect('tutorBot.db')
cursor = conn.cursor()
tID = 1 #later chosen by user
topic = cursor.execute(f'SELECT topic FROM topic WHERE tID = {tID}')\
    .fetchall()[0][0]
concepts = cursor.execute(f'SELECT concept FROM concept WHERE tID = {tID}')\
    .fetchall()
concepts = "* "+"\n* ".join([x[0] for x in concepts])
conn.close()

chat_text_qa_msgs = [
    ChatMessage(
        role=MessageRole.SYSTEM,
        content=(
            f"""
            Your goal is to check wether the user (a student) has an understanding of the following topic: 
            '{topic}'
            ----
            These are the sub-concepts that the user should understand:
            {concepts}
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
]
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

chat_engine = index.as_query_engine(
            text_qa_template=text_qa_template,
            refine_template=refine_template,
            llm=llm,
            streaming = True
        )

# ------- SHINY APP
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div

sessionID = reactive.value(0)
messages = reactive.value([])

userLog = reactive.value(f"""<h4 style='color:#236ba6'>--- BioBot:</h4>
                         <p style='color:#236ba6'>Hello, I'm here to help you get a basic understanding of 
                         the following topic: <b>{topic}</b>. Have you heard about this before?</p>""")

botLog = reactive.value(f"""---- PREVIOUS CONVERSATION ----\n--- YOU:\nHello, I'm here to help 
                        you get a basic understanding of the following topic: '{topic}'. 
                        Have you heard about this before?""")

chatInput = reactive.value(ui.TagList(
    ui.tags.hr(), 
    ui.input_text("newChat", "", value="", width="100%", spellcheck=True), 
    ui.input_action_button("send", "Send")))

@reactive.effect
@reactive.event(input.send, ignore_init=True)
def _():
    #print("Process new input")
    if input.newChat() == "": return
    msg = messages.get()
    msg.append((False,dt(), input.newChat()))
    messages.set(msg)
    botIn = botLog.get() + "\n---- NEW RESPONSE FROM USER ----\n" + input.newChat()    
    userLog.set(userLog.get() + "<h4 style='color:#A65E23'>--- YOU:</h4><p style='color:#A65E23'>" + input.newChat() + "</p>")
    botLog.set(botLog.get() + f"\n--- USER:\n{input.newChat()}")   
    #ui.update_text("newChat", value = "")
    chatInput.set(HTML("<hr><i>The BioBot is thinking hard ...</i>"))
    botResponse(botIn)

@reactive.extended_task
async def botResponse(botIn):
    #print("Get botResponse")
    return str(chat_engine.query(botIn))

@reactive.effect
def _():
    #print("Update logs")
    x = botResponse.result()
    with reactive.isolate():
        userLog.set(userLog.get() +  "<h4 style='color:#236ba6'>--- BioBot:</h4><p style='color:#236ba6'>" + x + "</p>")
        botLog.set(botLog.get() + "\n--- YOU:\n" + x) 
    chatInput.set(ui.TagList(
        ui.tags.hr(), 
        ui.input_text("newChat", "", value="", width="100%", spellcheck=True),
        ui.input_action_button("send", "Send")))
    msg = messages.get()
    msg.append((True,dt(), msg))
    messages.set(msg)

@reactive.effect
def _():
    #Register the session in the DB at start
    conn = sqlite3.connect('tutorBot.db')
    cursor = conn.cursor()
    #For now we only have anonymous users
    cursor.execute('INSERT INTO session (shinyToken, uID, start)'
                   f'VALUES("{session.id}", 1, "{dt()}")')
    sessionID.set(cursor.lastrowid)
    conn.commit()
    conn.close()

    #Set the function to be called when the session ends
    sID = sessionID.get()
    msg = messages.get()
    _ = session.on_ended(lambda: theEnd(sID, msg))

def theEnd(sID, msg):
    #Add logs to the database after user exits
    conn = sqlite3.connect('tutorBot.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE session SET end = "{dt()}" WHERE sID = {sID}')
    #For now we only have anonymous users
    cursor.execute(f'UPDATE session SET end = "{dt()}" WHERE sID = {sID}')
    conn.commit()
    conn.close()
    return "Session ended"

#---- Rendering the UI
@render.ui
def chatLog():    
    return HTML(userLog.get())

@render.ui
def chatButton():
    return chatInput.get()

# Add some JS so that enter can send the message too
ui.head_content(
    HTML("""<script>
         $(document).keyup(function(event) {
            if ($("#newChat").is(":focus") && (event.key == "Enter")) {
                $("#send").click();
            }
        });
         </script>""")
)
