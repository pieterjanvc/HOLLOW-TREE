# ------ Topics Module ------
# --------------------------

# -- General
import pandas as pd
from re import search as re_search

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui
from htmltools import HTML, div

import shared.shared as shared

# --- Functions


# --- UI
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
                        # def conceptsTable():
                        #     if concepts.get() is None:
                        #         return
                        #     return render.DataTable(
                        #         concepts.get()[["concept"]],
                        #         width="100%",
                        #         selection_mode="row",
                        #     )

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

# --- Server
@module.server
def topics_server(input: Inputs, output: Outputs, session: Session, uID):
    return
