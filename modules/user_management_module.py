# ------ User Management Module ------
# ------------------------------------
# This module is used to generate access codes for new users or to update passwords for existing users.

from shiny import Inputs, Outputs, Session, module, reactive, render, ui, req
import pandas as pd
from io import BytesIO

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# ---- VARS & FUNCTIONS ----

adminLevels = {1: "User", 2: "Instructor", 3: "Admin"}


def getAccessCodes(uID, adminLevel):
    conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    # Admins can see all codes, instructors only their own
    if adminLevel < 3:
        query = (
            f'SELECT * FROM "accessCode" WHERE "uID_creator" = {uID} AND "used" IS NULL'
        )
        result = shared.pandasQuery(conn, query=query)
        result = result[["code", "adminLevel", "created", "note"]]
    else:
        query = 'SELECT * FROM "accessCode" WHERE "used" IS NULL'
        result = shared.pandasQuery(conn, query=query)
        result = result.drop(columns=["uID_user", "used"])

    conn.close()

    result["adminLevel"] = [adminLevels[i] for i in result["adminLevel"]]
    return result


# ---- UI ----


@module.ui
def user_management_ui():
    return [
        # Generate access codes to create new users or update passwords
        ui.card(
            ui.card_header("Generate access codes"),
            ui.input_numeric(
                "numCodes", "Number of codes to generate", value=1, min=1, max=500
            ),
            ui.input_select("role", "Role", choices={}),
            ui.input_text("note", "(optional) Reason for generating codes"),
            ui.input_action_button("generateCodes", "Generate codes", width="180px"),
            ui.output_data_frame("newCodesTable"),
            ui.panel_conditional(
                "input.generateCodes > 0",
                ui.download_link("downloadCodes", "Download as CSV"),
            ),
        ),
        ui.card(
            ui.card_header("Unused access codes"), ui.output_data_frame("codesTable")
        ),
    ]


# ---- SERVER ----


@module.server
def user_management_server(input: Inputs, output: Outputs, session: Session, user):
    accessCodes = reactive.value()

    @reactive.effect
    @reactive.event(user)
    def _():
        accessCodes.set(
            getAccessCodes(uID=user.get()["uID"], adminLevel=user.get()["adminLevel"])
        )
        return

    @reactive.effect
    @reactive.event(user)
    def _():
        ui.update_select(
            "role",
            choices={
                key: adminLevels[key]
                for key in adminLevels
                if key <= user.get()["adminLevel"]
            },
        )

    @reactive.calc
    @reactive.event(input.generateCodes)
    def newAccessCodes():
        req(user.get()["uID"] != 1)
        newCodes = accorns_shared.generate_access_codes(
            n=input.numCodes(),
            uID=user.get()["uID"],
            adminLevel=int(input.role()),
            note=input.note(),
        )
        accessCodes.set(
            getAccessCodes(uID=user.get()["uID"], adminLevel=user.get()["adminLevel"])
        )
        return newCodes

    @render.data_frame
    def newCodesTable():
        return newAccessCodes()

    @render.download(filename="hollow-tree_accessCodes.csv")
    async def downloadCodes():
        with BytesIO() as buf:
            newAccessCodes().to_csv(buf, index=False)
            yield buf.getvalue()

    @render.data_frame
    def codesTable():
        return render.DataTable(accessCodes(), width="100%")

    return
