# ------ Group Join Module ------
# ------------------------------------
# This module has a button that will allow a user to join a group with a valid group access code

from shiny import Inputs, Outputs, Session, module, reactive, ui, req
from htmltools import HTML
from io import BytesIO

import shared.shared as shared


@module.ui
def group_join_ui():
    return [
        # Generate access codes to create new users or update passwords
        ui.input_action_button("joinGroup", "Join group", width="180px", inline=True),
    ]


# ---- SERVER ----


@module.server
def group_join_server(
    input: Inputs, output: Outputs, session: Session, user, groups, postgresUser
):
    @reactive.effect
    @reactive.event(input.joinGroup)
    def _():
        m = ui.modal(
            ui.input_text("accessCode", "Group access code"),
            title="Join group",
            easy_close=True,
            footer=ui.TagList(
                ui.input_action_button("submitJoin", "Submit"),
                ui.modal_button("Cancel"),
            ),
        )

        ui.modal_show(m)

        return

    @reactive.calc
    @reactive.event(input.submitJoin)
    def addToGroup():
        # Check the access code
        conn = shared.appDBConn(postgresUser=postgresUser)
        code = shared.accessCodeCheck(
            conn, accessCode=input.accessCode(), codeType=2, uID=int(user.get()["uID"])
        )

        invalid = code is None
        if invalid:
            shared.inputNotification(session, "accessCode", "Invalid access code")
            conn.close()
            return None

        invalid = code["adminLevel"].iloc[0] < 2 and postgresUser == shared.postgresAccorns
        if invalid:
            shared.inputNotification(session, "accessCode", "This access code only allows you to join this group as a user in SCUIRREL")
            conn.close()
            return None

        invalid = groups.get()[groups.get()["gID"] == int(code["gID"].iloc[0])]
        if invalid.shape[0] > 0:
            shared.inputNotification(
                session,
                "accessCode",
                f"You already are a member of group: {invalid.iloc[0]['group']}",
            )
            conn.close()
            return None

        dt = shared.dt()

        # Add user to group in the DB
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "group_member"("gID", "uID", "adminLevel", "added")'
            "VALUES(?, ?, ?, ?)",
            (
                int(code.iloc[0]["gID"]),
                int(user.get()["uID"]),
                int(code.iloc[0]["adminLevel"]),
                dt,
            ),
        )

        # Update the access code to be used
        _ = shared.executeQuery(
            cursor,
            'UPDATE "accessCode" SET "uID_user" = ?, "used" = ? WHERE "aID" = ?',
            (int(user.get()["uID"]), dt, int(code.iloc[0]["aID"])),
        )
        conn.commit()
        conn.close()

        ui.modal_remove()

        return code

    return addToGroup
