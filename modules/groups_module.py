# ------ Group Management Module ------
# ------------------------------------
# This module is used to manage groups of users and topics

from shiny import Inputs, Outputs, Session, module, reactive, render, ui, req
from io import BytesIO

import shared.shared as shared

# idea for widget: https://assets.justinmind.com/support/wp-content/uploads/2016/07/Sorted-lists-anim.gif

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
def groups_ui():
    return [
        # Generate access codes to create new users or update passwords
        ui.card(
            ui.card_header("Groups"),
            ui.input_select("group", "Group", choices={}),
            ui.input_action_button("newGroup", "New group", width="180px"),
        ),       
        ui.card(
                ui.card_header("Members"),
                ui.output_data_frame("membersTable"),
                ui.input_action_button("delMember", "Remove selected member from group", width="340px"),
            ),
        ui.card(
            ui.card_header("Unused group codes"),
            ui.output_data_frame("codesTable"),
            ui.input_action_button("generateCodes", "Generate new codes", width="230px"),
        ),
    ]


# ---- SERVER ----


@module.server
def groups_server(input: Inputs, output: Outputs, session: Session, user, postgresUser):
    
    # Set reactive variables
    conn = shared.appDBConn(postgresUser=postgresUser)
    groups = reactive.value(shared.pandasQuery(conn, 'SELECT * FROM "group"'))
    members = reactive.value(shared.pandasQuery(
            conn,
            (
                'SELECT m.*, u."username", u."fName", u."lName", u."email" '
                'FROM "group" AS \'g\', "user" AS \'u\', "group_member" AS \'m\' '
                'WHERE m."gID" = g."gID" AND m."uID" = u."uID" AND g."gID" = NULL'
            ),
        ))
    groupTopics = reactive.value(shared.pandasQuery(conn, 'SELECT * FROM "group_topic"'))
    groupCodes = reactive.value(shared.pandasQuery(
            conn,
            (
                'SELECT a.* '
                'FROM "accessCode" AS \'a\', "group" AS \'g\' '
                'WHERE a."gID" = g."gID" AND a."used" IS NULL AND a."gID" = NULL'
            ),
        ))  
    conn.close() 

    # Members table
    @render.data_frame
    def membersTable():
        return render.DataTable(members(), width="100%", height="auto")
    
    @render.data_frame
    def codesTable():
        return render.DataTable(groupCodes(), width="100%", height="auto")

    # backup
    # @reactive.effect
    # @reactive.event(user)
    # def _():
    #     groupCodes.set(
    #         getAccessCodes(uID=user.get()["uID"], adminLevel=user.get()["adminLevel"])
    #     )
    #     return

    # @reactive.effect
    # @reactive.event(user)
    # def _():
    #     ui.update_select(
    #         "role",
    #         choices={
    #             key: shared.adminLevels[key]
    #             for key in shared.adminLevels
    #             if key <= user.get()["adminLevel"]
    #         },
    #     )

    # # Render the table with the reset codes for the users who requested a password reset
    # @render.data_frame
    # def resetTable():
    #     conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    #     resetTable = shared.pandasQuery(
    #         conn,
    #         (
    #             'SELECT u."username", a."code" AS \'resetCode\', u."fName", u."lName", u."email"'
    #             'FROM "accessCode" AS a, "user" AS u WHERE a."uID_user" = u."uID" '
    #             'AND a."adminLevel" IS NULL AND a."used" IS NULL'
    #         ),
    #     )
    #     conn.close()

    #     return render.DataTable(resetTable, width="100%", height="auto")

    # # Generate new access codes
    # @reactive.calc
    # @reactive.event(input.generateCodes)
    # def newgroupCodes():
    #     req(user.get()["uID"] != 1)
    #     conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    #     cursor = conn.cursor()
    #     newCodes = shared.generate_access_codes(
    #         cursor=cursor,
    #         n=input.numCodes(),
    #         creatorID=user.get()["uID"],
    #         adminLevel=int(input.role()),
    #         note=input.note(),
    #     )
    #     conn.commit()
    #     conn.close()
    #     groupCodes.set(
    #         getAccessCodes(uID=user.get()["uID"], adminLevel=user.get()["adminLevel"])
    #     )
    #     return newCodes

    # @render.data_frame
    # def newCodesTable():
    #     return newgroupCodes()

    # @render.download(filename="hollow-tree_groupCodes.csv")
    # async def downloadCodes():
    #     with BytesIO() as buf:
    #         newgroupCodes().to_csv(buf, index=False)
    #         yield buf.getvalue()

    # @render.data_frame
    # def codesTable():
    #     return render.DataTable(groupCodes(), width="100%", height="auto")

    return
