# ------ Topics Module -----
# --------------------------

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, req
from htmltools import HTML, div

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# --- UI ---
@module.ui
def topics_ui():
    return ([
       ui.layout_columns(
                # Select, add or archive a topic
                ui.card(
                    ui.card_header("Topic"),
                    ui.input_select("tID", "Pick a topic", choices=[], width="400px"),
                    div(
                        ui.input_action_button("tAdd", "Add new", width="180px"),
                        ui.input_action_button("tEdit", "Edit selected", width="180px"),
                        ui.input_action_button(
                            "tArchive", "Archive selected", width="180px"
                        ),
                    )),
                # Table of concepts per topic with option to add, edit or archive
                ui.panel_conditional("input.tID",
                    ui.card(
                        ui.card_header("Concepts related to the topic"),
                        ui.output_data_frame("conceptsTable"),
                        div(
                            ui.input_action_button("cAdd", "Add new", width="180px"),
                            ui.input_action_button("cEdit", "Edit selected", width="180px"),
                            ui.input_action_button(
                                "cArchive", "Archive selected", width="180px"
                            ),
                            style="display:inline",
                        ),
                        HTML(
                            "<i>Concepts are specific facts or pieces of information you want SCUIRREL to check with your students. "
                            "You can be very brief, as all context will be retrieved from the database of documents. "
                            "Don't be too broad, split into multiple topics if needed. "
                            "SCUIRREL will walk through the concepts in order, so kep that in mind</i>"
                        )
                    )),col_widths=12)
    ])

# --- Server ---
@module.server
def topics_server(input: Inputs, output: Outputs, session: Session, sID, user):

    topics = reactive.value(None)
    concepts = reactive.value(None)
    
    @reactive.effect
    @reactive.event(user)
    def _():
        req(user.get()["uID"] != 1)

        # Get all active topics from the accorns database
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)   
        activeTopics = shared.pandasQuery(
            conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
        )
        conn.close()

        ui.update_select("tID", choices=dict(zip(activeTopics["tID"], activeTopics["topic"])))
        
        topics.set(activeTopics)

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
            ui.remove_ui("#noGoodTopic")
            ui.insert_ui(
                HTML(
                    "<div id=noGoodTopic style='color: red'>New topic must be at least 6 characters</div>"
                ),
                "#ntDescr",
                "afterEnd",
            )
            return

        # Add new topic to DB
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        cursor = conn.cursor()
        tID = shared.executeQuery(
            cursor,
            'INSERT INTO "topic"("topic", "created", "modified", "description")'
            "VALUES(?, ?, ?, ?)",
            (input.ntTopic(), shared.dt(), shared.dt(), input.ntDescr()),
            lastRowId="tID",
        )
        newTopics = shared.pandasQuery(
            conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
        )
        conn.commit()
        conn.close()

        # Update the topics select input
        ui.update_select(
            "tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])), selected=tID
        )
        topics.set(newTopics)
        ui.modal_remove()


    # --- Edit an existing topic - modal popup
    @reactive.effect
    @reactive.event(input.tEdit)
    def _():
        if input.tID() is not None:
            topic = topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["topic"]
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
                    ui.input_action_button("etEdit", "Update"), ui.modal_button("Cancel")
                ),
            )
            ui.modal_show(m)

    # When edit button is clicked
    @reactive.effect
    @reactive.event(input.etEdit)
    def _():
        # Only proceed if the input is valid
        if not shared.inputCheck(input.etInput()):
            ui.remove_ui("#noGoodTopic")
            ui.insert_ui(
                HTML(
                    "<div id=noGoodTopic style='color: red'>A topic must be at least 6 characters</div>"
                ),
                "#etInput",
                "afterEnd",
            )
            return

        if (
            topics.get()[topics.get()["tID"] == int(input.tID())].iloc[0]["topic"]
            == input.etInput()
        ):
            ui.remove_ui("#noGoodTopic")
            ui.insert_ui(
                HTML("<div id=noGoodTopic style='color: red'>No change detected</div>"),
                "#etInput",
                "afterEnd",
            )
            return

        # Update the DB
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        cursor = conn.cursor()
        # Backup old value
        accorns_shared.backupQuery(
            cursor, sID, "topic", input.tID(), "topic", False
        )
        # Update to new
        _ = shared.executeQuery(
            cursor,
            'UPDATE "topic" SET "topic" = ?, "modified" = ? WHERE "tID" = ?',
            (input.etInput(), shared.dt(), input.tID()),
        )
        newTopics = shared.pandasQuery(
            conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
        )
        conn.commit()
        conn.close()

        # Update the topics select input
        ui.update_select(
            "tID",
            choices=dict(zip(newTopics["tID"], newTopics["topic"])),
            selected=input.tID(),
        )
        topics.set(newTopics)
        ui.modal_remove()


    # --- Archive a topic - modal popup
    @reactive.effect
    @reactive.event(input.tArchive)
    def _():
        if input.tID() is None:
            return

        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'UPDATE "topic" SET "archived" = 1, "modified" = ? WHERE "tID" = ?',
            (shared.dt(), input.tID()),
        )
        newTopics = shared.pandasQuery(
            conn, 'SELECT "tID", "topic" FROM "topic" WHERE "archived" = 0'
        )

        # Empty the concept table is last topic was removed
        if topics.shape[0] == 0:
            conceptList = shared.pandasQuery(
                conn, 'SELECT * FROM "concept" WHERE "tID" = 0'
            )
            concepts.set(conceptList)

        conn.commit()
        conn.close()

        # Update the topics select input
        ui.update_select("tID", choices=dict(zip(newTopics["tID"], newTopics["topic"])))
        topics.set(newTopics)


    # ---- CONCEPTS ----
    @render.data_frame
    def conceptsTable():
        return render.DataTable(concepts.get()[["concept"]], width="100%", selection_mode="row")

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
            ui.remove_ui("#noGoodConcept")
            ui.insert_ui(
                HTML(
                    "<div id=noGoodConcept style='color: red'>New concept must be at least 6 characters</div>"
                ),
                "#ncInput",
                "afterEnd",
            )
            return

        # Add new topic to DB
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "concept"("tID", "concept", "created", "modified") VALUES(?, ?, ?, ?)',
            (input.tID(), input.ncInput(), shared.dt(), shared.dt()),
        )
        conceptList = shared.pandasQuery(
            conn, f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "archived" = 0'
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
                    ui.input_action_button("ncEdit", "Update"), ui.modal_button("Cancel")
                ),
            )
            ui.modal_show(m)

    # When edit button is clicked
    @reactive.effect
    @reactive.event(input.ncEdit)
    def _():
        # Only proceed if the input is valid
        if not shared.inputCheck(input.ecInput()):
            ui.remove_ui("#noGoodConcept")
            ui.insert_ui(
                HTML(
                    "<div id=noGoodConcept style='color: red'>A concept must be at least 6 characters</div>"
                ),
                "#ecInput",
                "afterEnd",
            )
            return
        concept = conceptsTable.data_view(selected=True).iloc[0]["concept"]
        if concept == input.ecInput():
            ui.remove_ui("#noGoodConcept")
            ui.insert_ui(
                HTML("<div id=noGoodConcept style='color: red'>No change detected</div>"),
                "#ecInput",
                "afterEnd",
            )
            return

        # Update the DB
        cID = concepts.get().iloc[conceptsTable.data_view(selected=True).index[0]]["cID"]
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        cursor = conn.cursor()
        # Backup old value
        accorns_shared.backupQuery(
            cursor, sID, "concept", int(cID), "concept", False
        )
        # Update to new
        _ = shared.executeQuery(
            cursor,
            'UPDATE "concept" SET "concept" = ?, "modified" = ? WHERE "cID" = ?',
            (input.ecInput(), shared.dt(), int(cID)),
        )
        conceptList = shared.pandasQuery(
            conn, f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "archived" = 0'
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

        cID = concepts.get().iloc[conceptsTable.data_view(selected=True).index[0]]["cID"]
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'UPDATE "concept" SET "archived" = 1, "modified" = ? WHERE "cID" = ?',
            (shared.dt(), int(cID)),
        )
        conceptList = shared.pandasQuery(
            conn, f'SELECT * FROM "concept" WHERE "tID" = {input.tID()} AND "archived" = 0'
        )
        conn.commit()
        conn.close()

        concepts.set(conceptList)

    # --- Load concepts when a topic is selected
    @reactive.effect
    @reactive.event(input.tID)
    def _():
        tID = input.tID() if input.tID() else 0
        conn = shared.appDBConn(postgresUser = shared.postgresAccorns)
        conceptList = shared.pandasQuery(
            conn, f'SELECT * FROM "concept" WHERE "tID" = {tID} AND "archived" = 0'
        )
        conn.close()
        concepts.set(conceptList)

    return topics, concepts
