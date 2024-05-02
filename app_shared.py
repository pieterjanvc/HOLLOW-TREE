# ******************************************************
# ----------- SCUIRREL + ACCORNS SHARED CODE -----------
# ******************************************************

# All variables and functions below are shared across different session
# This means none of these functions are reactive
# https://shiny.posit.co/py/docs/express-in-depth.html#shared-objects

# General
import os
import sqlite3
from datetime import datetime
import pandas as pd
import toml
import regex as re
import duckdb
import json
from shutil import move
import toml
from urllib.request import urlretrieve

# Llamaindex
from llama_index.core import VectorStoreIndex, ChatPromptTemplate, SimpleDirectoryReader, StorageContext
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.extractors import TitleExtractor, KeywordExtractor
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.duckdb import DuckDBVectorStore

# -- Shiny
from shiny.express import ui

# -- Other
import nest_asyncio
nest_asyncio.apply()

# --- VARIABLES ---

with open("config.toml", "r") as f:
    config = toml.load(f)

appDB = config["data"]["appDB"]
vectorDB = config["data"]["vectorDB"]
addDemo = any(config["general"]["addDemo"] == x for x in ["True", "true", "T", 1])
tempFolder = os.path.join(config["data"]["tempFolder"], "")
storageFolder = os.path.join(config["data"]["storageFolder"], "")
allowMultiGuess = any(
    config["general"]["allowMultiGuess"] == x for x in ["True", "true", "T", 1]
)

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")
gptModel = config["LLM"]["gptModel"]
llm = OpenAI(model=gptModel)

if os.environ["OPENAI_API_KEY"] is None:
    raise ValueError(
        "There is no OpenAI API key stored in the the OPENAI_API_KEY environment variable"
    )

# # Check if there are topics to discuss before proceeding
# conn = sqlite3.connect(appDB)
# topics = pd.read_sql_query(
#     "SELECT * FROM topic WHERE archived = 0 AND tID IN"
#     "(SELECT DISTINCT tID from concept WHERE archived = 0)",
#     conn,
# )

# if topics.shape[0] == 0:
#     raise ValueError(
#         "There are no active topics with at least one concept in the database."
#         " Please run the admin app first"
#     )
# conn.close()

### --- APP WIDE FUNCTIONS ---
def dt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def inputCheck(input):
    if re.search(r"(?=(.*[a-zA-Z0-9]){6,}).*", input):
        return True
    else:
        False

### --- ACCORN FUNCTIONS ---

# Database to store app data (this is not the vector database!)
def createAppDB(DBpath, addDemo=False):
    if os.path.exists(DBpath):
        return (1, "Database already exists. Skipping")

    # Create a new database from the SQL file
    with open("appData/createAppDB.sql", "r") as file:
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
        (
            "DNA: Composed of adenine (A), cytosine (C), guanine (G), and thymine (T)",
        ),
        ("Genes: Hold code for specific proteins",),
        ("RNA: Composed of nucleotides (including uracil, U); Single-stranded",),
        (
            "Transcription: RNA polymerase unwinds DNA double helix; Synthesizes complementary RNA strand",
        ),
        ("Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm",),
        ("RNA splicing: Removes introns; Retains exons",),
        ("Translation: Occurs in ribosomes; Deciphers mRNA to assemble protein",),
        (
            "Codons: Three-nucleotide sequences; Specify amino acids or signal start/termination of translation",
        ),
        ("Amino acids: Building blocks of proteins; Linked by peptide bonds",),
        ("Protein folding: Adopts specific three-dimensional structure",),
        (
            "Post-translational modifications: Addition of chemical groups; Cleavage of specific segments",
        ),
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
        with open("appData/expandVectorDB.sql", "r") as file:
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
        "INSERT INTO keyword(kID, fID, keyword) "
        f"VALUES(nextval('seq_kID'),'{fID}', ?)",
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

### --- SCUIRREL FUNCTIONS ---

# Load the vector index from storage
vector_store = DuckDBVectorStore.from_local(vectorDB)
index = VectorStoreIndex.from_vector_store(vector_store)


# Adapt the chat engine to the topic
def chatEngine(topic, concepts, cIndex, eval):
    # TUTORIAL Llamaindex + Prompt engineering
    # https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb
    # https://docs.llamaindex.ai/en/stable/examples/customization/prompts/chat_prompts/

    # The two strings below have not been altered from the defaults set by llamaindex,
    # but can be if needed
    qa_prompt_str = (
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Given the context information and not prior knowledge, "
        "answer the question: {query_str}\n"
    )

    refine_prompt_str = (
        "We have the opportunity to refine the original answer "
        "(only if needed) with some more context below.\n"
        "------------\n"
        "{context_msg}\n"
        "------------\n"
        "Given the new context, refine the original answer to better "
        "answer the question: {query_str}. "
        "If the context isn't useful, output the original answer again.\n"
        "Original Answer: {existing_answer}"
    )

    cDone = (
        ""
        if cIndex == 0
        else "These concepts were already covered successfully:\n* "
        + "\n* ".join(concepts.head(cIndex)["concept"])
    )

    cToDo = "The following concepts still need to be discussed:\n* " + "\n* ".join(
        concepts[cIndex:]["concept"]
    )

    progress = (
        "\nBased on the conversation it seems you need to explore the current topic "
        + f'a bit more as you noted the following: {eval["comment"]}\n'
        if int(eval["score"]) < 3
        else ""
    )

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                f"""You (MENTOR) are chatting with a student (STUDENT) to evaluate their understanding of the following topic: 
{topic}
----
{cDone}\n\n
{cToDo}
---- 

The current focus of the conversation is on the following concept: 
{concepts.iloc[cIndex]["concept"]}
{progress}
Remember that you are not lecturing, i.e. giving / asking definitions or giving away all the concepts.
Rather, you will ask a series of questions and use the student's answers to refine your next question 
according to their current understanding.
Try to make the student think and reason critically, but do help out if they get stuck. 
You will adapt the conversation until you feel the there are no more mistakes and there is basic understanding of the concept.
Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!"""
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=qa_prompt_str),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                """
If necessary, make edits to ensure the following:
- Do not keep repeating the topic title in your answer, focus on what's currently going on
- You should stay on topic, and make sure all sub-concepts are evaluated 
(but don't give them away accidentally!)
- If a user seems confused or does not know something, you should explain some of the theory 
in light of their current perceived knowledge
- Make sure you make the user think for themselves, but don't make it frustrating
- Double check if the latest user query does not contain conceptual or jargon errors and address them if needed
- You can add some fun facts based on the provided background if appropriate to keep the conversation
interesting 
"""
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=llm,
    )


# Adapt the chat engine to the topic
def progressCheckEngine(conversation, topic, concepts, cIndex):
    cDone = (
        ""
        if cIndex == 0
        else "These concepts were already covered successfully:\n* "
        + "\n* ".join(concepts.head(cIndex)["concept"])
    )

    cToDo = "The following concepts still need to be discussed:\n* " + "\n* ".join(
        concepts[cIndex:]["concept"]
    )

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                f"""You are monitoring a conversation between a tutor (TUTOR) and a student (STUDENT) on following topic:  
{topic}

{cDone}\n\n
{cToDo}

The conversation is currently focused on the following concept: 
{concepts.iloc[cIndex]["concept"]}

{conversation}

----

With this information, you have to decide if the STUDENT demonstrated enough understanding 
of the current concept to move on to the next one. 
You do this by outputting a numeric score with the following rubric:
* 1: No demonstration of understanding yet
* 2: Some understanding, but still incomplete or with mistakes warranting more discussion 
* 3: Basics of the concept seem to be understood and we might be able to move on
* 4: Clear demonstration of understanding

In addition you will add a short comment, based on the conversation and current concept, 
about what the STUDENT understands but more importantly what they still struggle with (if score < 4).

Please output your score in the following format:"""
                r'{{"score": <int>, "comment": "<>"}}'
            ),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                r'Make sure the output is in the following format: {{"score": <int>, "comment": "<>"}}'
            ),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=llm,
    )


# Function to register the end of a discussion in the DB
def endDiscussion(cursor, dID, messages, timeStamp=dt()):
    _ = cursor.execute(f'UPDATE discussion SET end = "{timeStamp}" WHERE dID = {dID}')
    # Executemany is optimised in such a way that it can't return the lastrowid.
    # Therefor we insert the last message separately as we need to know the ID
    msg = messages.astuple(
        ["cID", "isBot", "timeStamp", "content", "pCode", "pMessage"]
    )
    if len(msg) > 1:
        _ = cursor.executemany(
            f"INSERT INTO message(dID,cID,isBot,timestamp,message,progressCode,progressMessage)VALUES({dID}, ?, ?, ?, ?, ?, ?)",
            msg[:-1],
        )
    _ = cursor.execute(
        f"INSERT INTO message(dID,cID,isBot,timestamp,message,progressCode,progressMessage)VALUES({dID}, ?, ?, ?, ?, ?, ?)",
        msg[-1],
    )
    # If a chat issue was submitted, update the temp IDs to the real ones
    idShift = cursor.lastrowid - messages.id + 1
    if cursor.execute(f"SELECT fcID FROM feedback_chat WHERE dID = {dID}").fetchone():
        _ = cursor.execute(
            f"UPDATE feedback_chat_msg SET mID = mID + {idShift} WHERE fcID IN "
            f"(SELECT fcID FROM feedback_chat WHERE dID = {dID})"
        )


# --- CLASSES

# Messages and conversation
class Conversation:
    def __init__(self):
        self.id = 0
        columns = {
            "id": int,
            "cID": int,
            "isBot": int,
            "timeStamp": str,
            "content": str,
            "pCode": str,
            "pMessage": str,
        }
        self.messages = pd.DataFrame(columns=columns.keys()).astype(columns)

    def add_message(
        self,
        cID: int,
        isBot: int,
        content: str,
        pCode: int = None,
        pMessage: str = None,
        timeStamp: str = None,
    ):
        timeStamp = timeStamp if timeStamp else dt()
        self.messages = pd.concat(
            [
                self.messages,
                pd.DataFrame.from_dict(
                    {
                        "id": [self.id],
                        "cID": [cID],
                        "timeStamp": [timeStamp],
                        "isBot": [isBot],
                        "content": [content],
                        "pCode": [pCode],
                        "pMessage": [pMessage],
                    }
                ),
            ],
            ignore_index=True,
        )
        self.id += 1

    def addEval(self, score, comment):
        self.messages.at[self.messages.index[-1], "pCode"] = score
        self.messages.at[self.messages.index[-1], "pMessage"] = comment

    def astuple(self, order=None):
        if order is not None and (
            set(["cID", "isBot", "timeStamp", "content", "pCode", "pMessage"])
            != set(order)
        ):
            raise ValueError("messages order not correct")
        out = self.messages.drop(columns=["id"])
        if order:
            out = out[order]
        return [tuple(x) for x in out.to_numpy()]
