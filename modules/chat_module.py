# ------ Chat Module ------
# -------------------------

from modules.quiz_module import quiz_ui, quiz_server
from modules.group_join_module import group_join_server, group_join_ui
import shared.shared as shared
import SCUIRREL.scuirrel_shared as scuirrel_shared

# -- General
import json
from html import escape
import pandas as pd
import asyncio

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render
from htmltools import HTML, div



# ---- VARS & FUNCTIONS ----
def groupQuery(uID, postgresUser, demo=shared.addDemo):
    includeDemo = 'UNION SELECT "gID", "group" FROM "group" WHERE "gID" = 1 ' if demo else ""
    conn = shared.appDBConn(postgresUser)
    getGroups = shared.pandasQuery(
        conn,
        (
            'SELECT g."gID", g."group" '
            "FROM group_member AS 'm', \"group_topic\" AS 't', \"group\" AS 'g' "
            'WHERE m."uID" = ? AND m."gID" = g."gID" AND t."gID" = g."gID" '
            'AND t."tID" IN (SELECT DISTINCT "tID" FROM "concept" WHERE "archived" = 0) '
            f'{includeDemo} ORDER BY g."group"'
        ),
        (uID,),
    )
    conn.close()
    return getGroups


# --- UI
@module.ui
def chat_ui():
    return [
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
                id="about",
            ),
            ui.card(
                ui.card_header("Pick a topic"),
                div(
                    div(
                        ui.input_select("gID", "Group", choices={}),
                        **{"class": "makeInline"},
                    ),
                    group_join_ui("joinGroup"),
                ),
                ui.panel_conditional(
                    "input.gID",
                    div(
                        div(
                            ui.input_select(
                                "selTopic", "Topic", choices=[], width="auto"
                            ),
                            **{"class": "makeInline"},
                        ),
                        ui.input_action_button(
                            "startConversation",
                            "Start conversation",
                            width="200px",
                            style="display: inline-block;",
                        ),
                        quiz_ui("quiz"),
                    ),
                ),
                id="topicSelection",
            ),
            ui.panel_conditional(
                "input.startConversation > 0",
                ui.card(
                    ui.card_header(
                        HTML(
                            '<div class="progress-bar"><span id="chatProgress" class="progress-bar-fill" style="width: 0%;">Topic Progress</span></div>'
                            + str(
                                ui.input_action_button(
                                    "chatFeedback", "Provide chat feedback"
                                )
                            )
                        ),
                        id="chatHeader",
                    ),
                    div(id=module.resolve_id("conversation")),
                    id="chatWindow",
                    **{"class": "chatWindow"},
                    height="45vh",
                ),
                # User input, send button and wait message
                ui.card(
                    ui.input_text_area(
                        "newChat",
                        "",
                        value="",
                        width="100%",
                        spellcheck=True,
                        resize=False,
                        placeholder="Type your message here...",
                    ),
                    ui.input_action_button("send", "Send", width="100px"),
                    style="display: none;",
                    id="chatIn",
                ),
                ui.card(
                    HTML("<p><i>Scuirrel is foraging for an answer ...</i></p>"),
                    id="waitResp",
                    style="display: none;",
                ),
            ),
            col_widths=12,
        )
    ]


@module.server
def chat_server(
    input: Inputs, output: Outputs, session: Session, user, sID, postgresUser, pool
):
    # Reactive variables
    discussionID = reactive.value(0)  # Current conversation
    conceptIndex = reactive.value(0)  # Current concept index to discuss
    messages = reactive.value(None)  # Raw chat messages
    groups = reactive.value(None)  # User's groups
    botLog = reactive.value(None)  # Chat sent to the LLM

    # The quiz question popup is a separate module
    _ = quiz_server("quiz", tID=input.selTopic, sID=sID, user=user)
    newGroup = group_join_server(
        "joinGroup", user=user, groups=groups, postgresUser=postgresUser
    )

    @reactive.effect
    @reactive.event(newGroup)
    def _():
        if newGroup() is None:
            return

        groups.set(groupQuery(user.get()["uID"], postgresUser))
        return

    @reactive.effect
    @reactive.event(groups)
    def _():
        ui.update_select(
            "gID",
            choices=dict(
                zip(groups.get()["gID"].tolist(), groups.get()["group"].tolist())
            ),
        )

    # Update a custom, simple progress bar
    def progressBar(id, percent):
        @reactive.effect
        async def _():
            await session.send_custom_message(
                "progressBar", {"id": id, "percent": percent}
            )

    def scrollElement(selectors, direction="top"):
        @reactive.effect
        async def _():
            await session.send_custom_message(
                "scrollElement", {"selectors": selectors, "direction": direction}
            )

    # When a new user signs in, show / update the relevant topics
    @reactive.effect
    @reactive.event(user)
    def _():
        getGroups = groupQuery(user.get()["uID"], postgresUser)
        groups.set(getGroups)

        return

    # When a new user signs in, show / update the relevant topics
    @reactive.calc
    @reactive.event(input.gID)
    def topics():
        conn = shared.appDBConn(postgresUser)

        # Return all topics for a group
        topics = shared.pandasQuery(
            conn,
            (
                "SELECT t.* FROM \"topic\" AS 't', \"group_topic\" AS 'gt' "
                'WHERE t."tID" = gt."tID" AND gt."gID" = ? AND t."archived" = 0 '
                'ORDER BY t."topic"'
            ),
            (int(input.gID()),),
        )
        conn.close()

        return topics

    @reactive.effect
    @reactive.event(topics)
    def _():
        if not topics().empty:
            ui.update_select(
                "selTopic", choices=dict(zip(topics()["tID"], topics()["topic"]))
            )
            shared.elementDisplay("startConversation", "s", session, False)
            shared.elementDisplay("chatIn", "s", session, False)

        return

    # When the start conversation button is clicked...
    @reactive.effect
    @reactive.event(input.startConversation)
    def _():
        tID = int(topics()[topics()["tID"] == int(input.selTopic())].iloc[0]["tID"])
        conn = shared.appDBConn(postgresUser)
        cursor = conn.cursor()

        # Save the logs for the previous discussion (if any) adn wipe the chat window
        if messages.get():
            scuirrel_shared.endDiscussion(cursor, discussionID.get(), messages.get())
            ui.remove_ui("#" + module.resolve_id("conversation"))
            ui.insert_ui(
                div(id=module.resolve_id("conversation")),
                "#" + module.resolve_id("chatWindow"),
            )

        # Register the start of the  new topic discussion
        dID = shared.executeQuery(
            cursor,
            'INSERT INTO "discussion" ("tID", "sID", "start")' "VALUES(?, ?, ?)",
            (tID, sID, shared.dt()),
            lastRowId="dID",
        )
        discussionID.set(int(dID))
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
            "#" + module.resolve_id("conversation"),
        )
        botLog.set(f"---- PREVIOUS CONVERSATION ----\n--- MENTOR:\n{firstWelcome}")

        shared.elementDisplay("chatIn", "s", session)
        return tID

    # Get the concepts related to the topic
    @reactive.calc
    def concepts():
        conn = shared.appDBConn(postgresUser)
        concepts = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {int(input.selTopic())} AND "archived" = 0 ORDER BY "order"',
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
            isBot=0,
            cID=int(concepts().iloc[conceptIndex.get()]["cID"]),
            content=newChat,
        )        
        ui.insert_ui(
            HTML(
                f"<div class='userChat talk-bubble' onclick='chatSelection(this,{msg.id - 1})'><p>{escape(newChat)}</p></div>"
            ),
            "#" + module.resolve_id("conversation"),
        )
        botLog.set(botLog.get() + f"\n--- STUDENT:\n{newChat}")
        topic = topics()[topics()["tID"] == int(input.selTopic())].iloc[0]["topic"]
        scrollElement(".chatWindow .card-body")
        messages.set(msg)
        # Generate chat logs
        conversation = (
            botLog.get() + "\n---- NEW RESPONSE FROM STUDENT ----\n" + newChat
        )
        # Send the message to the LLM for processing
        botResponse(topic, concepts(), conceptIndex.get(), conversation)    
    
    def botResponse_task(topic, concepts, cIndex, conversation):
        # Check the student's progress on the current concept based on the last reply (other engine)
        engine = scuirrel_shared.progressCheckEngine(
            conversation, topic, concepts, cIndex, postgresUser = postgresUser
        )
        tries = 0
        while tries < 3:
            try:
                eval = json.loads(str(engine.query(conversation)))
                break
            except json.JSONDecodeError:
                print("Conversation agent JSON decode error, retrying...")
                tries += 1
        eval = None if tries == 3 else eval

        if eval is None:
            return {"resp": None, "eval": None}

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
    
    # Async Shiny task waiting for LLM reply
    @reactive.extended_task
    async def botResponse(topic, concepts, cIndex, conversation):        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(pool, botResponse_task, topic, concepts, cIndex, conversation)        

    # Processing LLM responses
    @reactive.effect
    def _():
        result = botResponse.result()
        eval = result["eval"]  # Evaluation of last response and progress
        resp = result["resp"]  # New response to student

        if eval is None:
            ui.notification_show(
                "SCUIRREL is having issues processing your response. Please try again later."
            )
            shared.elementDisplay("waitResp", "h", session)
            shared.elementDisplay("chatIn", "s", session)
            return

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
                "#" + module.resolve_id("conversation"),
            )
            botLog.set(botLog.get() + "\n--- MENTOR:\n" + resp)

            # Now the LLM has finished the user can send a new response
            shared.elementDisplay("waitResp", "h", session)
            ui.update_text_area("newChat", value="")
            # If conversation is over don't show new message box
            if not finished:
                shared.elementDisplay("chatIn", "s", session)
                scrollElement(".chatWindow .card-body")
            else:
                ui.insert_ui(HTML("<hr>"), "#" + module.resolve_id("conversation"))

    # When the chat feedback button is clicked
    @reactive.effect
    @reactive.event(input.chatFeedback)
    def _():
        sel = json.loads(input.selectedMsg())  # Custom JS input selectedMsg
        if sel == []:
            # With no messages selected
            ui.notification_show(
                "Please select all chat messages relevant to your feedback report"
            )
        else:
            # Ask for more details
            m = ui.modal(
                ui.input_radio_buttons(
                    "feedbackChatCode",
                    " Pick a category",
                    choices={
                        1: "Incorrect",
                        2: "Inappropriate",
                        3: "Not helpful",
                        4: "Not able to proceed",
                        5: "Other",
                    },
                    inline=True,
                ),
                ui.input_text_area(
                    "feedbackChatDetails", "Please provide more details", width="100%"
                ),
                title="Please provide some more information",
                size="l",
                footer=[
                    ui.input_action_button("feedbackChatSubmit", "Submit"),
                    ui.modal_button("Cancel"),
                ],
            )
            ui.modal_show(m)

    # Insert the issue into the DB
    @reactive.effect
    @reactive.event(input.feedbackChatSubmit)
    def _():
        # Because multiple issues can be submitted for a single conversation, we have to commit to the
        # DB immediately or it would become harder to keep track of TODO
        # This means we add a temp mID which will be updated in the end
        conn = shared.appDBConn(postgresUser)
        cursor = conn.cursor()
        fcID = shared.executeQuery(
            cursor,
            'INSERT INTO "feedback_chat"("dID","code","created","details") '
            "VALUES(?,?,?,?)",
            (
                discussionID.get(),
                int(input.feedbackChatCode()),
                shared.dt(),
                input.feedbackChatDetails(),
            ),
            lastRowId="fcID",
        )
        tempID = json.loads(input.selectedMsg())
        tempID.sort()
        _ = shared.executeQuery(
            cursor,
            f'INSERT INTO "feedback_chat_msg"("fcID","mID") VALUES({fcID},?)',
            [(x,) for x in tempID],
        )
        conn.commit()
        conn.close()
        # Remove modal and show confirmation
        ui.modal_remove()
        ui.notification_show("Feedback successfully submitted!", duration=3)

    return {"dID": discussionID, "messages": messages}
