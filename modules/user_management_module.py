# ------ User Management Module ------
# ------------------------------------
# This module is used to generate access codes for new users or to update passwords for existing users.

from shiny import Inputs, Outputs, Session, module, reactive, render, ui, req
import pandas as pd
from io import BytesIO

import ACCORNS.accorns_shared as accorns_shared

# ---- UI ----

@module.ui
def user_management_ui():
    return ([
            # Generate access codes to create new users or update passwords
            ui.card(
                ui.card_header("Generate access codes"),
                ui.input_numeric("numCodes", "Number of codes to generate", value=1, min=1, max=500),
                ui.input_select("role", "Role", choices={1: "User", 2: "Instructor", 3: "Admin"}),
                ui.input_action_button("generateCodes", "Generate codes", width="180px"),
                
                ui.output_data_frame("codesTable"),
                ui.panel_conditional("input.generateCodes > 0",
                    ui.download_link("downloadCodes", "Download as CSV")
                ))
    ])

# ---- SERVER ----

@module.server
def user_management_server(input: Inputs, output: Outputs, session: Session, user):

    @reactive.calc
    @reactive.event(input.generateCodes)
    def accessCodes():
        req(user.get()["uID"] != 1)
        newCodes = accorns_shared.generate_access_codes(n = input.numCodes(), uID= user.get()["uID"], adminLevel=int(input.role()))
        role = ["user", "instructor", "admin"][int(input.role())]
        # create a pandas dataframe form the dictionary
        return pd.DataFrame({"accessCode": newCodes, "role": role})
    
    @render.data_frame
    def codesTable():
        return accessCodes()
    
    @render.download(filename = "hollow-tree_accessCodes.csv")
    async def downloadCodes():
        with BytesIO() as buf:
            accessCodes().to_csv(buf, index=False)
            yield buf.getvalue()

    return
