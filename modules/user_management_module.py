# ------ User Management Module ------
# ------------------------------------
# This module is used to generate access codes for new users or to update passwords for existing users.

from shiny import Inputs, Outputs, Session, module, reactive, render, ui, req
from io import BytesIO

import shared.shared as shared

# ---- VARS & FUNCTIONS ----


def getAccessCodes(uID, adminLevel):
    conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    # Admins can see all codes, instructors only their own
    if adminLevel < 3:
        query = f'SELECT * FROM "accessCode" WHERE "uID_creator" = {uID} AND "used" IS NULL AND "adminLevel" IS NOT NULL'
        result = shared.pandasQuery(conn, query=query)
        result = result[["code", "adminLevel", "created", "note"]]
    else:
        query = 'SELECT * FROM "accessCode" WHERE "used" IS NULL AND "adminLevel" IS NOT NULL'
        result = shared.pandasQuery(conn, query=query)
        result = result.drop(columns=["uID_user", "used"])

    conn.close()

    result["adminLevel"] = [shared.adminLevels[i] for i in result["adminLevel"]]
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
            ui.card_header("Password reset requests"),
            ui.output_data_frame("resetTable"),
        ),
        ui.card(
            ui.card_header("Unused access codes"), ui.output_data_frame("codesTable")
        ),
    ]


# ---- SERVER ----


@module.server
def user_management_server(
    input: Inputs, output: Outputs, session: Session, user, postgresUser
):
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
                key: shared.adminLevels[key]
                for key in shared.adminLevels
                if key <= user.get()["adminLevel"] and key != 0
            },
        )

    # Render the table with the reset codes for the users who requested a password reset
    @render.data_frame
    def resetTable():
        conn = shared.appDBConn(postgresUser=postgresUser)
        resetTable = shared.pandasQuery(
            conn,
            (
                'SELECT u."username", a."code" AS "resetCode", u."fName", u."lName", u."email" '
                'FROM "accessCode" AS a, "user" AS u WHERE a."uID_user" = u."uID" '
                'AND a."codeType" = 1 AND a."used" IS NULL'
            ),
        )
        conn.close()

        return render.DataTable(resetTable, width="100%", height="auto")

    # Generate new access codes
    @reactive.calc
    @reactive.event(input.generateCodes)
    def newAccessCodes():
        req(user.get()["uID"] != 1)
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        newCodes = shared.generate_access_codes(
            cursor=cursor,
            codeType=0,
            n=input.numCodes(),
            creatorID=user.get()["uID"],
            adminLevel=int(input.role()),
            note=input.note(),
        )
        conn.commit()
        conn.close()
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
        return render.DataTable(accessCodes(), width="100%", height="auto")

    return
