# ***********************************************
# ----------- Global App Vars / Funcs -----------
# ***********************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

# General
import os
import sqlite3
from datetime import datetime
import pandas as pd

# Llamaindex
from llama_index.core import VectorStoreIndex
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore

# --- VARIABLES ---

appDB = "appData/appDB.db"
vectorDB = "appData/vectordb.duckdb"
# Get the OpenAI API key and organistation from the enviroment
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = "gpt-3.5-turbo-0125"  # use gpt-3.5-turbo-0125 or gpt-4
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
