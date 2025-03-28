# ------ Group Management Module ------
# ------------------------------------
# This module is used to manage groups of users and topics

from shiny import Inputs, Outputs, Session, module, reactive, render, ui, req
from htmltools import HTML, div
from io import BytesIO

import shared.shared as shared
from modules.group_join_module import group_join_server, group_join_ui

# idea for widget: https://assets.justinmind.com/support/wp-content/uploads/2016/07/Sorted-lists-anim.gif

# ---- VARS & FUNCTIONS ----

accessCodesQuery = (
    'SELECT u."username" AS creator, a.* '
    'FROM "accessCode" AS a, "group" AS g, "user" AS u '
    'WHERE a."gID" = g."gID" AND a."uID_creator" = u."uID" AND a."used" IS NULL AND a."gID" = ?'
)


def groupQuery(conn, user):
    userFilter = (
        'WHERE "gID" IN (SELECT "gID" FROM "group_member" WHERE "uID" = ?) '
        if user["adminLevel"] < 3
        else ""
    )
    params = (int(user["uID"]),) if user["adminLevel"] < 3 else ()
    return shared.pandasQuery(
        conn,
        (f'SELECT * FROM "group" {userFilter} '),
        params=params,
    )


# Ignore the anonymous group
groupAdminLevels = {
    k: shared.groupAdminLevels[k] for k in list(shared.groupAdminLevels.keys())[1:]
}
# ---- UI ----


@module.ui
def groups_ui():
    return [
        # Generate access codes to create new users or update passwords
        ui.card(
            ui.card_header("Groups"),
            ui.input_select("gID", "Group", choices={}),
            div(
                ui.input_action_button("newGroup", "New group", width="180px"),
                group_join_ui("joinGroup"),
            ),
        ),
        ui.panel_conditional(
            "input.gID",
            ui.card(
                ui.card_header("Members"),
                ui.output_data_frame("membersTable"),
                ui.input_action_button(
                    "delMember", "Remove selected member from group", width="340px"
                ),
            ),
            ui.card(
                ui.card_header("Generate group access codes"),
                ui.input_numeric(
                    "numCodes", "Number of codes to generate", value=1, min=1, max=500
                ),
                ui.input_select("role", "Role", choices=groupAdminLevels),
                ui.input_text("note", "(optional) Reason for generating codes"),
                ui.input_action_button(
                    "generateCodes", "Generate new codes", width="230px"
                ),
                ui.output_data_frame("newCodesTable"),
                ui.panel_conditional(
                    "input.generateCodes > 0",
                    ui.download_link("downloadGroupCodes", "Download as CSV"),
                ),
            ),
            ui.card(
                ui.card_header("Unused group access codes"),
                ui.output_data_frame("codesTable"),
            ),
        ),
    ]


# ---- SERVER ----


@module.server
def groups_server(
    input: Inputs, output: Outputs, session: Session, sID, user, postgresUser
):
    groups = reactive.value()
    groupCodes = reactive.value()
    members = reactive.value()

    # -- Join group module --
    newGroup = group_join_server(
        "joinGroup", user=user, groups=groups, postgresUser=postgresUser
    )

    @reactive.effect
    @reactive.event(newGroup)
    def _():
        conn = shared.appDBConn(postgresUser=postgresUser)
        newGroups = groupQuery(conn, user.get())
        conn.close()
        groups.set(newGroups)

    # ---

    # When user changes
    @reactive.effect
    @reactive.event(user)
    def _():
        # Set reactive variables
        conn = shared.appDBConn(postgresUser=postgresUser)
        groups.set(groupQuery(conn, user.get()))
        conn.close()

    # Update group list based on user
    @reactive.effect
    @reactive.event(groups)
    def _():
        gIDs = groups.get()["gID"].to_list()
        ui.update_select(
            "gID",
            choices=dict(zip(gIDs, groups.get()["group"].to_list())),
            selected=gIDs[-1] if groups.get().shape[0] > 0 else None,
        )

    # When group is selected
    @reactive.effect
    @reactive.event(input.gID)
    def _():
        conn = shared.appDBConn(postgresUser=postgresUser)
        members.set(
            shared.pandasQuery(
                conn,
                (
                    'SELECT m.*, u."username", u."fName", u."lName", u."email" '
                    'FROM "group" AS g, "user" AS u, "group_member" AS m '
                    'WHERE m."gID" = g."gID" AND m."uID" = u."uID" AND g."gID" = ?'
                ),
                params=(int(input.gID()),),
            )
        )
        groupCodes.set(
            shared.pandasQuery(conn, accessCodesQuery, params=(int(input.gID()),))
        )
        conn.close()

    # Members table
    @render.data_frame
    def membersTable():
        return render.DataTable(members(), width="100%", height="auto")

    @render.data_frame
    def codesTable():
        return render.DataTable(
            groupCodes()[["creator", "code", "adminLevel", "created", "note"]],
            width="100%",
            height="auto",
        )

    # --- Add Group - modal popup
    @reactive.effect
    @reactive.event(input.newGroup)
    def _():
        m = ui.modal(
            ui.tags.p(
                HTML(
                    "Create a new group to organize users and topics. (e.g. for a class, project, or team)"
                )
            ),
            ui.input_text("ngGroup", "New group:", width="100%"),
            ui.input_text("ngDescr", "Description (optional):", width="100%"),
            title="Add a new group",
            easy_close=True,
            size="l",
            footer=ui.TagList(
                ui.input_action_button("ngAdd", "Add"), ui.modal_button("Cancel")
            ),
        )
        ui.modal_show(m)

    # When add button is clicked
    @reactive.effect
    @reactive.event(input.ngAdd)
    def _():
        # Only proceed if the input is valid
        if not shared.inputCheck(input.ngGroup(), 3):
            shared.inputNotification(
                session, "ngGroup", "Please enter a group name of at least 3 characters"
            )
            return

        # Add new topic to DB
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        gID = shared.executeQuery(
            cursor,
            'INSERT INTO "group"("sID", "group", "created", "modified", "description")'
            "VALUES(?, ?, ?, ?, ?)",
            (sID, input.ngGroup(), shared.dt(), shared.dt(), input.ngDescr()),
            lastRowId="gID",
        )
        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "group_member"("gID", "uID", "adminLevel", "added")'
            "VALUES(?, ?, ?, ?)",
            (gID, int(user.get()["uID"]), 2, shared.dt()),
        )

        newGroups = groupQuery(conn, user.get())
        conn.commit()
        conn.close()

        groups.set(newGroups)
        ui.modal_remove()

    # Generate new access codes
    @reactive.calc
    @reactive.event(input.generateCodes)
    def newgroupCodes():
        req(user.get()["uID"] != 1)
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        newCodes = shared.generate_access_codes(
            cursor=cursor,
            codeType=2,
            gID=int(input.gID()),
            n=input.numCodes(),
            creatorID=user.get()["uID"],
            adminLevel=int(input.role()),
            note=input.note(),
        )

        groupCodes.set(
            shared.pandasQuery(conn, accessCodesQuery, params=(int(input.gID()),))
        )
        conn.commit()
        conn.close()

        return newCodes

    @render.data_frame
    def newCodesTable():
        return newgroupCodes()

    @render.download(filename="hollow-tree_groupCodes.csv")
    async def downloadGroupCodes():
        with BytesIO() as buf:
            newgroupCodes().to_csv(buf, index=False)
            yield buf.getvalue()

    return groups
