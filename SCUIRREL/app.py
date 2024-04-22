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
import json

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
                ui.input_select("selTopic", None, choices=[], width="600px"), 
                ui.input_action_button("quiz", "Give me a quiz question", width="300px")

            with ui.card(id="chatWindow", height="45vh"):
                ui.card_header("Conversation")

                @render.ui
                def chatLog():
                    return div(HTML(userLog.get()))

        # User input, send button and wait message
        (
            div(
                ui.input_text_area(
                    "newChat", "", value="", width="100%", spellcheck=True, resize=False
                ),
                ui.input_action_button("send", "Send"),
                id="chatIn",
            ),
        )
        div(
            HTML(
                "<p style='color: white'><i>Scuirrel is foraging for an answer ...</i></p>"
            ),
            id="waitResp",
            style="display: none;",
        )

    # USER PROGRESS TAB
    with ui.nav_panel("Profile"):
        with ui.layout_columns(col_widths=12):
            with ui.card():
                ui.card_header("User Progress")
                "TODO"


# --- REACTIVE VARIABLES & FUNCTIONS ---

sessionID = reactive.value(0)
discussionID = reactive.value(0)
conceptIndex = reactive.value(0)

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
    return tID


firstWelcome = (
    'Hello, I\'m here to help you get a basic understanding of the following topic: '
    f'{topics.iloc[0]["topic"]}. What do you already know about this?'
)


@reactive.calc
def welcome():
    return (
        'Hello, I\'m here to help you get a basic understanding of the following topic: '
        f'{topics[topics["tID"] == tID()].iloc[0]["topic"]}. What do you already know about this?'
    )


with reactive.isolate():
    messages = reactive.value([(1, shared.dt(), firstWelcome)])
    userLog = reactive.value(f"""<div class='botChat talk-bubble tri'>
                            <p>Hello, I'm here to help you get a basic understanding of 
                            the following topic: <b>{topics.iloc[0]["topic"]}</b>. 
                            What do you already know about this?</p></div>""")
    botLog = reactive.value(
        f"""---- PREVIOUS CONVERSATION ----\n--- MENTOR:\n{firstWelcome}"""
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
def chatEngine(topic,concepts,cIndex):
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

    cDone = "" if cIndex == 0 else "These concepts were already covered successfully:\n* " + \
    "\n* ".join(concepts.head(cIndex)["concept"])

    cToDo = "The following concepts still need to be discussed:\n* " + \
    "\n* ".join(concepts[cIndex:]["concept"])

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
f"""You (MENTOR) will chat with a student (STUDENT) to evaluate their understanding of the following topic: 
{topic}
----
{cDone}\n\n
{cToDo}
---- 

The current focus of the conversation should be on the following concept: 
{concepts.iloc[cIndex]["concept"]} 

Remember that you are not lecturing, i.e. giving / asking definitions or giving away all the concepts.
Rather, you will ask a series of questions and use the student's answers to refine your next question 
according to their current understanding.
Try to make the student think and reason critically, but do help out if they get stuck. 
You will adapt the conversation until you feel the there are no more mistakes and there is basic understanding of the concept.
Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!"""
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
        llm=shared.llm,
    )


# Adapt the chat engine to the topic
def progressCheckEngine(conversation,topic,concepts,cIndex):   

    cDone = "" if cIndex == 0 else "These concepts were already covered successfully:\n* " + \
    "\n* ".join(concepts.head(cIndex)["concept"])

    cToDo = "The following concepts still need to be discussed:\n* " + \
    "\n* ".join(concepts[cIndex:]["concept"])    

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
f"""You are monitoring a conversation between a tutor (TUTOR) and a student (STUDENT) on following topic:  
{topic}

{cDone}\n\n
{cToDo}

The conversation is currently focused on the following concept: 
{concepts.iloc[cIndex]["concept"]}

{conversation}

----

With this information, you have to decide if the STUDENT demonstrated enough understanding 
of the current concept to move on to the next one. 
You do this by outputting a numeric score with the following rubric:
* 1: No demonstration of understanding yet
* 2: Some understanding, but still incomplete or with mistakes warranting more discussion 
* 3: Basics of the concept seem to be understood and we might be able to move on
* 4: Clear demonstration of understanding

In addition you will add a short comment, based on the conversation and current concept, 
about what the STUDENT understands but more importantly what they still struggle with (if score < 4).

Please output your score in the following format:"""
r'{{"score": <int>, "comment": "<>"}}'
            ),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(r'Make sure the output is in the following format: {{"score": <int>, "comment": "<>"}}'),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    return shared.index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=shared.llm,
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
    conversation = botLog.get() + "\n---- NEW RESPONSE FROM STUDENT ----\n" + newChat
    userLog.set(
        userLog.get()
        + "<div class='userChat talk-bubble tri'><p>"
        + escape(newChat)  # prevent HTML injection from user
        + "</p></div>"
    )
    botLog.set(botLog.get() + f"\n--- STUDENT:\n{newChat}")
    topic = topics[topics["tID"] == tID()].iloc[0]["topic"]
    botResponse(topic,concepts(),conceptIndex.get(), conversation)


# Async Shiny task waiting for LLM reply
@reactive.extended_task
async def botResponse(topic,concepts,cIndex, conversation):
    engine = progressCheckEngine(conversation,topic,concepts,cIndex)
    eval = json.loads(str(engine.query(conversation)))
    print(eval)
    if int(eval["score"]) > 2:
        cIndex += 1
    
    if cIndex > concepts.shape[0]:
        resp = f"Well done! It seems you have demonstrated understanding of everything we wanted you to know about: {topic}"
    else:    
        engine = chatEngine(topic,concepts,cIndex)
        resp = str(engine.query(conversation))
    
    return {"resp": resp, "eval": eval}


# Processing LLM response
@reactive.effect
def _():
    result = botResponse.result()
    resp = result["resp"]
    eval = result["eval"]

    with reactive.isolate():
        if int(eval["score"]) > 2:
            conceptIndex.set(conceptIndex.get()+1)

        userLog.set(
            userLog.get()
            + "<div class='botChat talk-bubble tri'><p>"
            + resp
            + "</p></div>"
        )
        botLog.set(botLog.get() + "\n--- MENTOR:\n" + resp)
    # Now the LLM has finished the user can send a new response
    elementDisplay("waitResp", "h")
    elementDisplay("chatIn", "s")
    ui.update_text_area("newChat", value="")
    msg = messages.get()
    msg.append((True, shared.dt(), resp))
    messages.set(msg)

# -- QUIZ
 
quizQuestion = reactive.value()

# Clicking the quiz button shows a modal
@reactive.effect
@reactive.event(input.quiz)
def _():

    # Get a random question on the topic from the DB
    conn = sqlite3.connect(shared.appDB)
    q = pd.read_sql_query(f"SELECT * FROM question WHERE tID = {tID()} AND archived = 0", conn)
    conn.close()
    q = q.sample(1).iloc[0].to_dict()
    q["start"] =  shared.dt()   

    # UI for the quiz question popup (saved as a variable)
    @render.express
    def quizUI(): 
        HTML(f'<b>{q["question"]}</b><br><br>')
        ui.input_radio_buttons("quizOptions", None, width="100%", 
                                choices={"X":HTML("<i>Select an option below:</i>"),"A": q["optionA"],"B": q["optionB"],
                                        "C": q["optionC"],"D": q["optionD"]})
        ui.input_action_button("checkAnswer", "Check answer")    
        @render.ui
        def _():
            return checkAnswer()
    # The modal
    m = ui.modal(        
        quizUI,        
        title="Test your knowledge",
        easy_close=False,
        size="l",
        footer=ui.TagList(ui.input_action_button("qClose", "Return")),
    )
    ui.modal_show(m)
    quizQuestion.set(q)
    

# Clicking the check answer button will show result + explanation
@reactive.calc
@reactive.event(input.checkAnswer)
def checkAnswer():
    # User must select a valid option
    if input.quizOptions() == "X":
        return HTML("<hr><i>Select an option first!</i>")
    
    # Check Answer
    q = quizQuestion.get()
    correct = input.quizOptions() == q["answer"]
    q["response"] =  input.quizOptions()
    q["correct"] =  correct + 0 # Convert to integer
    # Add the response to the database

    # Hide the answer button (don't allow for multiple guessing)
    if not shared.allowMultiGuess:
        elementDisplay("checkAnswer", "h")
    
    # Add the timestamp the answer was checked
    q["check"] =  shared.dt()
    quizQuestion.set(q)

    return HTML(f'<hr><h3>{"Correct!" if correct else "Incorrect..."}</h3>'
                f'{q["explanation" + input.quizOptions()]}')

@reactive.effect
@reactive.event(input.qClose)
def _():
    q = quizQuestion.get()
    
    # Handle the case where user returns before checking an answer
    if "check" not in q:
        q["check"] = "NULL"  
        q["response"] = "NULL"
        q["correct"] = "NULL"
    else:
        q["check"] = f'"{q["check"]}"'
        q["response"] = f'"{q["response"]}"'

    # Add the response to the DB
    conn = sqlite3.connect(shared.appDB)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO response (sID, qID, "response", "correct", "start", "check", "end") '
                   f'VALUES({sessionID()}, {q["qID"]}, {q["response"]}, {q["correct"]},'
                   f'"{q["start"]}",{q["check"]},"{shared.dt()}")')
    conn.commit()
    conn.close()
    ui.modal_remove()
