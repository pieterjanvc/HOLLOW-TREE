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
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore

# Shiny
from shiny import reactive

# --- VARIABLES ---

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

with open(os.path.join(curDir, "shared_config.toml"), "r") as f:
    config = toml.load(f)

remoteAppDB = any(
    config["general"]["remoteAppDB"] == x for x in ["True", "true", "T", 1]
)
addDemo = any(
    config["general"]["addDemo"] == x for x in ["True", "true", "T", 1]
)
demoFile = "https://github.com/pieterjanvc/seq2mgs/files/14964109/Central_dogma_of_molecular_biology.pdf"
postgresHost = config["postgres"]["host"]
postgresPort = int(config["postgres"]["port"])
vectorDB = os.path.normpath(config["localStorage"]["duckDB"])
sqliteDB = os.path.normpath(config["localStorage"]["sqliteDB"])
postgresAccorns = "accorns"
postgresScuirrel = "scuirrel"

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

# Get the current date and time in the format "YYYY-MM-DD HH:MM:SS"
def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Check if the input is of sufficient length
def inputCheck(input):
    if re_search(r"(?=(.*[a-zA-Z0-9]){6,}).*", input):
        return True
    else:
        False

# This function allows you to hide/show/disable/enable elements by ID or data-value
    # The latter is needed because tabs don't use ID's but data-value
def elementDisplay(id, effect, session, alertNotFound=True):
    id = session.ns + '-' + id if session.ns != '' else id

    @reactive.effect    
    async def _():        
        await session.send_custom_message("hideShow", {"id": id, "effect": effect, "alertNotFound": alertNotFound})

# Get a local or remote DB connection (depending on config)
def appDBConn(postgresUser, remoteAppDB=remoteAppDB):
    if remoteAppDB:
        return psycopg2.connect(
            host=postgresHost,
            user=postgresUser,
            password=os.environ.get(
                "POSTGRES_PASS_"
                + ("SCUIRREL" if postgresUser == postgresScuirrel else "ACCORNS")
            ),
            database="accorns",
        )

    else:
        if not os.path.exists(config["localStorage"]["sqliteDB"]):
            raise ConnectionError(
                "The app database was not found. Please run ACCORNS first"
            )
        return sqlite3.connect(config["localStorage"]["sqliteDB"])

# Connect to the vector database
def vectorDBConn(postgresUser, remoteAppDB=remoteAppDB, vectorDB=vectorDB):
    if remoteAppDB:
        conn = psycopg2.connect(
            host=postgresHost,
            port=postgresPort,
            user=postgresUser,
            password=os.environ.get(
                "POSTGRES_PASS_"
                + ("SCUIRREL" if postgresUser == postgresScuirrel else "ACCORNS")
            ),
            database="vector_db",
        )
    else:
        conn = duckdb.connect(vectorDB)

    return conn

# Get the current vector database index
def getIndex(user, postgresUser, remote = remoteAppDB):
    if remote:
            vectorStore = PGVectorStore.from_params(
                host=postgresHost,
                port=postgresPort,
                user=user,
                password=os.environ.get(
                "POSTGRES_PASS_"
                + ("SCUIRREL" if postgresUser == postgresScuirrel else "ACCORNS")
                ),
                database="vector_db",
                table_name="document",
                embed_dim=1536,  # openai embedding dimension
            )
            return VectorStoreIndex.from_vector_store(vectorStore)
    else:
        return VectorStoreIndex.from_vector_store(
            DuckDBVectorStore.from_local(vectorDB)
        )
# Execute a query on the accorns database
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

# Execute a query on the accorns database returning a pandas dataframe
def pandasQuery(conn, query, params=()):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        query = query.replace("?", "%s") if remoteAppDB else query
        return pd.read_sql_query(sql = query, con = conn, params=params)


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
# Check if the 2 passwords match and if the password is strong enough
def passCheck(password, password2):
    # Check if the password is strong enough
    if re_search(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_+=])[A-Za-z\d!@#$%^&*()-_+=]{8,20}$",
                 password) is None:
        return "Password must be between 8 and 20 characters and contain at least one uppercase letter, one lowercase letter, one number, and one special character"
    
    # Check if the passwords match
    if password != password2:
        return "Passwords do not match"
    
    return None

# Check if the access code has not been used yet
def accessCodeCheck(conn, accessCode):
    # Check the access code (must be valid and not used yet)
    code = pandasQuery(
        conn,
        'SELECT * FROM "accessCode" WHERE "code" = ? AND "used" IS NULL',
        (accessCode,),
    )

    return None if code.shape[0] == 0 else code
