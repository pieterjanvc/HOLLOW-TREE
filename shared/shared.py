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
from regex import search as re_search

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
vectorDB = config["localStorage"]["duckDB"]
sqliteDB = config["localStorage"]["sqliteDB"]

# Create the parent directory for the sqliteDB if it does not exist
if not os.path.exists(os.path.dirname(sqliteDB)):
    os.makedirs(os.path.dirname(sqliteDB))

# Do the same for the vectorDB
if not os.path.exists(os.path.dirname(vectorDB)):
    os.makedirs(os.path.dirname(vectorDB))


# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = config["LLM"]["gptModel"]
llm = OpenAI(model=gptModel)

if not os.path.exists(vectorDB) and not shared.remoteAppDB:
    raise ConnectionError("The vector database was not found. Please run ACCORNS first")

if os.environ["OPENAI_API_KEY"] is None:
    raise ValueError(
        "There is no OpenAI API key stored in the the OPENAI_API_KEY environment variable"
    )

# --- FUNCTIONS ---
def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def inputCheck(input):
    if re_search(r"(?=(.*[a-zA-Z0-9]){6,}).*", input):
        return True
    else:
        False

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
        if not os.path.exists(config["localStorage"]["sqliteDB"]):
            raise ConnectionError(
                "The app database was not found. Please run ACCORNS first"
            )
        return sqlite3.connect(config["localStorage"]["sqliteDB"])

# Check if the postgres scuirrel database is available when remoteAppDB is set to True
def checkRemoteDB():
    try:
        conn = appDBConn()
        conn.close()
        return "Connection to postgres scuirrel database successful"
    except psycopg2.OperationalError as e:
        raise psycopg2.OperationalError(
            str(e) + "\n\n POSTGRESQL connection error: "
            "Please check the postgres connection settings in config.toml "
            "and make sure POSTGRES_PASS_SCUIRREL is set as an environment variable."
        )
    
if remoteAppDB:
    print(shared.checkRemoteDB())

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
