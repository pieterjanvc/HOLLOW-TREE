# *********************************************************
# ----------- CODE SHARED BY SCUIRREL & ACCORNS -----------
# *********************************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

# General
import os
import sqlite3
import duckdb
import psycopg2
from datetime import datetime
import pandas as pd
import toml
import warnings
from regex import search as re_search

# Llamaindex
from llama_index.llms.openai import OpenAI

# --- VARIABLES ---

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

with open(os.path.join(curDir, "shared_config.toml"), "r") as f:
    config = toml.load(f)

remoteAppDB = any(
    config["general"]["remoteAppDB"] == x for x in ["True", "true", "T", 1]
)
postgresHost = config["postgres"]["host"]
postgresPort = int(config["postgres"]["port"])
vectorDB = config["localStorage"]["duckDB"]
sqliteDB = config["localStorage"]["sqliteDB"]
postgresUser = None # Each app will set this variable to the correct user

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
def appDBConn(postgresUser=postgresUser, remoteAppDB=remoteAppDB):
    if remoteAppDB:
        return psycopg2.connect(
            host=postgresHost,
            user=postgresUser,
            password=os.environ.get("POSTGRES_PASS_" + ("SCUIRREL" if postgresUser == "scuirrel" else "ACCORNS")),
            database="accorns",
        )

    else:
        if not os.path.exists(config["localStorage"]["sqliteDB"]):
            raise ConnectionError(
                "The app database was not found. Please run ACCORNS first"
            )
        return sqlite3.connect(config["localStorage"]["sqliteDB"])

def vectorDBConn(postgresUser=postgresUser, remoteAppDB = remoteAppDB, vectorDB = vectorDB):
    if remoteAppDB:
        conn = psycopg2.connect(
                host=postgresHost,
                port=postgresPort,
                user=postgresUser,
                password=os.environ.get("POSTGRES_PASS_" + ("SCUIRREL" if postgresUser == "scuirrel" else "ACCORNS")),
                database="vector_db",
            )
    else:    
        conn = duckdb.connect(vectorDB)
    
    return conn

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

# Check if the postgres scuirrel database is available when remoteAppDB is set to True
def checkRemoteDB():
    try:
        conn = appDBConn("accorns")
        cursor = conn.cursor()
        _ = executeQuery(cursor, 'SELECT 1 FROM "session"')
        conn.close()

        conn = vectorDBConn("accorns")
        cursor = conn.cursor()
        _ = executeQuery(cursor, 'SELECT 1 FROM "file"')
        conn.close()

        return "Connections to postgres accorns and vector database successful"
    
    except psycopg2.OperationalError as e:
        raise psycopg2.OperationalError(
            str(e) + "\n\n POSTGRESQL connection error: "
            "Please check the postgres connection settings in config.toml "
            "and make sure POSTGRES_PASS_SCUIRREL and POSTGRES_PASS_SCUIRREL are set as an environment variables."
        )
    
if remoteAppDB:
    print(checkRemoteDB())
