# ******************************************
# ----------- SCUIRREL: MAIN APP -----------
# ******************************************

import shared.shared as shared
from SCUIRREL.scuirrel_shared import endDiscussion

from modules.login_module import login_server, login_ui
from modules.chat_module import chat_ui, chat_server
from modules.feedback_module import feedback_ui, feedback_server

# General
import os
import traceback
import concurrent.futures

# -- Shiny
from shiny import App, reactive, render, ui
from htmltools import HTML


# ----------- SHINY APP -----------
# *********************************

if shared.remoteAppDB:
    _ = shared.checkRemoteDB(postgresUser=shared.postgresScuirrel)

# --- RENDERING UI ---
# ********************

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
pool = concurrent.futures.ThreadPoolExecutor()

# --- UI LAYOUT ---
# Add some JS so that pressing enter can send the message too
demoInfo = (
    "If you don't have an account, you can still try the demo" if shared.addDemo else ""
)

# --- UI LAYOUT ---
app_ui = ui.page_fluid(
    ui.head_content(
        ui.include_css(os.path.join(curDir, "shared", "shared_css", "shared.css")),
        ui.include_css(
            os.path.join(curDir, "SCUIRREL", "scuirrel_css", "scuirrel.css")
        ),
        ui.include_js(os.path.join(curDir, "SCUIRREL", "scuirrel_js", "scuirrel.js")),
        ui.include_js(os.path.join(curDir, "shared", "shared_js", "shared.js")),
    ),
    ui.output_ui("scuirrelTabs"),
    # Customised feedback button (floating at right side of screen)
    feedback_ui("feedback"),
    id="tab",
    title=" SCUIRREL ",
)

# --- SERVER ---
# **************


def server(input, output, session):
    # Register the session start in the DB
    conn = shared.appDBConn(postgresUser=shared.postgresScuirrel)
    cursor = conn.cursor()
    sID = shared.executeQuery(
        cursor,
        'INSERT INTO "session" ("shinyToken", "uID", "appID", "start")'
        "VALUES(?, 1, 0, ?)",
        (session.id, shared.dt()),
        lastRowId="sID",
    )
    conn.commit()
    conn.close()

    # Login screen
    user = login_server(
        "login", postgresUser=shared.postgresScuirrel, sessionID=sID, minAdminLevel=1
    )
    # General feedback module
    _ = feedback_server("feedback", sID=sID, postgresUser=shared.postgresScuirrel)

    # Which tabs to show based on the user
    @render.ui
    @reactive.event(user)
    def scuirrelTabs():
        if user.get()["adminLevel"] < 1 or user.get()["adminLevel"] is None:
            return ui.TagList(
                ui.navset_pill(
                    # TAB 1 - HOME & LOGIN - shown before login
                    ui.nav_panel(
                        "Home",
                        ui.layout_columns(
                            ui.card(
                                ui.card_header("Welcome to SCUIRREL"),
                                HTML(f"""
<p>To access the full SCUIRREL functionality, please login first. If this is the first time you are accessing the 
application, please use the access code provided by your administrator to create an account. {demoInfo}</p>"""),
                            ),
                            col_widths=12,
                        ),
                        login_ui("login"),
                    ),
                    id="preLoginTabs",
                )
            )
        else:
            # Tabs to show after successful login
            return ui.TagList(
                ui.navset_pill(
                    # TAB 2 - CHAT
                    ui.nav_panel("SCUIRREL", chat_ui("chat"), value="cTab"),
                    id="postLoginTabs",
                )
            )

    # Server functions for the different tabs are found in their respective modules
    chat = chat_server(
        "chat", user=user, sID=sID, postgresUser=shared.postgresScuirrel, pool=pool
    )

    # Code to run at the END of the session (i.e. when user disconnects)
    _ = session.on_ended(lambda: theEnd())

    # Function to run at the end of the session (when user disconnects)
    def theEnd():
        with reactive.isolate():
            # Add logs to the database after user exits
            conn = shared.appDBConn(postgresUser=shared.postgresScuirrel)
            cursor = conn.cursor()

            if chat["dID"].get() != 0:
                endDiscussion(cursor, chat["dID"].get(), chat["messages"].get())

            # Register the end of the session and if an error occurred, log it
            errMsg = traceback.format_exc().strip()

            if errMsg == "NoneType: None":
                _ = shared.executeQuery(
                    cursor,
                    'UPDATE "session" SET "end" = ? WHERE "sID" = ?',
                    (shared.dt(), sID),
                )
            else:
                _ = shared.executeQuery(
                    cursor,
                    'UPDATE "session" SET "end" = ?, "error" = ? WHERE "sID" = ?',
                    (shared.dt(), errMsg, sID),
                )
            conn.commit()
            conn.close()

    return


app = App(app_ui, server)
app.on_shutdown(pool.shutdown)
