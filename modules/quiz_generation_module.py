# ------ Quiz Generation Module ------
# ------------------------------------

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# -- General
import pandas as pd
import json
import asyncio
import regex as re

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, module, req
from htmltools import HTML, div, br

# -- Llamaindex
from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole


# --- Functions ---
questionStatus = {0: "Active", 1: "Draft", 2: "Archived"}


def qDisplayNames(questions, input, selected=None):
    req(not questions.empty)

    selected = selected if selected is not None else input.qID()
    showArchived = input.qShowArchived()

    questionsList = questions.copy()

    # Add the status to the question name
    questionsList["question"] = questionsList.apply(
        lambda x: f"({questionStatus[x['status']]}) {x['question']}"
        if x["status"] != 0
        else x["question"],
        axis=1,
    )

    # Filter out archived question if needed
    if not showArchived:
        questionsList = questionsList[questionsList["status"] != 2]

    # Hide or show the edit and status buttons if there are no question to show
    if questionsList.shape[0] == 0:
        selected = None

    else:
        questionsList = questionsList.sort_values(["status", "question"])
        if selected:
            selected = str(
                questionsList["qID"].iloc[0]
                if int(selected) not in list(questionsList["qID"])
                else selected
            )

    # Update the select input with the new question
    ui.update_select(
        "qID",
        choices=dict(zip(questionsList["qID"], questionsList["question"])),
        selected=selected,
    )

    return


# LLM engine for generation
def quizEngine():
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

    # System prompt
    chat_text_qa_msgs = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=(
                """
Generate a question focused on the highlighted concept and take the following into account:
* If possible integrate across multiple concepts. 
* Do NOT mention the topic as part of the question (that's inferred) 
* Try to generate a question that that forces the student to think critically (not just a short definition).
* Generate 4 possible answers (A, B, C, D), with only ONE correct option, and an explanation why each option is correct or incorrect.

The output should be a python dictionary according to the template below. Make sure the "answer" field is a single capital letter (e.g. A):
{{
"question": "<Insert your question here>",
"answer": "<Insert the correct option letter here>",
"optionA": "<Insert option A here>",
"explanationA": "<Insert explanation for option A here>",
"optionB": "<Insert option B here>",
"explanationB": "<Insert explanation for option B here>",
"optionC": "<Insert option C here>",
"explanationC": "<Insert explanation for option C here>",
"optionD": "<Insert option D here>",
"explanationD": "<Insert explanation for option D here>"
}}"""
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
                "Make sure the provided response is a Python dictionary. "
                "Double check correct use of quotes and make sure the answer field is a single capital letter (e.g. A)"
            ),
        ),
        ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
    ]
    refine_template = ChatPromptTemplate(chat_refine_msgs)
    index = shared.getIndex(postgresUser=shared.postgresAccorns)

    return index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=shared.llm,
    )


# --- UI ---
@module.ui
def quiz_generation_ui():
    return [
        ui.head_content(
            ui.tags.style("""
            #revise * {                
                display:flex;
                vertical-align: middle;  
                padding: 0;
                margin: 1px;
                font-family: inherit;
                font-size: inherit;
                resize: none;
                field-sizing: content;
                    }
            #revise .shiny-bound-input {
                border:none;
                min-height: 1.7em;
                background: #f2f0f0;
                      }
            #revise .control-label {
                white-space:nowrap;
                font-weight: bold;
            }
        """)
        ),
        ui.card(
            ui.card_header("Questions by Topic"),
            # Dropdown of topics and questions per topic
            ui.input_select("gID", "Group", choices={}),
            ui.input_select("qtID", "Pick a topic", choices=[], width="400px"),
            div(
                shared.customAttr(
                    ui.input_select("qID", "Questions", choices=[], width="400px"),
                    {"style": "display:inline-block"},
                ),
                shared.customAttr(
                    ui.input_checkbox(
                        "qShowArchived",
                        "Show archived",
                        value=False,
                    ),
                    {"style": "display:inline-block"},
                ),
            ),
            # Buttons to add or archive questions and message when busy generating
            ui.input_action_button("qGenerate", "Generate new", width="180px"),
        ),
        # Only show this panel if there is at least one question
        ui.panel_conditional(
            "input.qID",
            ui.card(
                ui.card_header("Review question"),
                # Save updates
                ui.input_radio_buttons(
                    "qStatus", "Status", choices=questionStatus, inline=True
                ),
                ui.input_action_button("qEdit", "Edit question", width="180px"),
                # Show a preview of the question
                ui.output_ui("quizQuestionPreview", style=""),
                id=module.resolve_id("qEditPanel"),
            ),
        ),
    ]


# --- Server ---
@module.server
def quiz_generation_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    sID,
    user,
    topicsx,
    groups,
    postgresUser,
    pool,
):
    topics = reactive.value(None)
    questions = reactive.value(None)

    @reactive.effect
    @reactive.event(groups)
    def _():
        ui.update_select(
            "gID",
            choices=dict(
                zip(groups.get()["gID"].tolist(), groups.get()["group"].tolist())
            ),
        )

        if groups.get().shape[0] == 0:
            shared.inputNotification(
                session,
                "qID",
                "Create a group and a topic before generating a question",
            )
            shared.elementDisplay(session, {"qGenerate": "d", "qEditPanel": "h"})

    @reactive.effect
    @reactive.event(input.gID, topicsx)
    def _():
        # Get all active topics from the accorns database
        conn = shared.appDBConn(postgresUser=postgresUser)
        activeTopics = shared.pandasQuery(
            conn,
            (
                'SELECT t.* FROM "topic" AS t, "group_topic" AS gt '
                'WHERE t."tID" = gt."tID" AND gt."gID" = ? AND t."status" = 0 '
                'ORDER BY t."topic"'
            ),
            (int(input.gID()),),
        )
        conn.close()

        ui.update_select(
            "qtID", choices=dict(zip(activeTopics["tID"], activeTopics["topic"]))
        )

        if activeTopics.shape[0] == 0:
            shared.inputNotification(
                session, "qID", "This group has no active topics yet"
            )
            shared.elementDisplay(
                session, {"qGenerate": "d", "qEditPanel": "h", "qShowArchived": "d"}
            )
        else:
            shared.inputNotification(session, "qID", show=False)
            shared.elementDisplay(session, {"qGenerate": "e"})

        topics.set(activeTopics)

    @render.ui
    def quizQuestionPreview():
        req(input.qID())

        q = questions.get()[questions.get()["qID"] == int(input.qID())].iloc[0]

        return HTML(
            f"<b>{q['question']}</b><ol type='A'><li>{q['optionA']}</li>"
            f"<li>{q['optionB']}</li><li>{q['optionC']}</li>"
            f"<li>{q['optionD']}</li></ol><i>Correct answer: {q['answer']}</i>"
            "<i><b>Explanations:</b><ol type='A'><li>"
            f"{q['explanationA']}</li><li>{q['explanationB']}</li>"
            f"<li>{q['explanationC']}</li><li>{q['explanationD']}</li></ol></i>"
        )

    # When the generate button is clicked...
    @reactive.effect
    @reactive.event(input.qGenerate)
    def _():
        shared.elementDisplay(
            session,
            {
                "qGenerate": "d",
                "qEditPanel": "h",
                "gID": "d",
                "qtID": "d",
                "qID": "d",
                "qEditPanel": "h",
                "qShowArchived": "d",
            },
        )
        shared.inputNotification(
            session, "qID", "Generating a question...", colour="blue"
        )

        # Get the topic
        topic = topics.get()[topics.get()["tID"] == int(input.qtID())].iloc[0]["topic"]

        conn = shared.appDBConn(postgresUser=shared.postgresAccorns)

        # Get the concept with the least questions
        conceptList = shared.pandasQuery(
            conn,
            'SELECT "cID", max("concept") as "concept", count(*) as n FROM '
            f'(SELECT "cID", "concept" FROM "concept" WHERE "tID" = {int(input.qtID())} AND "status" = 0 '
            f'UNION ALL SELECT "cID", \'\' as concept FROM "question" where "tID" = {int(input.qtID())}) GROUP BY "cID"',
        )

        cID = int(
            conceptList[conceptList["n"] == min(conceptList["n"])]
            .sample(1)["cID"]
            .iloc[0]
        )
        prevQuestions = shared.pandasQuery(
            conn,
            f'SELECT "question" FROM "question" WHERE "cID" = {cID} AND "status" = 0',
        )
        conn.close()

        focusConcept = "* ".join(conceptList[conceptList["cID"] == cID]["concept"])
        conceptList = "* " + "\n* ".join(conceptList["concept"])
        if prevQuestions.shape[0] == 0:
            prevQuestions = ""
        else:
            prevQuestions = (
                "The following questions have already been generated so try to focus on a different aspect "
                "related to the concept if possible:\n"
                "* " + "\n* ".join(prevQuestions["question"])
            )

        info = f"""Generate a multiple choice question to test a student who just learned about the following topic: 
    {topic}.\n
    The following concepts were covered in this topic:
    {conceptList}\n
    The question should center around the following concept:
    {focusConcept}\n
    {prevQuestions}"""
        botResponse(quizEngine(), info, cID)

    def botResponse_task(quizEngine, info, cID):
        # Given the LLM output might not be correct format (or fails to convert to a DF, try again if needed)
        valid = False
        tries = 0
        while not valid:
            try:
                x = str(quizEngine.query(info))
                resp = pd.json_normalize(json.loads(x))
                # Make sure only to keep one capital letter for the answer
                resp["answer"] = re.search("[A-D]", resp["answer"].iloc[0]).group(0)[0]
                valid = True
            except Exception as e:
                import traceback

                print(("Failed to generate quiz question\n" + str(e)))
                print(traceback.format_exc())
                if tries > 1:
                    return {"resp": None, "cID": cID}
                tries += 1

        return {"resp": resp, "cID": cID}

    # Async Shiny task waiting for LLM reply
    @reactive.extended_task
    async def botResponse(quizEngine, info, cID):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(pool, botResponse_task, quizEngine, info, cID)

    # Processing LLM response
    @reactive.effect
    def _():
        # Populate the respective UI outputs with the questions details
        resp = botResponse.result()

        if resp["resp"] is None:
            accorns_shared.modalMsg(
                "The generation of a question with the LLM failed, try again later",
                "Error",
            )
            return

        with reactive.isolate():
            q = resp["resp"].iloc[0]  # For now only processing one
            # Save the questions in the appAB
            conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
            cursor = conn.cursor()
            # Insert question
            qID = shared.executeQuery(
                cursor,
                'INSERT INTO "question"("sID","tID","cID","question","answer","status","created","modified",'
                '"optionA","explanationA","optionB","explanationB","optionC","explanationC","optionD","explanationD")'
                "VALUES(?,?,?,?,?,1,?,?,?,?,?,?,?,?,?,?)",
                (
                    sID,
                    int(input.qtID()),
                    resp["cID"],
                    q["question"],
                    q["answer"],
                    shared.dt(),
                    shared.dt(),
                    q["optionA"],
                    q["explanationA"],
                    q["optionB"],
                    q["explanationB"],
                    q["optionC"],
                    q["explanationC"],
                    q["optionD"],
                    q["explanationD"],
                ),
                lastRowId="qID",
            )
            q = shared.pandasQuery(
                conn,
                f'SELECT * FROM "question" WHERE "tID" = {int(input.qtID())}',
            )
            conn.commit()
            conn.close()

            questions.set(q)
            qDisplayNames(q, input, qID)

            shared.elementDisplay(
                session,
                {
                    "qGenerate": "e",
                    "qEditPanel": "s",
                    "gID": "e",
                    "qtID": "e",
                    "qID": "e",
                    "qEditPanel": "s",
                    "qShowArchived": "e",
                },
            )

            shared.inputNotification(session, "qID", show=False)

    @reactive.effect
    @reactive.event(input.qtID)
    def _():
        # Get the question info from the DB
        conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
        q = shared.pandasQuery(
            conn,
            f'SELECT * FROM "question" WHERE "tID" = {int(input.qtID())} ',
        )
        conn.close()

        if q.shape[0] == 0:
            shared.elementDisplay(session, {"qEditPanel": "h", "qShowArchived": "d"})
        else:
            shared.elementDisplay(session, {"qEditPanel": "s", "qShowArchived": "e"})

        # Update the UI
        questions.set(q)
        qDisplayNames(q, input)

    @reactive.effect
    @reactive.event(input.qEdit)
    def _():
        q = questions.get()[questions.get()["qID"] == int(input.qID())].iloc[0]
        modal = ui.modal(
            div(
                # Fields to edit any part of the question
                ui.input_text_area(
                    "rqQuestion",
                    "Question",
                    value=q["question"],
                    width="100%",
                ),
                br(),
                ui.input_text_area(
                    "rqOA",
                    "Option A",
                    value=q["optionA"],
                    width="100%",
                ),
                ui.input_text_area(
                    "rqOAexpl",
                    "Explanation A",
                    value=q["explanationA"],
                    width="100%",
                ),
                br(),
                ui.input_text_area(
                    "rqOB",
                    "Option B",
                    value=q["optionB"],
                    width="100%",
                ),
                ui.input_text_area(
                    "rqOBexpl",
                    "Explanation B",
                    value=q["explanationB"],
                    width="100%",
                ),
                br(),
                ui.input_text_area(
                    "rqOC",
                    "Option C",
                    value=q["optionC"],
                    width="100%",
                ),
                ui.input_text_area(
                    "rqOCexpl",
                    "Explanation C",
                    value=q["explanationC"],
                    width="100%",
                ),
                br(),
                ui.input_text_area(
                    "rqOD",
                    "Option D",
                    value=q["optionD"],
                    width="100%",
                ),
                ui.input_text_area(
                    "rqODexpl",
                    "Explanation D",
                    value=q["explanationD"],
                    width="100%",
                ),
                id="revise",
            ),
            ui.input_radio_buttons(
                "rqCorrect",
                "Correct answer",
                choices=["A", "B", "C", "D"],
                selected=q["answer"],
                inline=True,
            ),
            title="Review the question and make any necessary changes",
            size="xl",
            footer=[
                ui.input_action_button("qSaveChanges", "Save Changes"),
                ui.modal_button("Cancel"),
            ],
        )
        ui.modal_show(modal)

    # Save question edits
    @reactive.effect
    @reactive.event(input.qSaveChanges)
    def _():
        # Get the original question
        q = questions.get()[questions.get()["qID"] == int(input.qID())].iloc[0]

        conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
        cursor = conn.cursor()

        fields = {
            "rqQuestion": "question",
            "rqCorrect": "answer",
            "rqOA": "optionA",
            "rqOAexpl": "explanationA",
            "rqOB": "optionB",
            "rqOBexpl": "explanationB",
            "rqOC": "optionC",
            "rqOCexpl": "explanationC",
            "rqOD": "optionD",
            "rqODexpl": "explanationD",
        }
        now = shared.dt()

        # Backup any changes
        updates = []
        values = ()
        for element, column in fields.items():
            if input[element].get().strip() != q[column]:
                accorns_shared.backupQuery(
                    cursor,
                    sID,
                    "question",
                    q["qID"],
                    column,
                    dataType="str",
                    isBot=False,
                    timeStamp=now,
                )
                updates.append(f'"{column}" = ?')
                values += (input[element].get().strip(),)
        # Update the question
        if updates != []:
            updates = ",".join(updates) + f", \"modified\" = '{now}'"
            values += (int(q["qID"]),)
            _ = shared.executeQuery(
                cursor, f'UPDATE "question" SET {updates} WHERE "qID" = ?', values
            )
            q = shared.pandasQuery(
                conn,
                f'SELECT * FROM "question" WHERE "tID" = {int(input.qtID())}',
            )
            conn.commit()
            questions.set(q)
            ui.notification_show("Your edits were successfully saved")
        else:
            ui.notification_show("No changes were detected. Nothing was saved")

        conn.close()
        ui.modal_remove()

    @reactive.effect
    @reactive.event(input.qStatus)
    def _():
        if input.qStatus() == "1":
            shared.elementDisplay(session, {"qEdit": "e"})
            shared.inputNotification(
                session,
                "qStatus",
                "Please review the question and make edits where needed",
                colour="blue",
            )
        else:
            shared.elementDisplay(session, {"qEdit": "d"})
            shared.inputNotification(
                session,
                "qStatus",
                "Questions can only be edited in 'Draft' mode",
                colour="blue",
            )

        req(input.qID())

        # Only update the status if it's different
        if questions.get()[questions.get()["qID"] == int(input.qID())].iloc[0][
            "status"
        ] == int(input.qStatus()):
            return

        conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'UPDATE "question" SET "status" = ? WHERE "qID" = ?',
            (int(input.qStatus()), int(input.qID())),
        )

        q = shared.pandasQuery(
            conn,
            f'SELECT * FROM "question" WHERE "tID" = {int(input.qtID())}',
        )
        conn.commit()
        conn.close()

        questions.set(q)
        qDisplayNames(q, input)

    @reactive.effect
    @reactive.event(input.qShowArchived, ignore_init=True)
    def _():
        q = questions.get()
        qDisplayNames(q, input)

    @reactive.effect
    @reactive.event(input.qID)
    def _():
        status = questions.get()[questions.get()["qID"] == int(input.qID())].iloc[0][
            "status"
        ]
        ui.update_radio_buttons("qStatus", selected=str(status))

    return
