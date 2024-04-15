# ******************************************
# ----------- SCUIRREL: MAIN APP -----------
# ******************************************

# Welcome to SCUIRREL:
# Science Concept Understanding with Interactive Research RAG Educational LLM

# See app_shared.py for variables and functions shared across sessions
import app_shared as shared 

# General
import sqlite3
from html import escape
import pandas as pd

# Llamaindex
from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

# Shiny
from shiny import reactive
from shiny.express import input, render, ui, session
from htmltools import HTML, div


# ----------- SHINY APP -----------
# *********************************

# Non-reactive session variables (loaded before session starts)
uID = 1  # if registered users update later

conn = sqlite3.connect(shared.appDB)
topics = pd.read_sql_query("SELECT tID, topic FROM topic WHERE archived = 0", conn)
conn.close()


# --- RENDERING UI ---
# ********************

ui.page_opts(fillable=True)
ui.include_css("www/styles.css")

# --- CUSTOM JS FUNCTIONS (move to separate file later) ---

# This function allows you to hide/show/disable/enable elements by ID or data-value
# The latter is needed because tabs don't use ID's but data-value
ui.tags.script(
    """
    Shiny.addCustomMessageHandler("hideShow", function(x) {

        if (document.getElementById(x.id)) {
            var element = document.getElementById(x.id);
        } else if (document.querySelector('[data-value="' + x.id + '"]')) {
            var element = document.querySelector('[data-value="' + x.id + '"]');
        } else {
            alert("No element found with an ID or data-value of:" + x.id);
            return;
        }

        switch(x.effect) {
            case "d":
                element.setAttribute("disabled", true);
                break;
            case "e":
                element.setAttribute("disabled", false);
                break;
            case "h":
                element.style.display = "none";
                break;
            case "s":
                element.style.display = "";
                break;
        }
        
    });
    """
)

def elementDisplay(id, effect):
    @reactive.effect
    async def _():
        await session.send_custom_message("hideShow", {"id": id, "effect": effect})

# Add some JS so that pressing enter can send the message too
ui.head_content(
    HTML("""<script>
         $(document).keyup(function(event) {
            if ($("#newChat").is(":focus") && (event.key == "Enter") && event.ctrlKey) {
                $("#send").click();
            }
        });
         </script>""")
)

# --- UI LAYOUT ---
with ui.navset_pill(id="tab"):
    # MAIN CHAT TAB
    with ui.nav_panel("SCUIRREL"):
        # Render the chat window
        with ui.layout_columns(col_widths=12):
            with ui.card(id="about"):
                HTML("""<p>Hello, I'm Scuirrel (Science Concept Understanding with Interactive Research RAG Educational LLM). 
                     I'm here to help you test your knowledge on specific concepts
                     related to topics relevant to your coursework. I will guide you though these concepts by asking you
                     a series of questions. Note that I will try and make you think for yourself, and not simply
                     provide answers. However, I sometimes go nuts so please talk to your course instructors / teaching 
                     fellows if you have questions or concerns.<br><br><i>NOTE:
                     Though this app is anonymous, I still like to collect data acorns (including chat history) for 
                     research purposes so don't share any personal information and keep to the topic at hand.</i></p>""")
            with ui.card(id="topicSelection"):
                ui.card_header("Pick a topic")
                ui.input_select("selTopic", None, choices=[], width="600px")

            with ui.card(id="chatWindow", height="45vh"):
                ui.card_header("Conversation")

                @render.ui
                def chatLog():
                    return div(HTML(userLog.get()))

        # User input, send button and wait message
        div(
            ui.input_text_area(
                "newChat", "", value="", width="100%", spellcheck=True, resize=False
            ),
            ui.input_action_button("send", "Send"),
            id = "chatIn"),
        div(HTML("<p style='color: white'><i>Scuirrel is foraging for an answer ...</i></p>"), 
            id = "waitResp", style="display: none;")
    
    # USER PROGRESS TAB
    with ui.nav_panel("Profile"):
        with ui.layout_columns(col_widths=12):
            with ui.card():
                ui.card_header("User Progress")
                "TODO"


# --- REACTIVE VARIABLES & FUNCTIONS ---

sessionID = reactive.value(0)
discussionID = reactive.value(0)

@reactive.calc
@reactive.event(input.selTopic)
def tID():
    tID = topics[topics["tID"] == int(input.selTopic())].iloc[0]["tID"]
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO discussion (tID, sID, start)"
        f'VALUES({tID}, {sessionID.get()}, "{shared.dt()}")'
    )
    discussionID.set(cursor.lastrowid)
    conn.commit()
    conn.close()
    return tID  # todo make user select topic


firstWelcome = (
    'Hello, I\'m here to help you get a basic understanding of the following topic: '
    f'{topics.iloc[0]["topic"]}. Have you heard about this before?'
)


@reactive.calc
def welcome():
    return (
        'Hello, I\'m here to help you get a basic understanding of the following topic: '
        f'{topics[topics["tID"] == tID()].iloc[0]["topic"]}. Have you heard about this before?'
    )


with reactive.isolate():
    messages = reactive.value([(1, shared.dt(), firstWelcome)])
    userLog = reactive.value(f"""<div class='botChat talk-bubble tri'>
                            <p>Hello, I'm here to help you get a basic understanding of 
                            the following topic: <b>{topics.iloc[0]["topic"]}</b>. 
                            Have you heard about this before?</p></div>""")
    botLog = reactive.value(
        f"""---- PREVIOUS CONVERSATION ----\n--- YOU:\n{firstWelcome}"""
    )


# Run once the session initialised
@reactive.effect
def _():
    # Set the function to be called when the session ends
    dID = discussionID.get()
    msg = messages.get()
    sID = sessionID.get()
    _ = session.on_ended(lambda: theEnd(sID, dID, msg))

    if sessionID.get() != 0:
        return

    # Register the session in the DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    # For now we only have anonymous users
    cursor.execute(
        "INSERT INTO session (shinyToken, uID, start)"
        f'VALUES("{session.id}", {uID}, "{shared.dt()}")'
    )
    sID = cursor.lastrowid
    conn.commit()
    conn.close()
    sessionID.set(sID)

    # Set the topics based on what's in the database
    ui.update_select("selTopic", choices=dict(zip(topics["tID"], topics["topic"])))


# Code to run at the end of the session (i.e. when user disconnects)
def theEnd(sID, dID, msg):
    # Add logs to the database after user exits
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute(f'UPDATE session SET end = "{shared.dt()}" WHERE sID = {sID}')
    cursor.execute(f'UPDATE discussion SET end = "{shared.dt()}" WHERE dID = {dID}')
    cursor.executemany(
        f"INSERT INTO message(dID,isBot,timeStamp,message)" f"VALUES({dID}, ?, ?, ?)",
        msg,
    )
    conn.commit()
    conn.close()


# Get the concepts related to the topic
@reactive.calc
def concepts():
    conn = sqlite3.connect(shared.appDB)
    concepts = pd.read_sql_query(
        f"SELECT * FROM concept WHERE tID = {tID()} AND archived = 0", conn
    )
    conn.close()
    return concepts


# Adapt the chat engine to the topic
@reactive.calc
def chatEngine():
    # TUTORIAL Llamaindex + Prompt engineering
    # https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb
    # https://docs.llamaindex.ai/en/stable/examples/customization/prompts/chat_prompts/

    # The two strings below have not been altered from the defaults set by llamaindex,
    # but can be if needed
    qa_prompt_str = (
        "Context information is below.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Given the context information and not prior knowledge, "
        "answer the question: {query_str}\n"
    )

    refine_prompt_str = (
        "We have the opportunity to refine the original answer "
        "(only if needed) with some more context below.\n"
        "------------\n"
        "{context_msg}\n"
        "------------\n"
        "Given the new context, refine the original answer to better "
        "answer the question: {query_str}. "
        "If the context isn't useful, output the original answer again.\n"
        "Original Answer: {existing_answer}"
    )

    topicList = "* " + "\n* ".join(concepts()["concept"])

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                f"""
                Your goal is to check wether the user (a student) has an understanding of the following topic: 
                {topics[topics["tID"] == tID()].iloc[0]["topic"]}
                ----
                These are the sub-concepts that the user should understand:
                {topicList}
                ----
                Remember that you are not lecturing, i.e. giving / asking definitions or giving away all the concepts.
                Rather, you will ask a series of questions (or generate a multiple choice question if it fits) and look
                at the answers to refine your next question according to the current understanding of the user.
                Try to make the user think and reason critically, but do help out if they get stuck. 
                You will adapt the conversation until you feel all sub-concepts are understood.
                Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
                message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!
                """
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=qa_prompt_str),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                """
                If necessary, make edits to ensure the following:
                - Do not keep repeating the topic title in your answer, focus on what's currently going on
                - You should stay on topic, and make sure all sub-concepts are evaluated 
                (but don't give them away accidentally!)
                - If a user seems confused or does not know something, you should explain some of the theory 
                in light of their current perceived knowledge
                - Make sure you make the user think for themselves, but don't make it frustrating
                - Double check if the latest user query does not contain conceptual or jargon errors and address them if needed
                - You can add some fun facts based on the provided background if appropriate to keep the conversation
                interesting 
                """
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return shared.index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=shared.llm
    )


# When the send button is clicked...
@reactive.effect
@reactive.event(input.send)
def _():    

    newChat = input.newChat()

    if (newChat == "") | (newChat.isspace()):
        return
    
    elementDisplay("waitResp", "s")
    elementDisplay("chatIn", "h")
    msg = messages.get()
    msg.append((False, shared.dt(), newChat))
    messages.set(msg)
    botIn = botLog.get() + "\n---- NEW RESPONSE FROM USER ----\n" + newChat
    userLog.set(
        userLog.get()
        + "<div class='userChat talk-bubble tri'><p>"
        + escape(newChat) # prevent HTML injection from user
        + "</p></div>"
    )
    botLog.set(botLog.get() + f"\n--- USER:\n{newChat}")    
    botResponse(chatEngine(), botIn)


# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def botResponse(chatEngine, botIn):
    return str(chatEngine.query(botIn))


# Processing LLM response
@reactive.effect
def _():
    resp = botResponse.result()
    with reactive.isolate():
        userLog.set(
            userLog.get()
            + "<div class='botChat talk-bubble tri'><p>"
            + resp
            + "</p></div>"
        )
        botLog.set(botLog.get() + "\n--- YOU:\n" + resp)
    # Now the LLM has finished the user can send a new response
    elementDisplay("waitResp", "h")
    ui.update_text_area("newChat", value=None)
    elementDisplay("chatIn", "s")
    msg = messages.get()
    msg.append((True, shared.dt(), resp))
    messages.set(msg)
