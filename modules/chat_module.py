# ------ Chat Module ------
# -------------------------

from modules.quiz_module import quiz_ui, quiz_server

# -- General
import json
from html import escape

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui
from htmltools import HTML, div

import shared.shared as shared
import SCUIRREL.scuirrel_shared as scuirrel_shared

# --- UI
@module.ui
def chat_ui():
    return ([
       ui.layout_columns(
            ui.card(
                HTML("""<p>Hello, I'm Scuirrel (Science Concept Understanding Interactive Research RAG Educational LLM). 
                     I'm here to help you test your knowledge on specific concepts
                     related to topics relevant to your coursework. I will guide you though these concepts by asking you
                     a series of questions. Note that I will try and make you think for yourself, and not simply
                     provide answers. However, I sometimes go nuts so please talk to your course instructors / teaching 
                     fellows if you have questions or concerns.<br><br><i>NOTE:
                     Though this app is anonymous, I still like to collect data acorns (including chat history) for 
                     research purposes so don't share any personal information and keep to the topic at hand.</i></p>"""),
                     id="about"),
            ui.card(
                ui.card_header("Pick a topic"),
                ui.input_select("selTopic", None, choices=[], width="600px"),
                ui.input_action_button("startConversation", "Start conversation", width="200px"),
                quiz_ui("quiz"), id="topicSelection"),
            ui.panel_conditional("input.startConversation > 0",
                ui.card(
                    ui.card_header(HTML(
                        '<div class="progress-bar"><span id="chatProgress" class="progress-bar-fill" style="width: 0%;">Topic Progress</span></div>'
                        + str(
                            ui.input_action_button("chatFeedback", "Provide chat feedback")
                        )
                    ), id="chatHeader"),                    
                    div(id="conversation"),id="chatWindow", height="45vh")),

                # User input, send button and wait message
                div(
                    ui.input_text_area(
                        "newChat", "", value="", width="100%", spellcheck=True, resize=False
                    ),
                    ui.input_action_button("send", "Send"),
                    id="chatIn",
                    ),
                div(
                    HTML(
                        "<p style='color: white'><i>Scuirrel is foraging for an answer ...</i></p>"
                    ),
                    id="waitResp",
                    style="display: none;",
                ),col_widths=12)
    ])

@module.server
def chat_server(input: Inputs, output: Outputs, session: Session, user, sID):

    # Reactive variables
    discussionID = reactive.value(0)  # Current conversation
    conceptIndex = reactive.value(0)  # Current concept index to discuss
    messages = reactive.value(None)  # Raw chat messages
    botLog = reactive.value(None)  # Chat sent to the LLM 

    # The quiz question popup is a separate module
    _ = quiz_server("quiz", tID = input.selTopic, sID = sID, user = user)       

    # Update a custom, simple progress bar
    def progressBar(id, percent):
        @reactive.effect
        async def _():
            await session.send_custom_message("progressBar", {"id": id, "percent": percent})

    # When a new user signs in, show / update the relevant topics
    @reactive.calc
    @reactive.event(user)
    def topics():
        # Get all active topics - TODO: add a filter specific users
        conn = shared.appDBConn(shared.postgresScuirrel)
        topics = shared.pandasQuery(conn, 'SELECT * FROM "topic" WHERE "archived" = 0')
        conn.close()        
        
        return topics
    
    @reactive.effect
    @reactive.event(topics)
    def _():
        ui.update_select("selTopic", choices=dict(zip(topics()["tID"], topics()["topic"])))
        print("HI")
        return
    
    # When the start conversation button is clicked...
    @reactive.effect
    @reactive.event(input.startConversation)
    def _():
        tID = int(topics()[topics()["tID"] == int(input.selTopic())].iloc[0]["tID"])
        conn = shared.appDBConn(scuirrel_shared.postgresUser)
        cursor = conn.cursor()
        # Save the logs for the previous discussion (if any)
        if messages.get():
            scuirrel_shared.endDiscussion(cursor, discussionID.get(), messages.get())
            shared.elementDisplay("chatIn", "s", session)  # In case hidden if previous finished

        # Register the start of the  new topic discussion
        dID = shared.executeQuery(
            cursor,
            'INSERT INTO "discussion" ("tID", "sID", "start")' "VALUES(?, ?, ?)",
            (tID, sID, shared.dt()),
            lastRowId="dID",
        )
        discussionID.set(int(dID))
        # Only show the quiz button if there are any questions
        _ = shared.executeQuery(
            cursor,
            'SELECT "qID" FROM "question" WHERE "tID" = ? AND "archived" = 0',
            (tID,),
        )
        if cursor.fetchone():
            shared.elementDisplay("quiz", "s", session)
        else:
            shared.elementDisplay("quiz", "h", session)

        conn.commit()
        conn.close()
        # The first message is not generated by the bot
        firstWelcome = (
            'Hello, I\'m here to help you get a basic understanding of the following topic: '
            f'{topics().iloc[0]["topic"]}. What do you already know about this?'
        )

        msg = scuirrel_shared.Conversation()
        msg.add_message(
            isBot=1,
            cID=int(concepts().iloc[conceptIndex.get()]["cID"]),
            content=firstWelcome,
        )
        messages.set(msg)
        ui.insert_ui(
            HTML(f"""<div id='welcome' class='botChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'>
                                <p>Hello, I'm here to help you get a basic understanding of 
                                the following topic: <b>{topics().iloc[0]["topic"]}</b>. 
                                What do you already know about this?</p></div>"""),
            "#conversation",
        )
        botLog.set(f"---- PREVIOUS CONVERSATION ----\n--- MENTOR:\n{firstWelcome}")
        return tID


    # Get the concepts related to the topic
    @reactive.calc
    def concepts():
        conn = shared.appDBConn(scuirrel_shared.postgresUser)
        concepts = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {int(input.selTopic())} AND "archived" = 0',
        )
        conn.close()
        return concepts


    # When the send button is clicked...
    @reactive.effect
    @reactive.event(input.send)
    def _():
        newChat = input.newChat()
        # Ignore empty chat
        if (newChat == "") | (newChat.isspace()):
            return

        # Prevent new chat whilst LLM is working and show waiting message
        shared.elementDisplay("waitResp", "s", session)
        shared.elementDisplay("chatIn", "h", session)
        # Add the user message
        msg = messages.get()
        msg.add_message(
            isBot=0, cID=int(concepts().iloc[conceptIndex.get()]["cID"]), content=newChat
        )
        messages.set(msg)
        # Generate chat logs
        conversation = botLog.get() + "\n---- NEW RESPONSE FROM STUDENT ----\n" + newChat
        ui.insert_ui(
            HTML(
                f"<div class='userChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'><p>{escape(newChat)}</p></div>"
            ),
            "#conversation",
        )
        botLog.set(botLog.get() + f"\n--- STUDENT:\n{newChat}")
        topic = topics()[topics()["tID"] == int(input.selTopic())].iloc[0]["topic"]
        # Send the message to the LLM for processing
        botResponse(topic, concepts(), conceptIndex.get(), conversation)


    # Async Shiny task waiting for LLM reply
    @reactive.extended_task
    async def botResponse(topic, concepts, cIndex, conversation):
        # Check the student's progress on the current concept based on the last reply (other engine)
        engine = scuirrel_shared.progressCheckEngine(conversation, topic, concepts, cIndex)
        eval = json.loads(str(engine.query(conversation)))
        # See if the LLM thinks we can move on to the next concept or or not
        if int(eval["score"]) > 2:
            cIndex += 1
        # Check if all concepts have been covered successfully
        if cIndex >= concepts.shape[0]:
            resp = f"Well done! It seems you have demonstrated understanding of everything we wanted you to know about: {topic}"
        else:
            engine = scuirrel_shared.chatEngine(topic, concepts, cIndex, eval)
            resp = str(engine.query(conversation))

        return {"resp": resp, "eval": eval}


    # Processing LLM responses
    @reactive.effect
    def _():
        result = botResponse.result()
        eval = result["eval"]  # Evaluation of last response and progress
        resp = result["resp"]  # New response to student

        with reactive.isolate():
            # Check the topic progress and move on to next concept if current one scored well
            i = conceptIndex.get()
            finished = False
            if int(eval["score"]) > 2:
                if i < (concepts().shape[0] - 1):
                    i = i + 1
                else:
                    finished = True

                progressBar("chatProgress", int(100 * i / concepts().shape[0]))

            # Add the evaluation of the student's last reply to the log
            msg = messages.get()
            msg.addEval(eval["score"], eval["comment"])
            msg.add_message(isBot=1, cID=int(concepts().iloc[i]["cID"]), content=resp)
            messages.set(msg)
            conceptIndex.set(i)
            ui.insert_ui(
                HTML(
                    f"<div class='botChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'><p>{escape(resp)}</p></div>"
                ),
                "#conversation",
            )
            botLog.set(botLog.get() + "\n--- MENTOR:\n" + resp)

            # Now the LLM has finished the user can send a new response
            shared.elementDisplay("waitResp", "h", session)
            ui.update_text_area("newChat", value="")
            # If conversation is over don't show new message box
            if not finished:
                shared.elementDisplay("chatIn", "s", session)
            else:
                ui.insert_ui(HTML("<hr>"), "#conversation")

    
    return
