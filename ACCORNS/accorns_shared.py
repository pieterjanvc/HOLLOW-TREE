# *********************************************
# ----------- ACCORNS APP SHARED CODE ---------
# *********************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

from shared import shared

# -- General
import os
import sqlite3
from sqlparse import split as sql_split
import json
from shutil import move
import toml
from urllib.request import urlretrieve
from tempfile import TemporaryDirectory

# -- Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore

# -- Shiny
from shiny.express import ui

# -- Other
import nest_asyncio

nest_asyncio.apply()

# --- Global variables
postgresUser = "accorns"  # Used by shared.appDBConn

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
appDBDir = os.path.join(curDir, "appDB")

with open(os.path.join(curDir, "accorns_config.toml"), "r") as f:
    config = toml.load(f)

addDemo = any(config["general"]["addDemo"] == x for x in ["True", "true", "T", 1])

saveFileCopy = any(
    config["localStorage"]["saveFileCopy"] == x for x in ["True", "true", "T", 1]
)

if not saveFileCopy:
    storageFolder = None
else:
    storageFolder = os.path.join(
        os.path.normpath(config["localStorage"]["storageFolder"]), ""
    )

demoFile = "https://github.com/pieterjanvc/seq2mgs/files/14964109/Central_dogma_of_molecular_biology.pdf"

# ----------- FUNCTIONS -----------
# *********************************


# Database to store app data (this is not the vector database!)
def createSQLiteAppDB(DBpath, addDemo=False):
    if os.path.exists(DBpath):
        return (2, "Database already exists. Skipping")

    # Create a new database from the SQL file
    with open(os.path.join(appDBDir, "appDB_sqlite_accorns.sql"), "r") as file:
        query = file.read().replace("\n", " ").replace("\t", "").split(";")

    conn = sqlite3.connect(DBpath)
    cursor = conn.cursor()

    for x in query:
        _ = cursor.execute(x)

    if not addDemo:
        conn.commit()
        conn.close()
        return (0, "DB created - No demo added")

    with open(os.path.join(appDBDir, "appDB_sqlite_demo.sql"), "r") as file:
        query = sql_split(file.read())

    for x in query:
        _ = cursor.execute(x)

    conn.commit()
    conn.close()

    return (1, "DB created - Demo added")


# Make new app DB if needed
if not (shared.remoteAppDB):
    print(createSQLiteAppDB(shared.sqliteDB, addDemo=addDemo))


# Create vector database and add files
def addFileToDB(
    newFile,
    vectorDB=None,
    remoteAppDB=shared.remoteAppDB,
    storageFolder=None,
    newFileName=None,
):
    # In case the file is a URL download it first
    isURL = False
    if newFile.startswith("http://") or newFile.startswith("https://"):
        isURL = True
        newFileName = os.path.basename(newFile)
        _, ext = os.path.splitext(newFile)

        if ext not in [
            ".pdf",
            ".docx",
            ".txt",
            "pptx",
            ".md",
            ".epub",
            ".ipynb",
            ".ppt",
        ]:
            return (2, "Not a valid file")

        tempDir = TemporaryDirectory()
        newFileName = os.path.join(tempDir.name, "") + newFileName
        newFile = urlretrieve(newFile, newFileName)[0]

    if not os.path.exists(newFile):
        raise ConnectionError(f"The newFile was not found at {newFile}")

    # Move the file to permanent storage if requested
    newFileName = os.path.basename(newFile) if newFileName is None else newFileName

    if (storageFolder is not None) & (not isURL):
        if not os.path.exists(storageFolder):
            os.makedirs(storageFolder)

        newFilePath = os.path.join(storageFolder, "") + newFileName

        if os.path.exists(newFilePath):
            return (1, "A file with this name already exists. Skipping")

        move(newFile, newFilePath)
        newFile = newFilePath
    elif not isURL:
        newFilePath = os.path.join(os.path.dirname(newFile), newFileName)
        move(newFile, newFilePath)
        newFile = newFilePath

    newData = SimpleDirectoryReader(input_files=[newFile]).load_data()

    # Delete the file from URL if not set to be kept
    if (storageFolder is None) & isURL:
        os.remove(newFile)

    if remoteAppDB:
        vector_store = PGVectorStore.from_params(
            host=shared.postgresHost,
            port=shared.postgresPort,
            user=postgresUser,
            password=os.environ.get("POSTGRES_PASS_ACCORNS"),
            database="vector_db",
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
        conn = shared.vectorDBConn(vectorDB=vectorDB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM information_schema.tables WHERE table_name ='keyword';"
        )
        if cursor.fetchone() is not None:
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

            with open(os.path.join(appDBDir, "appDB_duckdb_vectordb.sql"), "r") as file:
                query = sql_split(file.read())

            for x in query:
                _ = cursor.execute(x)

            cursor.commit()

        conn.close()

    # Get the metadata out of the DB excerpt_keywords document_title
    fileName = os.path.basename(newFileName)
    # vectorDB = "appData/vectorstore.duckdb"
    if remoteAppDB:
        conn = shared.vectorDBConn(postgresUser)
        cursor = conn.cursor()
        _ = cursor.execute(
            "SELECT metadata_ ->> 'document_title' as x, metadata_ ->> 'excerpt_keywords' as y "
            f"FROM data_document WHERE metadata_ ->> 'file_name' = '{fileName}'"
        )

        q = cursor.fetchall()
        # When we create the document table we need to grant access to the scuirrel user
        _ = cursor.execute("GRANT SELECT ON TABLE data_document TO scuirrel")
        conn.commit()
        conn.close()

        chunkTitles = "* " + "\n* ".join(set([x[0] for x in q]))
        chunkKeywords = ", ".join(set((", ".join([x[1] for x in q])).split(", ")))
    else:
        conn = shared.vectorDBConn(vectorDB=vectorDB)
        cursor = conn.cursor()
        _ = cursor.execute(
            "SELECT metadata_ ->> ['document_title', 'excerpt_keywords'] FROM documents WHERE "
            f"CAST(json_extract(metadata_, '$.file_name') as VARCHAR) = '\"{fileName}\"'"
        )
        q = cursor.fetchall()
        conn.close()

        chunkTitles = "* " + "\n* ".join(set([x[0][0] for x in q]))
        chunkKeywords = ", ".join(set((", ".join([x[0][1] for x in q])).split(", ")))

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

    conn = shared.vectorDBConn(postgresUser, vectorDB=vectorDB)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'INSERT INTO "file"("fID", "fileName", "title", "subtitle", "created") '
        "VALUES(nextval('seq_fID'), ?, ?, ?, ?)",
        (fileName, docSum["title"], docSum["subtitle"], shared.dt()),
    )
    shared.executeQuery(cursor, "SELECT currval('seq_fID')")
    fID = cursor.fetchone()[0]
    _ = shared.executeQuery(
        cursor,
        'INSERT INTO "keyword"("kID", "fID", "keyword") '
        f"VALUES(nextval('seq_kID'),{int(fID)}, ?)",
        [(item,) for item in docSum["keywords"]],
    )
    conn.commit()
    conn.close()

    return (0, "Completed")


# Add demo file to vector DB if in settings
conn = shared.vectorDBConn(postgresUser)
cursor = conn.cursor()

if shared.remoteAppDB:
    cursor.execute('SELECT * FROM "keyword" LIMIT 1')
else:
    cursor.execute(
        "SELECT * FROM information_schema.tables WHERE table_name ='keyword';"
    )

newVectorDB = True if cursor.fetchone() is None else False

if newVectorDB and not addDemo:
    # Create a blank DuckDB vector database
    with open(os.path.join(appDBDir, "appDB_duckdb_vectordb.sql"), "r") as file:
        query = sql_split(file.read())

        cursor = conn.cursor()
        query.append(
            'CREATE TABLE documents(node_id VARCHAR, "text" VARCHAR, embedding FLOAT[], metadata_ JSON);'
        )

        for x in query:
            _ = cursor.execute(x)

        cursor.commit()

conn.close()

if newVectorDB and addDemo:
    addFileToDB(demoFile, shared.vectorDB)

# Add demo topic / concepts to accorns if in settings
conn = shared.appDBConn(postgresUser)
cursor = conn.cursor()
cursor.execute("SELECT * FROM topic LIMIT 1")
newAppDB = True if cursor.fetchone() is None else False

# Adding to duckDB is handled in the createSQLiteAppDB function
if newAppDB & addDemo & shared.remoteAppDB:
    with open(os.path.join(appDBDir, "appDB_postgres_demo.sql"), "r") as file:
        query = file.read()

    _ = cursor.execute(query)

conn.commit()
conn.close()

# Load the vector index from storage
if shared.remoteAppDB:
    vector_store = PGVectorStore.from_params(
        host=shared.postgresHost,
        port=shared.postgresPort,
        user=postgresUser,
        password=os.environ.get("POSTGRES_PASS_ACCORNS"),
        database="vector_db",
        table_name="document",
        embed_dim=1536,  # openai embedding dimension
    )
else:
    vector_store = DuckDBVectorStore.from_local(shared.vectorDB)

index = VectorStoreIndex.from_vector_store(vector_store)


def backupQuery(
    cursor, sID, table, rowID, attribute, isBot=None, timeStamp=shared.dt()
):
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
