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
from bcrypt import checkpw
import secrets
import string

# Llamaindex
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore

# Shiny
from shiny import reactive, ui
from htmltools import HTML

# --- VARIABLES ---

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
adminLevels = {0: "anonymous", 1: "User", 2: "Instructor", 3: "Admin"}
codeTypes = {0: "accessCode", 1: "resetCode", 2: "groupCode"}

with open(os.path.join(curDir, "shared_config.toml"), "r") as f:
    config = toml.load(f)

remoteAppDB = any(
    config["general"]["remoteAppDB"] == x for x in ["True", "true", "T", 1]
)
addDemo = any(config["general"]["addDemo"] == x for x in ["True", "true", "T", 1])
demoFile = "https://github.com/pieterjanvc/seq2mgs/files/14964109/Central_dogma_of_molecular_biology.pdf"
postgresHost = config["postgres"]["host"]
postgresPort = int(config["postgres"]["port"])
vectorDB = os.path.normpath(config["localStorage"]["duckDB"])
sqliteDB = os.path.normpath(config["localStorage"]["sqliteDB"])
postgresAccorns = "accorns"
postgresScuirrel = "scuirrel"
personalInfo = any(
    config["auth"]["personalInfo"] == x for x in ["True", "true", "T", 1]
)
validEmail = config["auth"]["validEmail"]

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
def inputCheck(input, nChar=6):
    if re_search(rf"(?=(.*[a-zA-Z0-9]){{{nChar},}}).*", input):
        return True
    else:
        False


# Get the correct ID depending on the session namespace
def nsID(id, session, addHashtag=False):
    id = session.ns + "-" + id if (session.ns != "") else id

    return "#" + id if addHashtag else id


# This function allows you to hide/show/disable/enable elements by ID or data-value
# The latter is needed because tabs don't use ID's but data-value
def elementDisplay(id, effect, session, alertNotFound=True, ignoreNS=False):
    id = session.ns + "-" + id if (session.ns != "") and (not ignoreNS) else id

    @reactive.effect
    async def _():
        await session.send_custom_message(
            "hideShow", {"id": id, "effect": effect, "alertNotFound": alertNotFound}
        )


def consecutiveInt(nums, start=1):
    # Sort the list of numbers
    sorted_nums = sorted(nums)
    # Check if each number is consecutive starting from 1
    return all(sorted_nums[i] == i + start for i in range(len(sorted_nums)))


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
def getIndex(user, postgresUser, remote=remoteAppDB):
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
        return pd.read_sql_query(sql=query, con=conn, params=params)


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
    if (
        re_search(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_+=.])[A-Za-z\d!@#$%^&*()-_+=.]{8,20}$",
            password,
        )
        is None
    ):
        return "Password must be between 8 and 20 characters and contain at least one uppercase letter, one lowercase letter, one number, and one special character (!@#$%^&*()-_+=.)"

    # Check if the passwords match
    if password != password2:
        return "Passwords do not match"

    return None


# Generate a hash from a string
def generate_hash():
    alphanumeric_characters = string.ascii_letters + string.digits
    hash_parts = []
    for _ in range(3):
        hash_part = "".join(secrets.choice(alphanumeric_characters) for _ in range(3))
        hash_parts.append(hash_part)
    return "-".join(hash_parts)


# Generate a list of unique hash values
def generate_hash_list(n=1):
    hash_values = []
    for _ in range(n):
        hash_value = generate_hash()
        hash_values.append(hash_value)

    # CHeck if all the hash values are unique otherwise generate new hash values
    while len(hash_values) != len(set(hash_values)):
        # Only generate the number of hash values that are not unique
        hash_values = list(set(hash_values)) + generate_hash_list(
            n - len(set(hash_values))
        )

    return hash_values


# Generate access codes and add them to the database
def generate_access_codes(
    cursor, codeType, creatorID, gID=None, adminLevel=None, n=1, userID=None, note=""
):
    note = None if note.strip() == "" else note

    # Check if n and unID are set
    if userID is not None:
        n = 1
        adminLevel = None
        userID = int(userID)
    elif not isinstance(adminLevel, int):
        raise ValueError(
            "Please provide the adminLevel of the user generating the codes"
        )
    elif adminLevel < 0 or adminLevel > max(adminLevels.keys()):
        raise ValueError(
            f"The adminLevel must be an integer between 0 and {max(adminLevels.keys())}"
        )

    if gID is not None:
        gID = int(gID)

    if not creatorID:
        raise ValueError("Please provide the uID of the user generating the codes")

    codes = []
    x = n
    while len(codes) < n:
        codes = tuple(codes + (generate_hash_list(x)))
        # Check if the accessCode does not exist in the database
        executeQuery(
            cursor,
            'SELECT "code" FROM "accessCode" WHERE "code" IN ({})'.format(
                ",".join(["?"] * len(codes))
            ),
            codes,
        )
        existing_codes = cursor.fetchall()

        if existing_codes:
            # remove the existing codes from the list
            codes = [code for code in codes if code not in existing_codes[0]]
            x = n - len(codes)

    # Insert the new codes into the database
    _ = executeQuery(
        cursor,
        (
            'INSERT INTO "accessCode"("code", "codeType", "uID_creator", "uID_user", "gID", "adminLevel", "created", "note")'
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        [
            (code, int(codeType), int(creatorID), userID, gID, adminLevel, dt(), note)
            for code in codes
        ],
    )

    # Return a data frame
    return pd.DataFrame(
        {codeTypes[codeType]: codes, "adminLevel": adminLevel, "note": note}
    )


# Check if the access code has not been used yet
def accessCodeCheck(conn, accessCode, codeType, uID=None):
    # Check the access code (must be valid and not used yet)
    if codeType == 0:
        code = pandasQuery(
            conn,
            'SELECT * FROM "accessCode" WHERE "code" = ? AND "codeType" = 0 AND "used" IS NULL',
            (accessCode,),
        )
    elif codeType == 1:
        code = pandasQuery(
            conn,
            'SELECT * FROM "accessCode" WHERE "code" = ? AND "codeType" = 1 AND "uID_user" = ? AND used IS NULL',
            (accessCode, int(uID)),
        )
    elif codeType == 2:
        code = pandasQuery(
            conn,
            'SELECT * FROM "accessCode" WHERE "code" = ? AND "codeType" = 2 AND used IS NULL',
            (accessCode,),
        )
    else:
        raise ValueError(
            "Please provide a valid codeType. "
            + " ".join(f"{key}: {value}" for key, value in codeTypes.items())
        )

    return None if code.shape[0] == 0 else code


# check user authentication
def authCheck(conn, username, password):
    checkUser = pandasQuery(
        conn,
        'SELECT * FROM "user" WHERE "username" = ? AND "username" != \'anonymous\'',
        (username,),
    )

    if checkUser.shape[0] == 0:
        return {"user": None, "password_check": None, "admin_check": None}

    password_check = (
        True
        if checkpw(password.encode("utf-8"), checkUser.password.iloc[0].encode("utf-8"))
        else False
    )
    checkUser.drop(columns=["password"], inplace=True)

    return {
        "user": checkUser,
        "password_check": password_check,
        "adminLevel": int(checkUser.adminLevel.iloc[0]),
    }


def inputNotification(session, id, message="Error", show=True, colour="red"):
    msgId = id + "_msg"
    ui.remove_ui(nsID(msgId, session, True))

    if show:
        ui.insert_ui(
            HTML(
                f"<div id={nsID(msgId, session)} style='color: {colour}'>{message}</div>"
            ),
            nsID(id, session, True),
            "afterEnd",
        )

    return
