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

# Llamaindex
from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

# --- CLASSES


# Messages and conversation
class Conversation:
    def __init__(self):
        self.id = 0
        columns = {
            "id": int,
            "cID": int,
            "isBot": int,
            "timeStamp": str,
            "content": str,
            "pCode": str,
            "pMessage": str,
        }
        self.messages = pd.DataFrame(columns=columns.keys()).astype(columns)

    def add_message(
        self,
        cID: int,
        isBot: int,
        content: str,
        pCode: int = None,
        pMessage: str = None,
        timeStamp: str = None,
    ):
        timeStamp = timeStamp if timeStamp else shared.dt()
        self.messages = pd.concat(
            [
                self.messages,
                pd.DataFrame.from_dict(
                    {
                        "id": [self.id],
                        "cID": [cID],
                        "timeStamp": [timeStamp],
                        "isBot": [isBot],
                        "content": [content],
                        "pCode": [pCode],
                        "pMessage": [pMessage],
                    }
                ),
            ],
            ignore_index=True,
        )
        self.id += 1

    def addEval(self, score, comment):
        self.messages.at[self.messages.index[-1], "pCode"] = score
        self.messages.at[self.messages.index[-1], "pMessage"] = comment

    def astuple(self, order=None):
        if order is not None and (
            set(["cID", "isBot", "timeStamp", "content", "pCode", "pMessage"])
            != set(order)
        ):
            raise ValueError("messages order not correct")
        out = self.messages.drop(columns=["id"])
        if order:
            out = out[order]
        return [tuple(x) for x in out.to_numpy()]


# ---- VARS & FUNCTIONS ----
def groupQuery(user, postgresUser, demo=shared.addDemo):
    includeDemo = (
        'UNION SELECT "gID", "group" FROM "group" WHERE "gID" = 1 ' if demo else ""
    )
    userFilter = 'AND m."uID" = ? ' if user["adminLevel"] < 3 else ""
    params = (user["uID"],) if user["adminLevel"] < 3 else ()

    conn = shared.appDBConn(postgresUser)
    getGroups = shared.pandasQuery(
        conn,
        (
            'SELECT g."gID", g."group" '
            'FROM "group_member" AS m, "group_topic" AS t, "group" AS g '
            f'WHERE m."gID" = g."gID" AND t."gID" = g."gID" {userFilter}'
            'AND t."tID" IN (SELECT DISTINCT "tID" FROM "concept" WHERE "status" = 0) '
            f'{includeDemo} ORDER BY "group"'
        ),
        params,
    )
    conn.close()
    return getGroups


# Chat Agent - Adapt the chat engine to the topic
def chatEngine(topic, concepts, cIndex, eval):
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

    cDone = (
        ""
        if cIndex == 0
        else "Already discussed:\n* " + "\n* ".join(concepts.head(cIndex)["concept"])
    )

    cToDo = "Will be discussed later:\n* " + "\n* ".join(
        concepts[(cIndex + 1) :]["concept"]
    )

    cAll = "CONCEPT LIST:\n* " + "\n* ".join(concepts["concept"])

    currentConcept = concepts.iloc[cIndex]["concept"]
    prevConcept = concepts.iloc[cIndex - 1]["concept"] if cIndex > 0 else ""

    if int(eval["progress"]) == 1:
        if int(eval["score"]) == 1:
            progress = (
                f"You are currently discussing the following concept: {currentConcept}\n"
                "It seems the student did not understand the question, or is very mistaken. "
                "Try and reformulate the question without giving away the whole concept."
            )
        elif int(eval["score"]) == 2:
            progress = (
                f"You are currently discussing the following concept: {currentConcept}\n"
                "It seems you need to explore this concept a bit more "
                "with the student as there is still lack of understanding or mistakes were made. "
                "Be carful not to give away any crucial information but do provide hints."
            )
        else:
            progress = (
                f"It seems the student has a basic understanding of the concept: {currentConcept} \n"
                "However, you feel you can nudge them just a little further"
            )
    else:
        if int(eval["score"]) < 3:
            progress = (
                "It seems the student is stuck:\n"
                f"FIRST - Explain the concept concept they are stuck on: {prevConcept}. Don't ask questions about it anymore\n"
                f"SECOND - move on to the next concept: {currentConcept}"
            )
        else:
            progress = (
                f"It seems the student has a good enough understanding of the previous concept: {prevConcept} \n"
                " Provide relevant feedback and highlight any parts of this previous "
                "concept that were not explicitly covered in the conversation. \n\n"
                f"Your next question will focus on: {currentConcept}"
            )

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                f"""You (MENTOR) are chatting with a student (STUDENT) to review their understanding of the following topic: 
{topic}

You are using a list of concepts (i.e. facts / information) about this topic to guide the conversation.
{cAll}

{progress}

IMPORTANT:
- DO NOT use the concept text as part of your question. Instead ask questions of which the answer is the concept text
- If the last student response is asking about something not related to the current concept, please steer them back
- Do not lecture, i.e. providing dry definitions, but be inquisitive and ask questions 
- Make sure not to deviate from the concepts being discussed. If your question is not related to the current concept, please adjust it
- Make the student thinks and reasons critically
- Do not go beyond what is listed in the concepts list, you can explain more, but not ask questions about adjecent concepts
- Always check the previous user messages for conceptual mistakes, like the use of incorrect terminology. Correct if needed, this is very important!"""
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
Only if necessary, make edits to ensure your response does not contain any errors and 
is not giving away the concept you are trying to test. 
"""
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    index = shared.getIndex(postgresUser=shared.postgresScuirrel)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=shared.llm,
    )


# Monitoring Agent - Adapt the chat engine to the topic
def progressCheckEngine(conversation, topic, concepts, cIndex, postgresUser):
    cDone = (
        ""
        if cIndex == 0
        else "These concepts were already covered successfully:\n* "
        + "\n* ".join(concepts.head(cIndex)["concept"])
    )

    cToDo = "The following concepts still need to be discussed:\n* " + "\n* ".join(
        concepts[cIndex:]["concept"]
    )

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
of the current concept to move on to the next one or if they are stuck and the TUTOR should provide the answer. 
You do this by evaluating the conversation using the following metrics:

score: Score the STUDENT's current understanding of the concept on a scale of 1-4
* 1: No relevant response, error, or any demonstration of understanding yet
* 2: Some understanding, but not all aspects of the topic have been covered or there are mistakes
* 3: All basics of the concept are understood and correct terminology has been used
* 4: Clear demonstration of understanding

progress: Decide how the conversation is going
* 1: The STUDENT has not demonstrated understanding of the concept yet
* 2: The conversation is stuck (only after at least two attempts) and the TUTOR should provide the answer
* 3: The STUDENT has demonstrated understanding and the conversation can move on to the next concept

comment: Reasoning behind the score and decision
In addition you will provide a very brief comment why you gave the score

OUTPUT:
Provide a response in the form of a Python dictionary: \n"""
                r'{{"score": <int>, "progress": <int>, "comment": "<reasoning>"}}'
            ),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

    # Refine Prompt
    chat_refine_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                r'Make sure the output is in Python dictionary format: {{"score": <int>, "progress": <int>, "comment": "<reasoning>"}}'
            ),
        ),
        ChatMessage(role=MessageRole.USER),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)

    index = shared.getIndex(postgresUser=postgresUser)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=shared.llm,
    )


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
                    shared.customAttr(
                        ui.input_select("gID", "Group", choices={}),
                        {"style": "display:inline-block"},
                    ),
                    group_join_ui("joinGroup"),
                ),
                ui.panel_conditional(
                    "input.gID",
                    div(
                        shared.customAttr(
                            ui.input_select(
                                "selTopic", "Topic", choices=[], width="auto"
                            ),
                            {"style": "display:inline-block"},
                        ),
                        ui.input_action_button(
                            "startConversation",
                            "Start new conversation",
                            width="auto",
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
                    height="75vh",
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

        groups.set(groupQuery(user.get(), postgresUser))
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
        getGroups = groupQuery(user.get(), postgresUser)
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
                'SELECT t.* FROM "topic" AS t, "group_topic" AS gt '
                'WHERE t."tID" = gt."tID" AND gt."gID" = ? AND t."status" = 0 '
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
            shared.elementDisplay(session, {"startConversation": "s", "chatIn": "s"})
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

        msg = Conversation()
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

        shared.elementDisplay(session, {"chatIn": "s"})
        return tID

    # Get the concepts related to the topic
    @reactive.calc
    def concepts():
        conn = shared.appDBConn(postgresUser)
        concepts = shared.pandasQuery(
            conn,
            f'SELECT * FROM "concept" WHERE "tID" = {int(input.selTopic())} AND "status" = 0 ORDER BY "order"',
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
        shared.elementDisplay(session, {"waitResp": "s", "chatIn": "h"})

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
        engine = progressCheckEngine(
            conversation, topic, concepts, cIndex, postgresUser=postgresUser
        )
        tries = 0
        while tries < 3:
            try:
                resp = str(engine.query(conversation))
                print(resp)
                eval = json.loads(resp)
                break
            except json.JSONDecodeError:
                print("Conversation agent JSON decode error, retrying...")
                tries += 1
        eval = None if tries == 3 else eval

        if eval is None:
            return {"resp": None, "eval": None}

        # See if the LLM thinks we can move on to the next concept or or not
        if int(eval["progress"]) > 1:
            cIndex += 1
        # Check if all concepts have been covered successfully
        if cIndex >= concepts.shape[0]:
            resp = f"Well done! It seems you have demonstrated understanding of everything we wanted you to know about: {topic}"
        else:
            engine = chatEngine(topic, concepts, cIndex, eval)
            # import pprint
            # pprint.pprint(engine.get_prompts())
            x = engine.query(conversation)
            resp = str(x)

        return {"resp": resp, "eval": eval}

    # Async Shiny task waiting for LLM reply
    @reactive.extended_task
    async def botResponse(topic, concepts, cIndex, conversation):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            pool, botResponse_task, topic, concepts, cIndex, conversation
        )

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
            shared.elementDisplay(session, {"waitResp": "h", "chatIn": "s"})
            return

        with reactive.isolate():
            # Check the topic progress and move on to next concept if current one scored well
            i = conceptIndex.get()
            finished = False
            if int(eval["progress"]) > 1:
                finished = False if i < (concepts().shape[0] - 1) else True
                i = i + 1 if not finished else i
                progress = int(100 * i / concepts().shape[0]) if not finished else 100
                progressBar("chatProgress", progress)

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
            shared.elementDisplay(session, {"waitResp": "h"})
            ui.update_text_area("newChat", value="")
            # If conversation is over don't show new message box
            if not finished:
                shared.elementDisplay(session, {"chatIn": "s"})
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
