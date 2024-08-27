# ************************************************
# ----------- SCUIRREL APP SHARED CODE -----------
# ************************************************

from shared import shared

# General
import os
import pandas as pd
import toml

# --- VARIABLES ---

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

with open(os.path.join(curDir, "scuirrel_config.toml"), "r") as f:
    config = toml.load(f)

allowMultiGuess = config["general"]["allowMultiGuess"]

if not os.path.exists(shared.vectorDB) and not shared.remoteAppDB:
    raise ConnectionError("The vector database was not found. Please run ACCORNS first")

# Check if there are topics to discuss before proceeding
conn = shared.appDBConn(shared.postgresScuirrel)
topics = shared.pandasQuery(
    conn,
    'SELECT * FROM "topic" WHERE "status" = 0 AND "tID" IN'
    '(SELECT DISTINCT "tID" from "concept" WHERE "status" = 0)',
)

if topics.shape[0] == 0:
    raise ValueError(
        "There are no active topics with at least one concept in the database."
        " Please run the ACCORNS app first"
    )
conn.close()


# Function to register the end of a discussion in the DB
def endDiscussion(cursor, dID, messages, timeStamp=shared.dt()):
    _ = shared.executeQuery(
        cursor, 'UPDATE "discussion" SET "end" = ? WHERE "dID" = ?', (timeStamp, dID)
    )
    # Executemany is optimised in such a way that it can't return the lastrowid.
    # Therefor we insert the last message separately as we need to know the ID
    msg = messages.astuple(
        ["cID", "isBot", "timeStamp", "content", "pCode", "pMessage"]
    )
    mID = shared.executeQuery(
        cursor,
        'INSERT INTO "message"("dID","cID","isBot","timestamp","message","progressCode","progressMessage") '
        f"VALUES({dID}, ?, ?, ?, ?, ?, ?)",
        msg,
        lastRowId="mID",
    )
    # If a chat issue was submitted, update the temp IDs to the real ones
    idShift = int(mID) - messages.id + 1
    _ = shared.executeQuery(
        cursor, 'SELECT "fcID" FROM "feedback_chat" WHERE "dID" = ?', (dID,)
    )
    if cursor.fetchone():
        _ = shared.executeQuery(
            cursor,
            'UPDATE "feedback_chat_msg" SET "mID" = "mID" + ? WHERE "fcID" IN '
            '(SELECT "fcID" FROM "feedback_chat" WHERE "dID" = ?)',
            (idShift, dID),
        )
