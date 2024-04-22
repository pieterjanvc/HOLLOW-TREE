# ************************************************
# ----------- SCUIRREL APP SHARED CODE -----------
# ************************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

# General
import os
import sqlite3
from datetime import datetime
import pandas as pd
import toml

# Llamaindex
from llama_index.core import VectorStoreIndex, ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore

# --- VARIABLES ---

with open("config.toml", "r") as f:
    config = toml.load(f)

appDB = config["data"]["appDB"]
vectorDB = config["data"]["vectorDB"]
allowMultiGuess = any(config["settings"]["allowMultiGuess"] == x for x in ["True", "true", "T", 1])

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = config["LLM"]["gptModel"]
llm = OpenAI(model=gptModel)

if not os.path.exists(appDB):
    raise ConnectionError(
        "The app database was not found. Please run the admin app first"
    )

if not os.path.exists(vectorDB):
    raise ConnectionError(
        "The vector database was not found. Please run the admin app first"
    )

if os.environ["OPENAI_API_KEY"] is None:
    raise ValueError(
        "There is no OpenAI API key stored in the the OPENAI_API_KEY environment variable"
    )

# Check if there are topics to discuss before proceeding
conn = sqlite3.connect(appDB)
topics = pd.read_sql_query(
    "SELECT * FROM topic WHERE archived = 0 AND tID IN"
    "(SELECT DISTINCT tID from concept WHERE archived = 0)",
    conn,
)

if topics.shape[0] == 0:
    raise ValueError(
        "There are no active topics with at least one concept in the database."
        " Please run the admin app first"
    )
conn.close()

# Load the vector index from storage
vector_store = DuckDBVectorStore.from_local(vectorDB)
index = VectorStoreIndex.from_vector_store(vector_store)


# --- FUNCTIONS ---
def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Adapt the chat engine to the topic
def chatEngine(topic,concepts,cIndex):
    # TUTORIAL Llamaindex + Prompt engineering
    # https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb
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

    cDone = "" if cIndex == 0 else "These concepts were already covered successfully:\n* " + \
    "\n* ".join(concepts.head(cIndex)["concept"])

    cToDo = "The following concepts still need to be discussed:\n* " + \
    "\n* ".join(concepts[cIndex:]["concept"])

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
f"""You (MENTOR) will chat with a student (STUDENT) to evaluate their understanding of the following topic: 
{topic}
----
{cDone}\n\n
{cToDo}
---- 

The current focus of the conversation should be on the following concept: 
{concepts.iloc[cIndex]["concept"]} 

Remember that you are not lecturing, i.e. giving / asking definitions or giving away all the concepts.
Rather, you will ask a series of questions and use the student's answers to refine your next question 
according to their current understanding.
Try to make the student think and reason critically, but do help out if they get stuck. 
You will adapt the conversation until you feel the there are no more mistakes and there is basic understanding of the concept.
Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!"""
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
If necessary, make edits to ensure the following:
- Do not keep repeating the topic title in your answer, focus on what's currently going on
- You should stay on topic, and make sure all sub-concepts are evaluated 
(but don't give them away accidentally!)
- If a user seems confused or does not know something, you should explain some of the theory 
in light of their current perceived knowledge
- Make sure you make the user think for themselves, but don't make it frustrating
- Double check if the latest user query does not contain conceptual or jargon errors and address them if needed
- You can add some fun facts based on the provided background if appropriate to keep the conversation
interesting 
"""
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=llm,
    )


# Adapt the chat engine to the topic
def progressCheckEngine(conversation,topic,concepts,cIndex):   

    cDone = "" if cIndex == 0 else "These concepts were already covered successfully:\n* " + \
    "\n* ".join(concepts.head(cIndex)["concept"])

    cToDo = "The following concepts still need to be discussed:\n* " + \
    "\n* ".join(concepts[cIndex:]["concept"])    

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
f"""You are monitoring a conversation between a tutor (TUTOR) and a student (STUDENT) on following topic:  
{topic}

{cDone}\n\n
{cToDo}

The conversation is currently focused on the following concept: 
{concepts.iloc[cIndex]["concept"]}

{conversation}

----

With this information, you have to decide if the STUDENT demonstrated enough understanding 
of the current concept to move on to the next one. 
You do this by outputting a numeric score with the following rubric:
* 1: No demonstration of understanding yet
* 2: Some understanding, but still incomplete or with mistakes warranting more discussion 
* 3: Basics of the concept seem to be understood and we might be able to move on
* 4: Clear demonstration of understanding

In addition you will add a short comment, based on the conversation and current concept, 
about what the STUDENT understands but more importantly what they still struggle with (if score < 4).

Please output your score in the following format:"""
r'{{"score": <int>, "comment": "<>"}}'
            ),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(r'Make sure the output is in the following format: {{"score": <int>, "comment": "<>"}}'),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=llm,
)