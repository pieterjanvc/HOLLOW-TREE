# ------ Vector DB Module ------
# ------------------------------

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# -- General
import os

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, req
from htmltools import HTML, div

# -- Llamaindex
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.duckdb import DuckDBVectorStore
from llama_index.vector_stores.postgres import PGVectorStore


# --- Functions ---
def getIndex(remote = shared.remoteAppDB):
    if remote:
            vectorStore = PGVectorStore.from_params(
                host=shared.postgresHost,
                port=shared.postgresPort,
                user=accorns_shared.postgresUser,
                password=os.environ.get("POSTGRES_PASS_ACCORNS"),
                database="vector_db",
                table_name="document",
                embed_dim=1536,  # openai embedding dimension
            )
            return VectorStoreIndex.from_vector_store(vectorStore)
    else:
        return VectorStoreIndex.from_vector_store(
            DuckDBVectorStore.from_local(shared.vectorDB)
        )

# --- UI ---

@module.ui
def vectorDB_management_ui():
    return ([
            div(ui.card(
                HTML(
                    "<i>Welcome to ACCORNS, the Admin Control Center Overseeing RAG Needed for SCUIRREL!<br>"
                    "In order to get started, please add at least one file to the vector database</i>"
                )), id="blankDBMsg", style="display: none;"),
            # Tables of the files that are in the DB
            ui.card(
                ui.card_header("Vector database files"),
                ui.output_data_frame("filesTable")
            ),
            ui.panel_conditional("output.fileInfo != ''",
                ui.card(
                ui.card_header("File info"),
                ui.output_ui("fileInfo"),
                id="fileInfoCard"            
            )),
            # Option to add new files
            ui.card(
                ui.card_header("Upload a new file"),
                div(
                    ui.input_file(
                        "newFile",
                        "Pick a file",
                        width="100%",
                        accept=[
                            ".csv",
                            ".pdf",
                            ".docx",
                            ".txt",
                            ".md",
                            ".epub",
                            ".ipynb",
                            ".ppt",
                            ".pptx",
                        ],
                    ),
                    id="uiUploadFile",
                ),
            ),
            
    ])

# --- Server ---
@module.server
def vectorDB_management_server(input: Inputs, output: Outputs, session: Session, uID):

    conn = shared.vectorDBConn()
    files = shared.pandasQuery(conn, query='SELECT * FROM "file"')
    conn.close()
    if files.shape[0] == 0:
        index = None
        shared.elementDisplay("blankDBMsg", "s", session)
    else:
        index = getIndex()
    
    files = reactive.value(files)
    index = reactive.value(index)
    
    # Display the files in the vector database as a table
    @render.data_frame
    def filesTable():
        req(not files.get().empty)
        return render.DataTable(
            files.get()[["title", "fileName"]],
            width="100%",
            selection_mode="row",
        )

    # Upload a new file
    @reactive.effect
    @reactive.event(input.newFile)
    def _():
        # Move the file to the uploadedFiles folder
        updateVectorDB(
            input.newFile()[0]["datapath"],
            shared.vectorDB,
            accorns_shared.storageFolder,
            input.newFile()[0]["name"],
        )
        shared.elementDisplay("uiUploadFile", "h", session)
        # TODO add nice loading animation https://codepen.io/nzbin/pen/GGrXbp
        ui.insert_ui(
            HTML(
                f'<div id=processFile><i>Processing {input.newFile()[0]["name"]}</i></div>'
            ),
            "#uiUploadFile",
            "afterEnd",
        )


    # Add the file to the vector database
    @reactive.extended_task
    async def updateVectorDB(newFile, vectorDB, storageFolder, newFileName):
        print("Start adding file...")
        return accorns_shared.addFileToDB(
            newFile=newFile,
            vectorDB=vectorDB,
            storageFolder=storageFolder,
            newFileName=newFileName,
        )

    # Process the result of adding the file to the vector database
    @reactive.effect
    def _():
        insertionResult = updateVectorDB.result()[0]

        if insertionResult == 0:
            msg = "File successfully added to the vector database"
        elif insertionResult == 1:
            msg = "A file with the same name already exists. Skipping upload"
        else:
            msg = "Not a valid file type. Please upload a .csv, .pdf, .docx, .txt, .md, .epub, .ipynb, .ppt or .pptx file"

        ui.notification_show(msg)
        #ui.modal_show(ui.modal(msg, title="Success" if insertionResult == 0 else "Issue"))

        # Get the new file info
        conn = shared.vectorDBConn()
        getFiles = shared.pandasQuery(conn, 'SELECT * FROM "file"')                
        conn.close()

        files.set(getFiles)
        index.set(getIndex())

        shared.elementDisplay("uiUploadFile", "s", session)
        ui.remove_ui("#processFile")

    # Get file details
    @render.ui
    @reactive.calc
    def fileInfo():
        if filesTable.data_view(selected=True).empty:
            # elementDisplay("fileInfoCard", "h")
            return HTML("")

        info = files().iloc[filesTable.data_view(selected=True).index[0]]

        conn = shared.vectorDBConn()
        keywords = shared.pandasQuery(
            conn, f'SELECT "keyword" FROM "keyword" WHERE "fID" = {int(info.fID)}'
        )
        conn.close()
        keywords = "; ".join(keywords["keyword"])

        return HTML(
            f"<h4>{info.fileName}</h4><ul>"
            f"<li><b>Summary title</b> <i>(AI generated)</i>: {info.title}</li>"
            f"<li><b>Summary subtitle</b> <i>(AI generated)</i>: {info.subtitle}</li>"
            f"<li><b>Uploaded</b>: {info.created}</li></ul>"
            "<p><b>Top-10 keywords extracted from document</b> <i>(AI generated)</i></p>"
            f"{keywords}"
        )
    
    return index, files
