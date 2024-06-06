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
from sqlparse import split as sql_split
import json
from shutil import move
import toml
from urllib.request import urlretrieve
from tempfile import TemporaryDirectory
import secrets
import string

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

saveFileCopy = any(
    config["localStorage"]["saveFileCopy"] == x for x in ["True", "true", "T", 1]
)

if not saveFileCopy:
    storageFolder = None
else:
    storageFolder = os.path.join(
        os.path.normpath(config["localStorage"]["storageFolder"]), ""
    )

# ----------- FUNCTIONS -----------
# *********************************

# Database to store app data (this is not the vector database!)
def createLocalAccornsDB(DBpath, sqlFile):
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

def createLocalVectorDB(DBpath, sqlFile):
    conn = duckdb.connect(DBpath)
    cursor = conn.cursor()
    # Check if the documents, file and keyword tables exist
    cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_name IN('documents', 'file', 'keyword');")
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


# Generate local databases if needed
if not (shared.remoteAppDB):
    print(createLocalAccornsDB(shared.sqliteDB, os.path.join(appDBDir, "appDB_sqlite_accorns.sql")))
    print(createLocalVectorDB(shared.vectorDB, os.path.join(appDBDir, "appDB_duckdb_vectordb.sql")))

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

def addDemo():    
    conn = shared.appDBConn(postgresUser)    
    cursor = conn.cursor()    
    
    # Check if the demo has already been added  
    cursor.execute("SELECT * FROM topic LIMIT 1")  
    if cursor.fetchone() is not None:
        return (1, "Demo already present")
    
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
    addFileToDB(shared.demoFile, shared.vectorDB)
    
    return (0, "Demo added")

# Add the demo to the database if requested
if shared.addDemo:
    print(addDemo()) 

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

def generate_hash():
    alphanumeric_characters = string.ascii_letters + string.digits
    hash_parts = []
    for _ in range(3):
        hash_part = ''.join(secrets.choice(alphanumeric_characters) for _ in range(3))
        hash_parts.append(hash_part)
    return '-'.join(hash_parts)


def generate_hash_list(n = 1):
    hash_values = []
    for _ in range(n):
        hash_value = generate_hash()
        hash_values.append(hash_value)
    
    # CHeck if all the hash values are unique otherwise generate new hash values
    while len(hash_values) != len(set(hash_values)):
        # Only generate the number of hash values that are not unique
        hash_values = list(set(hash_values)) + generate_hash_list(n - len(set(hash_values)))
        

    return hash_values

def generate_access_codes(n, uID, adminLevel):

    # Check if n and unID are set
    if not n:
        raise ValueError("Please provide the number of access codes to generate")
    if not uID:
        raise ValueError("Please provide the uID of the user generating the access codes")

    codes = []
    conn = shared.appDBConn()
    cursor = conn.cursor()
    x = n
    while len(codes) < n:
        codes = codes + (generate_hash_list(x))
        # Check if the accessCode does not exist in the database
        cursor.execute("SELECT code FROM accessCode WHERE code IN ({})".format(','.join(['?']*len(codes))), codes)
        existing_codes = cursor.fetchall()
        
        if existing_codes:
            # remove the existing codes from the list
            codes = [code for code in codes if code not in existing_codes[0]]
            x = n - len(codes)
    
    # Insert the new codes into the database
    _ = shared.executeQuery(cursor, 'INSERT INTO "accessCode"("code", "uID_creator", "adminLevel", "created") VALUES(?, ?, ?, ?)',
                             [(code, uID, adminLevel, shared.dt()) for code in codes])
    conn.commit()
    conn.close()

    return codes
