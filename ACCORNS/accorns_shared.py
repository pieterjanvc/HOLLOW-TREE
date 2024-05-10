# *********************************************
# ----------- ACCORNS APP SHARED CODE ---------
# *********************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

from shared import shared

# -- General
import os
import sqlite3
import duckdb
import json
from shutil import move
import toml
from urllib.request import urlretrieve
import psycopg2

# -- Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore

# -- Shiny
from shiny.express import ui

# -- Other
import nest_asyncio

nest_asyncio.apply()

# --- Global variables

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
appDBDir = os.path.join(curDir, "appDB")

with open(os.path.join(curDir,"accorns_config.toml"), "r") as f:
    config = toml.load(f)

addDemo = any(config["general"]["addDemo"] == x for x in ["True", "true", "T", 1])
tempFolder = os.path.join(config["localStorage"]["tempFolder"], "")
storageFolder = os.path.join(config["localStorage"]["storageFolder"], "")

# ----------- FUNCTIONS -----------
# *********************************

# Database to store app data (this is not the vector database!)
def createSQLiteAppDB(DBpath, addDemo=False):
    if os.path.exists(DBpath):
        return (2, "Database already exists. Skipping")

    # Create a new database from the SQL file
    with open(os.path.join(appDBDir,"appDB_sqlite.sql"), "r") as file:
        query = file.read().replace("\n", " ").replace("\t", "").split(";")

    conn = sqlite3.connect(DBpath)
    cursor = conn.cursor()

    for x in query:
        _ = cursor.execute(x)

    if not addDemo:
        conn.commit()
        conn.close()
        return (0, "DB created - No demo added")

    with open(os.path.join(appDBDir,"appDB_sqlite_demo.sql"), "r") as file:
        query = file.read().replace("\n", " ").replace("\t", "").split(";")

    for x in query:
        _ = cursor.execute(x)

    conn.commit()
    conn.close()

    return (1, "DB created - Demo added")


# Make new app DB if needed
print(createSQLiteAppDB(shared.sqliteDB, addDemo=addDemo))


# Create DuckDB vector database and add files
def addFileToDB(newFile, vectorDB, storageFolder=None, newFileName=None):
    # In case the file is a URL download it first
    isURL = False
    if newFile.startswith("http://") or newFile.startswith("https://"):
        if not os.path.exists(tempFolder):
            os.makedirs(tempFolder)

        isURL = True
        urlretrieve(newFile, tempFolder + os.path.basename(newFile))
        newFile = tempFolder + os.path.basename(newFile)

    if not os.path.exists(newFile):
        raise ConnectionError(f"The newFile was not found at {newFile}")

    # Move the file to permanent storage if requested
    if (storageFolder is not None) & (not isURL):
        if not os.path.exists(storageFolder):
            os.makedirs(storageFolder)

        newFileName = os.path.basename(newFile) if newFileName is None else newFileName
        newFilePath = os.path.join(storageFolder, "") + newFileName

        if os.path.exists(newFilePath):
            return (1, "A file with this name already exists. Skipping")

        move(newFile, newFilePath)
        newFile = newFilePath

    newData = SimpleDirectoryReader(input_files=[newFile]).load_data()

    # Delete the file from URL if not set to be kept
    if (storageFolder is None) & isURL:
        os.remove(newFile)

    if shared.remoteAppDB:
        vector_store = PGVectorStore.from_params(
                database="vector_db",
                host="localhost",
                password="accorns",
                port=5432,
                user="accorns",
                table_name="document",
                embed_dim=1536,  # openai embedding dimension
            )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(
            newData,
            storage_context=storage_context,
            transformations=[TitleExtractor(), KeywordExtractor()],
        )
    else:

        # Add file to vector store https://docs.llamaindex.ai/en/stable/examples/vector_stores/DuckDBDemo/?h=duckdb
        if os.path.exists(vectorDB):
            vector_store = DuckDBVectorStore.from_local(vectorDB)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                newData,
                storage_context=storage_context,
                transformations=[TitleExtractor(), KeywordExtractor()],
        )
        else:
            vector_store = DuckDBVectorStore(
                os.path.basename(vectorDB), persist_dir=os.path.dirname(vectorDB)
            )
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_documents(
                newData,
                storage_context=storage_context,
                transformations=[TitleExtractor(), KeywordExtractor()],
            )        

            with open(os.path.join(appDBDir,"expandVectorDB.sql"), "r") as file:
                query = file.read().replace("\n", " ").replace("\t", "").split(";")

            conn = duckdb.connect(vectorDB)
            cursor = conn.cursor()

            for x in query:
                _ = cursor.execute(x)

            cursor.commit()
            conn.close()

    # Get the metadata out of the DB excerpt_keywords document_title
    fileName = newData[0].metadata["file_name"]
    # vectorDB = "appData/vectorstore.duckdb"
    if shared.remoteAppDB:
        conn = psycopg2.connect(
            host="localhost",
            user="accorns",
            password="accorns",
            database="vector_db",
        )      
        cursor = conn.cursor()
        x = cursor.execute(       
            "SELECT metadata_ ->> 'document_title' as x, metadata_ ->> 'excerpt_keywords' as y "
            f"FROM data_document WHERE metadata_ ->> 'file_name' = '{fileName}'"
        ).fetchall()

        chunkTitles = "* " + "\n* ".join(set([y[0] for y in x]))
        chunkKeywords = ", ".join(set((", ".join([y[1] for y in x])).split(", "))) 
    else:
        conn = duckdb.connect(vectorDB)
        cursor = conn.cursor()
        _ = cursor.execute(       
            "SELECT metadata_ ->> ['document_title', 'excerpt_keywords'] FROM documents WHERE "
            f"CAST(json_extract(metadata_, '$.file_name') as VARCHAR) = '\"{fileName}\"'"
        )
        x = cursor.fetchall()

        chunkTitles = "* " + "\n* ".join(set([y[0][0] for y in x]))
        chunkKeywords = ", ".join(set((", ".join([y[0][1] for y in x])).split(", ")))

    # Summarise everything using the LLM and add it to the appDB
    docSum = (
        "Below is a list of subheadings belonging to the same document."
        f"Note that many of them might be near identical:\n\n{chunkTitles}"
        f"\n\nYou also get a list of keywords describing the same content:\n\n{chunkKeywords}"
        "\n\nAgain note that some key words are very related.\n"
        "Your task is to summarize all of this into a single, succinct short title, a subtitle, "
        "and a list of the top-10 keywords. Stay as close to the original titles as possible."
        " The output should be in the following valid JSON format: \n\n"
        '{"title": "", "subtitle": "", "keywords": []}'
    )
    docSum = json.loads(str(index.as_query_engine().query(docSum)))

    cursor = conn.cursor()
    _ = shared.executeQuery(cursor,
            'INSERT INTO "file"("fID", "fileName", "title", "subtitle", "created") '
            "VALUES(nextval('seq_fID'), ?, ?, ?, ?)",
            (fileName,docSum['title'],docSum['subtitle'], shared.dt())
                         )
    fID = shared.executeQuery(cursor, "SELECT currval('seq_fID')").fetchall()[0][0]
    _ = shared.executeQuery(cursor,
        'INSERT INTO "keyword"("kID", "fID", "keyword") '
        f"VALUES(nextval('seq_kID'),{int(fID)}, ?)",
        [(item,) for item in docSum["keywords"]],
    )
    conn.commit()
    conn.close()

    return (0, "Completed")


# When demo data is to be added use a file stored in a GitHub issue
# TODO Replace URL once public!
if addDemo & (not os.path.exists(shared.vectorDB)):
    newFile = "https://github.com/pieterjanvc/seq2mgs/files/14964109/Central_dogma_of_molecular_biology.pdf"
    addFileToDB(newFile, shared.vectorDB)

# Load the vector index from storage
if shared.remoteAppDB:
    vector_store = PGVectorStore.from_params(
        database="accorns",
        host="localhost",
        password="accorns",
        port=5432,
        user="accorns",
        table_name="document",
        embed_dim=1536,  # openai embedding dimension
    )
else:
    vector_store = DuckDBVectorStore.from_local(shared.vectorDB)
index = VectorStoreIndex.from_vector_store(vector_store)

def backupQuery(cursor, sID, table, rowID, attribute, isBot=None, timeStamp=shared.dt()):
    # Get the Primary Key
    if shared.remoteAppDB:
        q = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' LIMIT 1"
    else:
        q = f"SELECT name FROM pragma_table_info('{table}') WHERE pk = 1"

    _ = shared.executeQuery(cursor, q)
    PK = cursor.fetchone()[0]

    if PK is None:
        raise ValueError(
            f"There is no table with the name {table} in the SCUIRREL database"
        )

    # Check if the attribute exists
    if shared.remoteAppDB:
        q = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{attribute}'"
    else:
        q = f"SELECT name FROM pragma_table_info('{table}') WHERE name = '{attribute}'"

    _ = shared.executeQuery(cursor, q)
    check = cursor.fetchone()

    if check is None:
        raise ValueError(f"'{attribute}' is not a column of table '{table}'")
    # Check isBot and assign 0, 1 or Null when False, True, None
    isBot = isBot + 0 if isBot is not None else "NULL"
    # Insert into backup
    _ = shared.executeQuery(
        cursor,
        f'INSERT INTO "backup" ("sID", "modified", "table", "rowID", "created", "isBot", "attribute", "tValue") '
        f'SELECT {sID} as "sID", \'{timeStamp}\' as "modified", \'{table}\' as "table", {rowID} as "rowID", '
        f'"modified" as "created", {isBot} as "isBot", \'{attribute}\' as "attribute", "{attribute}" as "tValue" '
        f'FROM "{table}" WHERE "{PK}" = {rowID}',
    )


def modalMsg(content, title="Info"):
    m = ui.modal(
        content,
        title=title,
        easy_close=True,
        size="s",
        footer=ui.TagList(ui.modal_button("Close")),
    )
    ui.modal_show(m)
