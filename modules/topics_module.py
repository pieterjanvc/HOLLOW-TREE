# ------ Topics Module -----
# --------------------------

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, module
from htmltools import HTML, div

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# --- Functions & variables ---
topicStatus = {0: "Active", 1: "Draft", 2: "Archived"}

def topicsQuery(conn, gID):
    return shared.pandasQuery(
            conn,
            (
                'SELECT t.* FROM "topic" AS t, "group_topic" AS gt '
                'WHERE t."tID" = gt."tID" AND gt."gID" = ? '
                'ORDER BY t."topic"'
            ),
            (int(gID),),
        )

# Update the list of topics shown in the select input
def tDisplayNames(topics, input, session, selected = None):

    selected = selected if selected is not None else input.tID()
    showArchived = input.tShowArchived()    
    
    topicsList = topics.copy()

    # Add the status to the topic name
    topicsList["topic"] = topicsList.apply(
        lambda x: f"({topicStatus[x['status']]}) {x['topic']}" if x["status"] != 0 else x["topic"],
        axis=1,
    )

    # Filter out archived topics if needed
    if not showArchived:
        topicsList = topicsList[topicsList["status"] != 2]    

    # Hide or show the edit and status buttons if there are no topics to show
    if topicsList.shape[0] == 0:
        selected = None
        # shared.elementDisplay(session, {"tEdit": "d", "tStatus": "h"})
    else:
        topicsList = topicsList.sort_values(["status", "topic"])
        if selected:
            selected = str(topicsList["tID"].iloc[0] if int(selected) not in list(topicsList["tID"]) else selected)
        # shared.elementDisplay(session, {"tEdit": "e", "tStatus": "s"})   

    # Update the select input with the new topics
    ui.update_select("tID", choices=dict(zip(topicsList["tID"], topicsList["topic"])),
                         selected=selected)
    
    return

# --- UI ---
@module.ui
def topics_ui():
    return [

        # Select, add or archive a topic
        ui.card(
            ui.card_header("Topic"),
            ui.input_select("gID", "Group", choices={}, width="400px"),
            ui.panel_conditional(
                "input.gID",
                div(shared.customAttr(ui.input_select("tID", "Topic", choices=[], width="400px"),
                    {'style': 'display:inline-block'}),       
                    shared.customAttr(ui.input_checkbox("tShowArchived", "Show archived", value=False,),
                                        {'style': 'display:inline-block'},)),                           
                div(
                    ui.input_action_button("tAdd", "Add new", width="180px"),
                    ui.input_action_button("tEdit", "Edit name", width="180px"),
                ),
                ui.input_radio_buttons("tStatus", "Change topic status", choices=topicStatus,
                                        inline=True, selected=None),
            ),
        ),
        # Table of concepts per topic with option to add, edit or archive
        ui.panel_conditional(
            "input.tID",
            ui.card(
                ui.card_header("Concepts related to the topic"),
                ui.output_data_frame("conceptsTable"),
                div(
                    ui.input_action_button("cAdd", "Add new", width="180px"),
                    ui.input_action_button("cEdit", "Edit selected", width="180px"),
                    ui.input_action_button(
                        "cArchive", "Archive selected", width="180px"
                    ),
                    ui.input_action_button("cReorder", "Reorder", width="180px"),
                    style="display:inline",
                ),
                HTML("<i>Concepts are specific facts or pieces of information you want SCUIRREL to check with your students. "
                    "You can be very brief, as all context will be retrieved from the database of documents. "
                    "Don't be too broad, split into multiple topics if needed. "
                    "SCUIRREL will walk through the concepts in order, so kep that in mind</i>"),                
        ),
    )
    ]


# --- Server ---
@module.server
def topics_server(
    input: Inputs, output: Outputs, session: Session, sID, user, groups, postgresUser
):
    topics = reactive.value(None)
    concepts = reactive.value(None)

    @reactive.effect
    @reactive.event(groups)
    def _():

        if groups.get().shape[0] == 0:
            shared.elementDisplay(session, {"tAdd": "d", "tEdit": "d", "tStatus": "h", "tShowArchived": "d"},
                                  alertNotFound=False)
            shared.inputNotification(
                session, "gID", "Create a group (groups tab) before adding topics"
            )
            return
        else:
            shared.elementDisplay(session, {"tAdd": "e", "tEdit": "e", "tStatus": "s", "tShowArchived": "e"},
                                  alertNotFound=False)
            shared.inputNotification(session, "gID", show=False)

        ui.update_select(
            "gID",
            choices=dict(
                zip(groups.get()["gID"].tolist(), groups.get()["group"].tolist())
            ),
        )

    @reactive.effect
    @reactive.event(input.gID)
    def _():
        # req(user.get()["uID"] != 1)

        # Get all active topics from the accorns database
        conn = shared.appDBConn(postgresUser=postgresUser)
        topicsList = topicsQuery(conn, input.gID())
        conn.close()

        # IN case there are no topics (including archived) hide the show archived button
        if topicsList.shape[0] == 0:
            shared.elementDisplay(session, {"tShowArchived": "h"})
        else:
            shared.elementDisplay(session, {"tShowArchived": "s"})

        tDisplayNames(topicsList, input, session)
        topics.set(topicsList)

    @reactive.effect
    @reactive.event(input.tShowArchived, ignore_init=True)
    def _():
        
        tDisplayNames(topics.get(), input, session)

    # --- Add topic - modal popup
    @reactive.effect
    @reactive.event(input.tAdd)
    def _():
        m = ui.modal(
            ui.tags.p(
                HTML(
                    "<i>Keep the topic name short.<br>"
                    "Make sure the topic can be covered by ~ 4-8 concepts, otherwise split it up."
                    "The AI might struggle with broad topics that cover many concepts</i>"
                )
            ),
            ui.input_text("ntTopic", "New topic:", width="100%"),
            ui.input_text("ntDescr", "Description (optional):", width="100%"),
            title="Add a topic",
            easy_close=True,
            size="l",
            footer=ui.TagList(
                ui.input_action_button("ntAdd", "Add"), ui.modal_button("Cancel")
            ),
        )
        ui.modal_show(m)

    # When add button is clicked
    @reactive.effect
    @reactive.event(input.ntAdd)
    def _():
        # Only proceed if the input is valid
        if not shared.inputCheck(input.ntTopic()):
            shared.inputNotification(session, "ntDescr", "New topic must be at least 6 characters")
            return
        else:
            shared.inputNotification(session, "ntDescr", show=False)
        
        # Add new topic to DB
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        dt = shared.dt()
        tID = shared.executeQuery(
            cursor,
            'INSERT INTO "topic"("sID", "topic", "created", "modified", "description")'
            "VALUES(?, ?, ?, ?, ?)",
            (sID, input.ntTopic(), dt, dt, input.ntDescr()),
            lastRowId="tID",
        )

        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "group_topic"("gID", "tID", "uID", "added") VALUES(?, ?, ?, ?)',
            (int(input.gID()), tID, int(user.get()["uID"]), dt),
        )
        newTopics = topicsQuery(conn, input.gID())
        conn.commit()
        conn.close()

        # Update the topics select input
        tDisplayNames(newTopics, input, session, selected = tID)
       
        topics.set(newTopics)
        ui.modal_remove()

    # --- Edit an existing topic - modal popup
    @reactive.effect
    @reactive.event(input.tEdit)
    def _():
        if input.tID() is not None:
            topic = topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0][
                "topic"
            ]
            m = ui.modal(
                ui.tags.p(
                    HTML(
                        "<i>Make sure to only make small edits that do not change the topic. "
                        "Otherwise add or delete instead</i>"
                    )
                ),
                ui.input_text("etInput", "Updated topic:", width="100%", value=topic),
                title="Edit an existing topic",
                easy_close=True,
                size="l",
                footer=ui.TagList(
                    ui.input_action_button("etEdit", "Update"),
                    ui.modal_button("Cancel"),
                ),
            )
            ui.modal_show(m)

    # When edit button is clicked
    @reactive.effect
    @reactive.event(input.etEdit)
    def _():

        # Only proceed if the input is valid
        if not shared.inputCheck(input.etInput()):
            shared.inputNotification(session, "etInput", "A topic must be at least 6 characters")
            return
        else:
            shared.inputNotification(session, "etInput", show=False)

        if (
            topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["topic"]
            == input.etInput()
        ):
            shared.inputNotification(session, "etInput", "No change detected")
            return
        else:
            shared.inputNotification(session, "etInput", show=False)

        # Update the DB
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        # Backup old values
        ts = shared.dt()
        accorns_shared.backupQuery(
            cursor=cursor,
            sID=sID,
            table="topic",
            rowID=input.tID(),
            attribute="topic",
            dataType="str",
            isBot=False,
            timeStamp=ts,
        )
        accorns_shared.backupQuery(
            cursor=cursor,
            sID=sID,
            table="topic",
            rowID=input.tID(),
            attribute="sID",
            dataType="int",
            isBot=False,
            timeStamp=ts,
        )

        # Update to new
        _ = shared.executeQuery(
            cursor,
            'UPDATE "topic" SET "sID" = ?, "topic" = ?, "modified" = ? WHERE "tID" = ?',
            (sID, input.etInput(), shared.dt(), input.tID()),
        )         
        conn.commit()
        topicsList = topicsQuery(conn, input.gID())  
        conn.close()

        tDisplayNames(topicsList, input, session)      

        topics.set(topicsList)
        ui.modal_remove()

    # --- Archive a topic - modal popup
    @reactive.effect
    @reactive.event(input.tStatus)
    def _():        

        if input.tID() is None:
            return
        
        statusCode = int(input.tStatus())
        prevStatus = topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["status"]

        if concepts.get().empty and statusCode == 0:
            ui.notification_show("No concepts available for this topic. Please add some before activating the topic")
            ui.update_radio_buttons("tStatus", selected=str(prevStatus))
            return
              
        if statusCode == 1:
            shared.elementDisplay(session, {"tEdit":"e", "cAdd": "s", "cEdit": "s", "cArchive": "s", 
                                            "cReorder": "s"})
            shared.inputNotification(session, "tStatus", show=False)
        else:
            shared.elementDisplay(session, {"tEdit":"d","cAdd": "h", "cEdit": "h", "cArchive": "h", 
                                            "cReorder": "h"})
            shared.inputNotification(session, "tStatus", "<i>The topic Title or Concepts can only be edited when the topic is in 'Draft' status</i>", colour = "blue")
                
        if statusCode == prevStatus:
            return

        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'UPDATE "topic" SET "status" = ?, "modified" = ? WHERE "tID" = ?',
            (statusCode, shared.dt(), input.tID()),
        )
        newTopics = topicsQuery(conn, input.gID())

        conn.commit()
        conn.close()

        tDisplayNames(newTopics, input, session)
        
        topics.set(newTopics)

    # ---- CONCEPTS ----
    @render.data_frame
    def conceptsTable():
        return render.DataTable(
            concepts.get()[["concept"]],
            width="100%",
            selection_mode="row",
            height="auto",
        )

    # --- Add a new concepts - modal popup
    @reactive.effect
    @reactive.event(input.cAdd)
    def _():
        m = ui.modal(
            ui.tags.p(
                HTML(
                    "<i>Concepts are single facts that a student should understand<br>"
                    "There is no need to provide context as this will come from the database</i>"
                )
            ),
            ui.input_text("ncInput", "New concept:", width="100%"),
            title="Add a new concept to the topic",
            easy_close=True,
            size="l",
            footer=ui.TagList(
                ui.input_action_button("ncAdd", "Add"), ui.modal_button("Cancel")
            ),
        )
        ui.modal_show(m)

    # When add button is clicked
    @reactive.effect
    @reactive.event(input.ncAdd)
    def _():
        # Only proceed if the input is valid
        if not shared.inputCheck(input.ncInput()):
            shared.inputNotification(session, "ncInput", "New concept must be at least 6 characters")
            return
        else:
            shared.inputNotification(session, "ncInput", show=False)

        # Add new topic to DB
        order = concepts.get()["order"].tolist()
        order = 1 if len(order) == 0 else max(order) + 1

        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "concept"("sID", "tID", "order", "concept", "created", "modified") VALUES(?, ?, ?, ?, ?, ?)',
            (sID, input.tID(), int(order), input.ncInput(), shared.dt(), shared.dt()),
        )
        conceptList = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "status" = 0 ORDER BY "order"',
        )
        conn.commit()
        conn.close()
        # Update concept table
        concepts.set(conceptList)
        ui.modal_remove()

    # --- Edit an existing concepts - modal popup
    @reactive.effect
    @reactive.event(input.cEdit)
    def _():
        if not conceptsTable.data_view(selected=True).empty:
            concept = conceptsTable.data_view(selected=True).iloc[0]["concept"]
            m = ui.modal(
                ui.tags.p(
                    HTML(
                        "<i>Make sure to only make edits that do not change the concept. "
                        "Otherwise add or delete instead</i>"
                    )
                ),
                ui.input_text("ecInput", "Edit concept:", width="100%", value=concept),
                title="Edit and existing topic",
                easy_close=True,
                size="l",
                footer=ui.TagList(
                    ui.input_action_button("ncEdit", "Update"),
                    ui.modal_button("Cancel"),
                ),
            )
            ui.modal_show(m)

    # When edit button is clicked
    @reactive.effect
    @reactive.event(input.ncEdit)
    def _():
        # Only proceed if the input is valid
        if not shared.inputCheck(input.ecInput()):
            shared.inputNotification(session, "ecInput", "A concept must be at least 6 characters")
            return
        else:
            shared.inputNotification(session, "ecInput", show=False)
        
        concept = conceptsTable.data_view(selected=True).iloc[0]["concept"]

        if concept == input.ecInput():
            shared.inputNotification(session, "ecInput", "No change detected")
            return
        else:
            shared.inputNotification(session, "ecInput", show=False)

        # Update the DB
        cID = concepts.get().iloc[conceptsTable.data_view(selected=True).index[0]][
            "cID"
        ]
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        # Backup old value
        ts = shared.dt()
        accorns_shared.backupQuery(
            cursor=cursor,
            sID=sID,
            table="concept",
            rowID=int(cID),
            attribute="concept",
            dataType="str",
            isBot=False,
            timeStamp=ts,
        )
        accorns_shared.backupQuery(
            cursor=cursor,
            sID=sID,
            table="concept",
            rowID=int(cID),
            attribute="sID",
            dataType="int",
            isBot=False,
            timeStamp=ts,
        )
        # Update to new
        _ = shared.executeQuery(
            cursor,
            'UPDATE "concept" SET "sID" = ?, "concept" = ?, "modified" = ? WHERE "cID" = ?',
            (sID, input.ecInput(), shared.dt(), int(cID)),
        )
        conceptList = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "status" = 0 ORDER BY "order"',
        )
        conn.commit()
        conn.close()
        # Update concept table
        concepts.set(conceptList)
        ui.modal_remove()

    # --- delete a concept (archive) - modal popup
    @reactive.effect
    @reactive.event(input.cArchive)
    def _():
        if conceptsTable.data_view(selected=True).empty:
            return

        cID = concepts.get().iloc[conceptsTable.data_view(selected=True).index[0]][
            "cID"
        ]
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        # Set the status of the concept to archived
        _ = shared.executeQuery(
            cursor,
            'UPDATE "concept" SET "status" = 1, "modified" = ? WHERE "cID" = ?',
            (shared.dt(), int(cID)),
        )
        # Make sure to archive any related quiz questions
        _ = shared.executeQuery(
            cursor,
            'UPDATE "question" SET "status" = 1, "modified" = ? WHERE "cID" = ?',
            (shared.dt(), int(cID)),
        )
        # Get the new list of active concepts
        conceptList = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "status" = 0 ORDER BY "order"',
        )
        conn.commit()
        conn.close()

        concepts.set(conceptList)

    # --- Load concepts when a topic is selected
    @reactive.effect
    @reactive.event(input.tID)
    def _():

        # Hide panel when no topic is available
        if input.tID() is None:
            shared.elementDisplay(session, {"conceptsPanel": "h", "tStatus": "h"},
                                  alertNotFound=False)
            return
        else:
            shared.elementDisplay(session, {"conceptsPanel": "s", "tStatus": "s"},
                                  alertNotFound=False) 

        status = topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["status"]
        if status != 1:
            shared.elementDisplay(session, {"tEdit": "d"})
        else:
            shared.elementDisplay(session, {"tEdit": "e"})

        ui.update_radio_buttons("tStatus", selected=str(status))

        tID = input.tID() if input.tID() else 0
        conn = shared.appDBConn(postgresUser=postgresUser)
        conceptList = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {tID} AND "status" = 0 ORDER BY "order"',
        )
        conn.close()

        concepts.set(conceptList)

    # --- Reorder the concepts - modal popup
    @reactive.effect
    @reactive.event(input.cReorder)
    def _():
        # Limit the number of character in the concept list to 80 followed by ... if cropped
        conceptList = [i[:80] + (i[80:] and "...") for i in concepts.get()["concept"]]
        # Generate a comma separated string of integers as long as the concept list
        defOrder = ",".join([str(i) for i in range(1, len(conceptList) + 1)])
        # Create a numbered list of concepts
        conceptList = ui.tags.ol([ui.tags.li(concept) for concept in conceptList])

        m = ui.modal(
            conceptList,
            ui.input_text("rcNewOrder", "New order:", width="100%", value=defOrder),
            title="Reorder concepts",
            easy_close=True,
            size="l",
            footer=ui.TagList(
                ui.input_action_button("rcUpdate", "Update"),
                ui.modal_button("Cancel"),
            ),
        )
        ui.modal_show(m)

    # When edit button is clicked
    @reactive.effect
    @reactive.event(input.rcUpdate)
    def _():
        # Check if the rcNewOrder contains a comma separated list of integers non repeating and between 1 and the number of concepts
        newOrder = input.rcNewOrder().split(",")
        # Remove all strings that are not integers after whitespace removal
        newOrder = [int(i) for i in newOrder if i.strip().isdigit()]
        # Check if the list is the same length as the concept list and all integers are consecutive if ordered
        if len(set(newOrder)) != concepts.get().shape[0] or not shared.consecutiveInt(
            newOrder
        ):
            shared.inputNotification(session, "rcNewOrder", "Order must be a comma separated list of all integers")
            return
        else:
            shared.inputNotification(session, "rcNewOrder", show=False)
        
        # Reorder the concepts based on the new order
        newConcepts = concepts.get()
        newConcepts["newOrder"] = newOrder
        newConcepts = newConcepts.sort_values("newOrder")

        # Get data frame with only rows where concept order changed
        changedOrder = newConcepts[newConcepts["order"] != newConcepts["newOrder"]]

        # Message if no order changed
        if changedOrder.shape[0] == 0:
            shared.inputNotification(session, "rcNewOrder", "No order change detected")
            return
        else:
            shared.inputNotification(session, "rcNewOrder", show=False)

        # Get the connection to the database
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        ts = shared.dt()
        for _, row in changedOrder.iterrows():
            # Backup old value
            accorns_shared.backupQuery(
                cursor=cursor,
                sID=sID,
                table="concept",
                rowID=row["cID"],
                attribute="order",
                dataType="int",
                isBot=False,
                timeStamp=ts,
            )
        # Update the order of the concept with changedOrder["newOrder"] for changedOrder["cID"]
        _ = shared.executeQuery(
            cursor,
            f'UPDATE "concept" SET "order" = ?, "modified" = \'{ts}\' WHERE "cID" = ?',
            list(changedOrder[["newOrder", "cID"]].itertuples(index=False, name=None)),
        )
        conn.commit()
        conn.close()

        # Replace the order with newOrder and remove the newOrder column
        newConcepts["order"] = newConcepts["newOrder"]
        newConcepts.drop(columns=["newOrder"], inplace=True)

        concepts.set(newConcepts)

        ui.modal_remove()

    return topics, concepts
