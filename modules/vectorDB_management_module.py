# ------ Vector DB Module ------
# ------------------------------

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# -- General
import asyncio

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, req
from htmltools import HTML, div

# --- UI ---


@module.ui
def vectorDB_management_ui():
    return [
        div(
            ui.card(
                HTML(
                    "<i>Welcome to ACCORNS, the Admin Control Center Overseeing RAG Needed for SCUIRREL!<br>"
                    "In order to get started, please add at least one file to the vector database</i>"
                )
            ),
            id="blankDBMsg",
            style="display: none;",
        ),
        # Tables of the files that are in the DB
        ui.card(
            ui.card_header("Vector database files"), ui.output_data_frame("filesTable")
        ),
        ui.panel_conditional(
            "output.fileInfo != ''",
            ui.card(
                ui.card_header("File info"), 
                ui.output_ui("fileInfo"),
                id="fileInfoCard"
            ),
        ),
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
    ]


# --- Server ---
@module.server
def vectorDB_management_server(
    input: Inputs, output: Outputs, session: Session, user, pool
):
    conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
    files = shared.pandasQuery(conn, query='SELECT * FROM "file"')
    conn.close()
    if files.shape[0] == 0:
        index = None
        shared.elementDisplay("blankDBMsg", "s", session, alertNotFound=False)
    else:
        index = shared.getIndex(postgresUser=shared.postgresAccorns)

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
        shared.elementDisplay("uiUploadFile", "h", session, alertNotFound=False)
        # TODO add nice loading animation https://codepen.io/nzbin/pen/GGrXbp
        ui.insert_ui(
            HTML(
                f'<div id=processFile><i>Processing {input.newFile()[0]["name"]}</i></div>'
            ),
            "#uiUploadFile",
            "afterEnd",
        )

    def updateVectorDB_task(newFile, vectorDB, storageFolder, newFileName):
        return accorns_shared.addFileToDB(
            newFile=newFile,
            shinyToken=session.id,
            vectorDB=vectorDB,
            storageFolder=storageFolder,
            newFileName=newFileName,
        )

    # Add the file to the vector database
    @reactive.extended_task
    async def updateVectorDB(newFile, vectorDB, storageFolder, newFileName):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            pool, updateVectorDB_task, newFile, vectorDB, storageFolder, newFileName
        )

    # Process the result of adding the file to the vector database
    @reactive.effect
    def _():
        insertionResult = updateVectorDB.result()[0]

        if insertionResult == 0:
            msg = "File successfully added to the vector database"
        elif insertionResult == 1:
            msg = "A file with the same name already exists. Please rename the file and try again"
        else:
            msg = "Not a valid file type. Please upload a .csv, .pdf, .docx, .txt, .md, .epub, .ipynb, .ppt or .pptx file"

        ui.notification_show(msg)
        # ui.modal_show(ui.modal(msg, title="Success" if insertionResult == 0 else "Issue"))

        # Get the new file info
        conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
        getFiles = shared.pandasQuery(conn, 'SELECT * FROM "file"')
        conn.close()

        files.set(getFiles)
        index.set(shared.getIndex(postgresUser=shared.postgresAccorns))

        shared.elementDisplay("uiUploadFile", "s", session, alertNotFound=False)
        ui.remove_ui("#processFile")

    # Get file details
    @render.ui
    @reactive.calc
    def fileInfo():
        if filesTable.data_view(selected=True).empty:
            # elementDisplay("fileInfoCard", "h")
            return HTML("")

        info = files().iloc[filesTable.data_view(selected=True).index[0]]

        conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
        keywords = shared.pandasQuery(
            conn, f'SELECT "keyword" FROM "keyword" WHERE "fID" = {int(info.fID)}'
        )
        conn.close()
        keywords = "; ".join(keywords["keyword"])

        return ui.TagList(HTML(
            f"<h4>{info.fileName}</h4><ul>"
            f"<li><b>Summary title</b> <i>(AI generated)</i>: {info.title}</li>"
            f"<li><b>Summary subtitle</b> <i>(AI generated)</i>: {info.subtitle}</li>"
            f"<li><b>Uploaded</b>: {info.created}</li></ul>"
            "<p><b>Top-10 keywords extracted from document</b> <i>(AI generated)</i></p>"
            f"{keywords}"
        ), ui.input_action_button("deleteFile","Delete file", width="auto"),)
    
    @reactive.effect
    @reactive.event(input.deleteFile)
    def _():
        if user.get()["adminLevel"] < 3:
            # Get the userid of the file owner
            shinyToken = files().iloc[filesTable.data_view(selected=True).index[0]].shinyToken
            conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
            shinyToken = shared.pandasQuery(
                conn, 
                'SELECT "uID" FROM "session" WHERE "shinyToken" = ?', 
                (shinyToken,)
            )
            conn.close()
            if user.get()["uID"] not in shinyToken["uID"].values:
                ui.notification_show("Only admins can delete files uploaded by others")
                return
        
        fileName = files().iloc[filesTable.data_view(selected=True).index[0]].fileName
        ui.modal_show(
            ui.modal(
                HTML(f"<p style='color:red;'>{fileName}</p>"
                 "<p>If you sure you want to delete this file from the vector database,"
                 "type <b>DELETE</b> in all caps in the text box below and click confirm</p><br>"),
                ui.input_text("deleteConfirm", label="Type DELETE in all caps"),
                title="Delete file",                
                footer=[
                    ui.input_action_button("confirmDelete", "Confirm"),
                    ui.modal_button("Cancel"),
                ],
            )
        )
    
    @reactive.effect
    @reactive.event(input.confirmDelete)
    def _():
        if input.deleteConfirm() == "DELETE":
            file = files().iloc[filesTable.data_view(selected=True).index[0]]
            conn = shared.vectorDBConn(postgresUser=shared.postgresAccorns)
            # Delete the vectors
            cursor = conn.cursor()
            # The syntax is different between DuckDB and PostgreSQL for JSON extraction
            if shared.remoteAppDB:
                _ = cursor.execute(
                    ("DELETE FROM data_document WHERE metadata_ ->> 'file_name' = %s"),
                    parameters=(file.fileName,),                
                )
            else:
                _ = cursor.execute(
                    ('DELETE FROM "documents" WHERE '
                    "CAST(json_extract(metadata_, '$.file_name') as VARCHAR) = ?"),
                    parameters=('"'+ file.fileName + '"',),                
                )

            _ = shared.executeQuery(
                cursor,
                'DELETE FROM "keyword" WHERE "fID" = ?',
                (int(file.fID),),                
            )
            _ = shared.executeQuery(
                cursor,
                'DELETE FROM "file" WHERE "fID" = ?',
                (int(file.fID),),                
            )            
            shared.elementDisplay("fileInfoCard", "h", session, alertNotFound=False)
            files.set(shared.pandasQuery(conn, query='SELECT * FROM "file"'))            
            conn.commit()
            conn.close()
            ui.notification_show("File successfully deleted")
            ui.modal_remove()
        else:
            ui.notification_show("Incorrect input. Please type DELETE in all caps to confirm deletion")
    

    return index, files
