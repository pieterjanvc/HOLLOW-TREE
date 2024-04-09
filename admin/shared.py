# *******************************************
# ----------- ADMIN APP SHARED CODE ---------
# *******************************************

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

# -- Llamaindex
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore

# --- Global variables

with open("config.toml", "r") as f:
    config = toml.load(f)

appDB = config["data"]["appDB"]
vectorDB = config["data"]["vectorDB"]
# keep files user uploads, if set to None, original not kept
storageFolder = config["data"]["storageFolder"]

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
def createAppDB(DBpath, sqlFile="appData/createDB.sql", addDemo=True):
    if os.path.exists(DBpath):
        return (1, "Database already exists. Skipping")

    # Create a new database from the SQL file
    with open(sqlFile, "r") as file:
        query = file.read().replace("\n", " ").replace("\t", "").split(";")

    conn = sqlite3.connect(DBpath)
    cursor = conn.cursor()

    for x in query:
        _ = cursor.execute(x)

    # Add the anonymous user and main admin
    _ = cursor.execute(
        "INSERT INTO user(username, isAdmin, created)"
        f'VALUES("anonymous", 0, "{dt()}"), ("admin", 1, "{dt()}")'
    )

    if not addDemo:
        conn.commit()
        conn.close()
        return

    # Add a test topic (to be removed later)
    topic = "The central dogma of molecular biology"
    _ = cursor.execute(
        "INSERT INTO topic(topic, created)" f'VALUES("{topic}", "{dt()}")'
    )
    tID = cursor.lastrowid

    # Add topic concepts (to be removed later)
    concepts = [
        ("DNA is made up of 4 bases that encode all information needed for life",),
        ("A protein is encoded in the DNA as a seqeunce of bases",),
        ("To create a protein, you first have to transcribe the DNA into RNA",),
        (
            "RNA is similar to DNA but instead of ACTG it has ACUG and is single stranded",
        ),
        ("RNA is processed by removing introns, keeping only exons",),
        (
            "RNA is translated into protein. 3 RNA bases form a codon, and each codon)"
            "represents an amino acid, or the start / stop of the seqeunce",
        ),
        (
            "Based on RNA codons, amino acids are chained together into a single protrein strand",
        ),
        (
            "The protein will fold into a 3D shape to become functional,"
            "with optional post-translational processing",
        ),
    ]
    _ = cursor.executemany(
        "INSERT INTO concept(tID, concept, created) " f'VALUES({tID}, ?, "{dt()}")',
        concepts,
    )
    conn.commit()
    conn.close()

    return (0, "Creation completed")


# newFile = "appData/Central_dogma_of_molecular_biology.pdf"
# newFile = "appData/Mendelian inheritance.txt"
# vectorDB = "appData/testDB.duckdb"
# appDB = "appData/appDB.db"
# storageFolder = "appData/uploadedFiles"
# newFileName = None


# Create DuckDB vector database and add files
def addFileToDB(newFile, vectorDB, appDB, storageFolder=None, newFileName=None):
    if not os.path.exists(appDB):
        raise ConnectionError("The appDB was not found")

    if not os.path.exists(newFile):
        raise ConnectionError(f"The newFile was not found at {newFile}")

    # Move the file to permanent storage if requested
    if storageFolder is not None:
        if not os.path.exists(storageFolder):
            os.makedirs(storageFolder)

        newFileName = os.path.basename(newFile) if newFileName is None else newFileName
        newFilePath = os.path.join(storageFolder, "") + newFileName

        if os.path.exists(newFilePath):
            return (1, "A file with this name already exists. Skipping")

        move(newFile, newFilePath)
        newFile = newFilePath

    newData = SimpleDirectoryReader(input_files=[newFile]).load_data()

    # Build the vector store https://docs.llamaindex.ai/en/stable/examples/vector_stores/DuckDBDemo/?h=duckdb
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

    # Summarise everything using the LLM and add it to the DB
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

    conn = sqlite3.connect(appDB)
    cursor = conn.cursor()
    _ = cursor.execute(
        (
            'INSERT INTO file(fileName, title, subtitle, created) '
            f'VALUES("{fileName}", "{docSum["title"]}", "{docSum["subtitle"]}", "{dt()}")'
        )
    )
    fID = cursor.lastrowid
    _ = cursor.executemany(
        "INSERT INTO keyword(fID, keyword) " f'VALUES("{fID}", ?)',
        [(item,) for item in docSum["keywords"]],
    )
    conn.commit()
    conn.close()

    return (0, "Completed")
