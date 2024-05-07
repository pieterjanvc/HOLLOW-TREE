# *********************************************************
# ----------- CODE SHARED BY SCUIRREL & ACCORNS -----------
# *********************************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

# General
import os
import sqlite3
import psycopg2
from datetime import datetime
import pandas as pd
import toml
import warnings

# Llamaindex
from llama_index.core import VectorStoreIndex
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore

from shared import shared

# --- VARIABLES ---

with open("shared/shared_config.toml", "r") as f:
    config = toml.load(f)

remoteAppDB = any(
    config["general"]["remoteAppDB"] == x for x in ["True", "true", "T", 1]
)
vectorDB = config["localStorage"]["vectorDB"]

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = config["LLM"]["gptModel"]
llm = OpenAI(model=gptModel)

if not os.path.exists(vectorDB) & shared.remoteAppDB:
    raise ConnectionError("The vector database was not found. Please run ACCORNS first")

if os.environ["OPENAI_API_KEY"] is None:
    raise ValueError(
        "There is no OpenAI API key stored in the the OPENAI_API_KEY environment variable"
    )

# Load the vector index from storage
vector_store = DuckDBVectorStore.from_local(vectorDB)
index = VectorStoreIndex.from_vector_store(vector_store)


# --- FUNCTIONS ---
def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Get a local or remote DB connection (depending on config)
def appDBConn(remoteAppDB=remoteAppDB):
    if remoteAppDB:
        return psycopg2.connect(
            host=config["postgres"]["host"],
            user=config["postgres"]["username"],
            password=os.environ.get("POSTGRES_PASS_SCUIRREL"),
            database=config["postgres"]["db"],
        )

    else:
        if not os.path.exists(config["localStorage"]["appDB"]):
            raise ConnectionError(
                "The app database was not found. Please run ACCORNS first"
            )
        return sqlite3.connect(config["localStorage"]["appDB"])


def executeQuery(cursor, query, params=(), lastRowId="", remoteAppDB=remoteAppDB):
    query = query.replace("?", "%s") if remoteAppDB else query
    query = (
        query + f' RETURNING "{lastRowId}"'
        if remoteAppDB & (lastRowId != "")
        else query
    )

    if isinstance(params, tuple):
        cursor.execute(query, params)
    else:
        if len(params) > 1:
            cursor.executemany(query, params[:-1])
        cursor.execute(query, params[-1])

    if lastRowId != "":
        if remoteAppDB:
            return cursor.fetchone()[0]
        else:
            return cursor.lastrowid

    return


def pandasQuery(conn, query):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.read_sql_query(query, conn)
