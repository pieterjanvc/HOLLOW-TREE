# *********************************************
# ----------- ACCORNS APP SHARED CODE ---------
# *********************************************

from shared import shared

# -- General
import os
import sqlite3
import duckdb
from sqlparse import split as sql_split
import json
from shutil import move
import toml
from urllib.request import urlretrieve
from tempfile import TemporaryDirectory
import nest_asyncio

nest_asyncio.apply()

# -- Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore

# -- Shiny
from shiny.express import ui

# --- Global variables

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
appDBDir = os.path.join(curDir, "appDB")

with open(os.path.join(curDir, "accorns_config.toml"), "r") as f:
    config = toml.load(f)

saveFileCopy = config["localStorage"]["saveFileCopy"]

if not saveFileCopy:
    storageFolder = None
else:
    storageFolder = os.path.join(
        os.path.normpath(config["localStorage"]["storageFolder"]), ""
    )

# ----------- FUNCTIONS -----------
# *********************************


# Create a file-based accorns database
def createLocalAccornsDB(
    DBpath=shared.sqliteDB, sqlFile=os.path.join(appDBDir, "appDB_sqlite_accorns.sql")
):
    if os.path.exists(DBpath):
        return (1, "Accorns database already exists. Skipping")

    # Create a new database from the SQL file
    with open(sqlFile, "r") as file:
        query = file.read().replace("\n", " ").replace("\t", "").split(";")

    conn = sqlite3.connect(DBpath)
    cursor = conn.cursor()

    for x in query:
        _ = cursor.execute(x)

    conn.commit()
    conn.close()
    return (0, "Accorns database created")


# Create a file-based vector database
def createLocalVectorDB(
    DBpath=shared.vectorDB, sqlFile=os.path.join(appDBDir, "appDB_duckdb_vectordb.sql")
):
    conn = duckdb.connect(DBpath)
    cursor = conn.cursor()
    # Check if the documents, file and keyword tables exist
    cursor.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name IN('documents', 'file', 'keyword');"
    )
    # Check there are three tables
    if cursor.fetchone()[0] == 3:
        conn.close()
        return (1, "Vector database already exists. Skipping")

    with open(sqlFile, "r") as file:
        query = sql_split(file.read())

        for x in query:
            _ = cursor.execute(x)

    cursor.commit()
    conn.close()

    return (0, "Local DuckDB vector database created")


# Create vector database and add files
def addFileToDB(
    newFile,
    shinyToken,
    vectorDB,
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

    # Check if the file name is already in file table of the vector database
    conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
    existingFile = shared.pandasQuery(
        conn,
        'SELECT "fileName" FROM "file" WHERE "fileName" = ?',
        (newFileName,),
    )
    conn.close()

    if existingFile.shape[0] > 0:
            return (1, "A file with this name already exists. Please rename the file before uploading it again")

    if (storageFolder is not None) & (not isURL):
        if not os.path.exists(storageFolder):
            os.makedirs(storageFolder)

        newFilePath = os.path.join(storageFolder, "") + newFileName

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
            user=shared.postgresAccorns,
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
        vector_store = DuckDBVectorStore.from_local(vectorDB)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(
            newData,
            storage_context=storage_context,
            transformations=[TitleExtractor(), KeywordExtractor()],
        )

    # Get the metadata out of the DB excerpt_keywords document_title
    fileName = os.path.basename(newFileName)

    if remoteAppDB:
        conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
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
        conn = shared.vectorDBConn(
            postgresUser=shared.postgresAccorns, vectorDB=vectorDB
        )
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

    conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns, vectorDB=vectorDB)
    cursor = conn.cursor()
    _ = shared.executeQuery(
        cursor,
        'INSERT INTO "file"("fID", "fileName", "title", "subtitle", "shinyToken", "created") '
        "VALUES(nextval('seq_fID'), ?, ?, ?, ?, ?)",
        (fileName, docSum["title"], docSum["subtitle"], shinyToken, shared.dt()),
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


# Add the demo to the app
def addDemo(shinyToken):
    msg = 0

    conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    cursor = conn.cursor()

    # Check if the demo has already been added
    cursor.execute("SELECT * FROM topic LIMIT 1")
    if cursor.fetchone() is None:
        msg = 1

        # Check if the conn is to duckdb or postgres
        if "sqlite" in str(conn):
            with open(os.path.join(appDBDir, "appDB_sqlite_demo.sql"), "r") as file:
                query = sql_split(file.read())

            for x in query:
                _ = cursor.execute(x)

        else:
            with open(os.path.join(appDBDir, "appDB_postgres_demo.sql"), "r") as file:
                query = file.read()
                _ = cursor.execute(query)

        conn.commit()
        conn.close()

    # Add the demo file to the vector database
    # Check if the demo file is already in the database
    conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
    cursor = conn.cursor()
    _ = cursor.execute('SELECT "fID" FROM file LIMIT 1')

    if cursor.fetchone() is None:
        msg = 3 if msg == 1 else 2
        addFileToDB(
            newFile=shared.demoFile, shinyToken=shinyToken, vectorDB=shared.vectorDB
        )

    return (
        msg,
        [
            "Demo already present",
            "Demo added to the accorns database",
            "Demo file added to the vector database",
            "Demo added to accorns and vector database",
        ][msg],
    )


# Backup fields from specific tables in accorns
def backupQuery(
    cursor, sID, table, rowID, attribute, dataType, isBot=None, timeStamp=shared.dt()
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

    # type of the attribute needs to be checked
    if dataType == "str":
        dataType = '"tValue"'
    elif dataType == "int":
        dataType = '"iValue"'
    else:
        raise ValueError("The data type of the attribute is not supported")

    # Insert into backup
    _ = shared.executeQuery(
        cursor,
        (
            f'INSERT INTO "backup" ("sID", "modified", "table", "rowID", "created", "isBot", "attribute", {dataType}) '
            f'SELECT {sID} as "sID", \'{timeStamp}\' as "modified", \'{table}\' as "table", {rowID} as "rowID", '
            f'"modified" as "created", {isBot} as "isBot", \'{attribute}\' as "attribute", "{attribute}" as {dataType} '
            f'FROM "{table}" WHERE "{PK}" = {rowID}'
        ),
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
