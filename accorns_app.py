# ******************************************
# ----------- ACCORNS: ADMIN APP -----------
# ******************************************

# See app_shared.py for variables and functions shared across sessions
import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

from modules.user_management_module import user_management_server, user_management_ui
from modules.login_module import login_server,  login_ui
from modules.topics_module import topics_ui, topics_server
from modules.vectorDB_management_module import vectorDB_management_ui, vectorDB_management_server
from modules.quiz_generation_module import quiz_generation_ui, quiz_generation_server
from modules.feedback_module import feedback_ui, feedback_server

# -- General
import os
import traceback

# -- Shiny
from shiny import App,reactive, render, req, ui
from htmltools import HTML

# The following is needed to prevent async issues when inserting new data in vector DB
# https://github.com/run-llama/llama_index/issues/9978
import nest_asyncio
nest_asyncio.apply()

# ----------- SHINY APP -----------
# *********************************

uID = reactive.value(0)  # if registered admins make reactive later

# --- SETUP and CHECKS ---
# Generate local databases if needed
if not (shared.remoteAppDB):
    print(accorns_shared.createLocalAccornsDB())
    print(accorns_shared.createLocalVectorDB())
else:
    # Check if a remote database is used and if it's accessible
    print(shared.checkRemoteDB())
# Add the demo to the database if requested
if shared.addDemo:
    print(accorns_shared.addDemo(None)) 


# --- RENDERING UI ---
# ********************

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
os.path.join(curDir, "ACCORNS")

# --- UI LAYOUT ---
app_ui = ui.page_fluid(
    ui.head_content(
    ui.include_css(os.path.join(curDir, "shared", "shared_css", "shared.css")),
    ui.include_css(os.path.join(curDir, "ACCORNS", "accorns_css", "accorns.css")),
    ui.include_js(os.path.join(curDir, "ACCORNS", "accorns_js", "accorns.js")),
    ui.include_js(os.path.join(curDir, "shared", "shared_js", "shared.js")),
    ),
    ui.output_ui("accornsTabs"),
    # Customised feedback button (floating at right side of screen)
    feedback_ui("feedback"),
    id = "tab", title="ACCORNS")

# --- SERVER ---
# **************

def server(input, output, session):

    # Register the session start in the DB
    conn = shared.appDBConn(postgresUser=accorns_shared.postgresUser)
    cursor = conn.cursor()
    sID = shared.executeQuery(
        cursor,
        'INSERT INTO "session" ("shinyToken", "uID", "appID", "start")'
        "VALUES(?, 1, 1, ?)",
        (session.id, shared.dt()),
        lastRowId="sID",
    )
    conn.commit()
    conn.close()

    # Check which user is using the app
    user = login_server("login", postgresUser = shared.postgresAccorns, sessionID = sID, minAdminLevel = 2)
    _ = feedback_server("feedback", sID = sID, postgresUser=shared.postgresAccorns)

    # Which tabs to show based on the user
    @render.ui
    @reactive.event(user)
    def accornsTabs():
        if user.get()["adminLevel"] < 2 or user.get()["adminLevel"] is None:
            return ui.TagList(
                ui.navset_pill( 
        # TAB 1 - HOME & LOGIN - shown before login
        ui.nav_panel("Home",
            ui.layout_columns(
                ui.card(
                    ui.card_header("Welcome to ACCORNS"),
                    HTML("""
    <p>To access the ACCORNS you need an admin account. If this is the first time you are accessing the 
    application, please use the access code provided by your administrator to create an account</p>""")),col_widths=12),
            login_ui("login"),
            ),        
        id = "tab")
            )
        else:
            # Tabs to show after successful login
            return ui.TagList(ui.navset_pill(
                # TAB 2 - VECTOR DATABASE
                ui.nav_panel("Vector Database",
                    vectorDB_management_ui("vectorDB"), value="vTab"),
                # TAB 3 - TOPICS
                ui.nav_panel("Topics",
                    topics_ui("topics"), value="tTab"),
                # TAB 4 - QUIZ QUESTIONS
                ui.nav_panel("Quiz Questions",
                    # Select a topic and a question with options to add or archive
                    quiz_generation_ui("quizGeneration"), value="qTab"),
                # TAB 5 - USER MANAGEMENT
                ui.nav_panel("User Management",
                    user_management_ui("testUI")
                    , value="uTab"),
            ))

    # Server functions for the different tabs are found in their respective modules
    topics, concepts = topics_server("topics", sID=sID, user = user)
    _ = user_management_server("testUI", user = user)
    index, files = vectorDB_management_server("vectorDB", user = user)
    _ = quiz_generation_server("quizGeneration", sID = sID, index = index, topics = topics, user = user)

    # Code to run at the END of the session (i.e. when user disconnects)
    _ = session.on_ended(lambda: theEnd())

    def theEnd():
        # Add logs to the database after user exits            
        conn = shared.appDBConn(postgresUser=accorns_shared.postgresUser)
        cursor = conn.cursor()
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
