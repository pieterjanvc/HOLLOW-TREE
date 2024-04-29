# *********************************************
# ----------- ACCORNS APP SHARED CODE ---------
# *********************************************

# All variables and functions below are shared across different session
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

# -- General
import os
import sqlite3
from datetime import datetime
import regex as re
import duckdb
import json
from shutil import move
import toml
from urllib.request import urlretrieve

# -- Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore

# -- Shiny
from shiny.express import ui

# -- Other
import nest_asyncio

nest_asyncio.apply()

# --- Global variables

with open("config.toml", "r") as f:
    config = toml.load(f)

addDemo = any(config["general"]["addDemo"] == x for x in ["True", "true", "T", 1])
appDB = config["data"]["appDB"]
vectorDB = config["data"]["vectorDB"]
tempFolder = os.path.join(config["data"]["tempFolder"], "")
storageFolder = os.path.join(config["data"]["storageFolder"], "")

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = config["LLM"]["gptModel"]

# Use OpenAI LLM from Llamaindex
llm = OpenAI(model=gptModel)


# ----------- FUNCTIONS -----------
# *********************************


def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def inputCheck(input):
    if re.search(r"(?=(.*[a-zA-Z0-9]){6,}).*", input):
        return True
    else:
        False


# Database to store app data (this is not the vector database!)
def createAppDB(DBpath, addDemo=False):
    if os.path.exists(DBpath):
        return (1, "Database already exists. Skipping")

    # Create a new database from the SQL file
    with open("appDB/createAppDB.sql", "r") as file:
        query = file.read().replace("\n", " ").replace("\t", "").split(";")

    conn = sqlite3.connect(DBpath)
    cursor = conn.cursor()

    for x in query:
        _ = cursor.execute(x)

    # Add the anonymous user and main admin
    _ = cursor.execute(
        "INSERT INTO user(username, isAdmin, created, modified)"
        f'VALUES("anonymous", 0, "{dt()}", "{dt()}"), ("admin", 1, "{dt()}", "{dt()}")'
    )

    if not addDemo:
        conn.commit()
        conn.close()
        return

    # Add a test topic (to be removed later)
    topic = "The central dogma of molecular biology"
    _ = cursor.execute(
        "INSERT INTO topic(topic, created, modified)"
        f'VALUES("{topic}", "{dt()}", "{dt()}")'
    )
    tID = cursor.lastrowid

    # Add topic concepts (to be removed later)
    concepts = [
        ("Central dogma of molecular biology: DNA → RNA → Protein",),
        ("DNA: Composed of adenine (A), cytosine (C), guanine (G), and thymine (T); Blueprint of life",),
        ("Genes: Hold code for specific proteins",),
        ("RNA: Composed of nucleotides (including uracil, U); Single-stranded",),
        ("Transcription: RNA polymerase unwinds DNA double helix; Synthesizes complementary RNA strand",),
        ("Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm",),
        ("RNA splicing: Removes introns; Retains exons",),
        ("Translation: Occurs in ribosomes; Deciphers mRNA to assemble protein", ),
        ("Codons: Three-nucleotide sequences; Specify amino acids or signal start/termination of translation", ),
        ("Amino acids: Building blocks of proteins; Linked by peptide bonds", ),
        ("Protein folding: Adopts specific three-dimensional structure", ),
        ("Post-translational modifications: Addition of chemical groups; Cleavage of specific segments", ),
    ]
    _ = cursor.executemany(
        "INSERT INTO concept(tID, concept, created, modified) "
        f'VALUES({tID}, ?, "{dt()}", "{dt()}")',
        concepts,
    )
    conn.commit()
    conn.close()

    return (0, "Creation completed")


# Make new app DB if needed
print(createAppDB(appDB, addDemo=addDemo))


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

        # Add the a custom file info and keywords table
        with open("appDB/expandVectorDB.sql", "r") as file:
            query = file.read().replace("\n", " ").replace("\t", "").split(";")

        conn = duckdb.connect("../appData/vectordb.duckdb")
        cursor = conn.cursor()

        for x in query:
            _ = cursor.execute(x)

        cursor.commit()
        conn.close()

    # Get the metadata out of the DB excerpt_keywords document_title
    fileName = newData[0].metadata["file_name"]
    # vectorDB = "appData/vectorstore.duckdb"
    con = duckdb.connect(vectorDB)
    # con.query("SELECT metadata_ FROM documents").fetchall()
    x = con.query(
        f"SELECT metadata_ ->> ['document_title', 'excerpt_keywords'] FROM documents WHERE CAST(json_extract(metadata_, '$.file_name') as VARCHAR) = '\"{fileName}\"'"
    ).fetchall()
    con.close()

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

    conn = duckdb.connect(vectorDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        (
            'INSERT INTO file(fID, fileName, title, subtitle, created) '
            f"VALUES(nextval('seq_fID'), '{fileName}', '{docSum['title']}', '{docSum['subtitle']}', '{dt()}')"
        )
    )
    fID = cursor.execute("SELECT currval('seq_fID')").fetchall()[0][0]
    _ = cursor.executemany(
        "INSERT INTO keyword(kID, fID, keyword) " f"VALUES(nextval('seq_kID'),'{fID}', ?)",
        [(item,) for item in docSum["keywords"]],
    )
    conn.commit()
    conn.close()

    return (0, "Completed")


# When demo data is to be added use a file stored in a GitHub issue
# TODO Replace URL once public!
if addDemo & (not os.path.exists(vectorDB)):
    newFile = "https://github.com/pieterjanvc/seq2mgs/files/14964109/Central_dogma_of_molecular_biology.pdf"
    addFileToDB(newFile, vectorDB)


def backupQuery(cursor, sID, table, rowID, attribute, isBot=None, timeStamp=dt()):
    # Check if the table exists
    if (
        cursor.execute(
            f'SELECT * FROM sqlite_master WHERE tbl_name = "{table}"'
        ).fetchone()
        is None
    ):
        raise sqlite3.DataError("The table '{table}' does not exist in the database")
    # Get the Primary Key
    PK = cursor.execute(
        f"SELECT name FROM pragma_table_info('{table}') WHERE pk = 1"
    ).fetchone()[0]
    # Check if the attribute exists
    if (
        cursor.execute(
            f"SELECT name FROM pragma_table_info('{table}') WHERE name = '{attribute}'"
        ).fetchone()
        is None
    ):
        raise sqlite3.DataError(f"'{attribute}' is not a column of table '{table}'")
    # Check isBot and assign 0, 1 or Null when False, True, None
    isBot = isBot + 0 if isBot is not None else "NULL"
    # Insert into backup
    _ = cursor.execute(
        f"INSERT INTO backup (sID, modified, 'table', 'rowID', created, isBot, 'attribute', tValue) "
        f"SELECT {sID} as sID, '{timeStamp}' as 'modified', '{table}' as 'table', {rowID} as 'rowID', "
        f"modified as 'created', {isBot} as isBot, '{attribute}' as 'attribute', {attribute} as 'tValue' "
        f"FROM {table} WHERE {PK} = {rowID}"
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
