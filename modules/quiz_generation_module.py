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
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, module
from htmltools import HTML, div, br

# -- Llamaindex
from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole


# --- Functions ---
questionStatus = {0: "Active", 1: "Draft", 2: "Archived"}

def qDisplayNames(questions, input, selected = None):

    selected = selected if selected is not None else input.qID()
    showArchived = input.qShowArchived()    
    
    questionsList = questions.copy()

    # Add the status to the question name
    questionsList["question"] = questionsList.apply(
        lambda x: f"({questionStatus[x['status']]}) {x['question']}" if x["status"] != 0 else x["question"],
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
            selected = str(questionsList["qID"].iloc[0] if int(selected) not in list(questionsList["qID"]) else selected) 

    # Update the select input with the new question
    ui.update_select("qID", choices=dict(zip(questionsList["qID"], questionsList["question"])),
                         selected=selected)
    
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
            div(shared.customAttr(ui.input_select("qID", "Question", choices=[], width="400px"),
                    {'style': 'display:inline-block'}),       
                    shared.customAttr(ui.input_checkbox("qShowArchived", "Show archived", value=False,),
                                        {'style': 'display:inline-block'},)),
            # Buttons to add or archive questions and message when busy generating
            ui.input_action_button("qGenerate", "Generate new", width="180px"),
        ),
        # Only show this panel if there is at least one question
        ui.panel_conditional(
            "input.qID",
            ui.card(
                ui.card_header("Review question"),               
                # Save updates
                ui.input_radio_buttons("qStatus", "Status", choices=questionStatus, inline=True),
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
            shared.inputNotification(session, "qID", "Create a group and a topic before generating a question")
            shared.elementDisplay(session, {"qGenerate": "d", "qEditPanel": "h"})

    @reactive.effect
    @reactive.event(input.gID, topicsx)
    def _():
        # req(user.get()["uID"] != 1)

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
            shared.inputNotification(session, "qID", "This group has no active topics yet")
            shared.elementDisplay(session, {"qGenerate": "d", "qEditPanel": "h"})

        topics.set(activeTopics)

    @render.ui
    @reactive.event(input.qID)
    def quizQuestionPreview():

        if questions.get() is None:
            return
        
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
        shared.elementDisplay(session, {"qGenerate": "d", "qEditPanel": "h", "gID": "d", 
                                        "qtID": "d", "qID": "d", "qEditPanel": "h"})
        shared.inputNotification(session, "qID", "Generating a question...", colour="blue")

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
                "VALUES(?,?,?,?,?,0,?,?,?,?,?,?,?,?,?,?)",
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

            # Update the UI
            ui.update_select(
                "qID", choices=dict(zip(q["qID"], q["question"])), selected=qID
            )
            shared.elementDisplay(session, {"qGenerate": "e", "qEditPanel": "s", "gID": "e", 
                                            "qtID": "e", "qID": "e", "qEditPanel": "s"})            

            shared.inputNotification(session, "qID", show=False)

    @reactive.effect
    @reactive.event(input.qtID)
    def _():
        # Get the question info from the DB
        conn = shared.appDBConn(postgresUser=shared.postgresAccorns)

        ## No longer needed given active status is now a requirement to have concepts
        # q = shared.pandasQuery(
        #     conn,
        #     f'SELECT "cID" FROM "concept" WHERE "tID" = {int(input.qtID())} AND "status" = 0',
        # )

        # if q.shape[0] == 0:
        #     shared.elementDisplay(session, {"qGenerate": "d", "qEditPanel": "h"}) 
        #     shared.inputNotification(session, "qID", "This topic has no concepts yet, please add some first in the Topics tab")
           
        #     return
        
        q = shared.pandasQuery(
            conn,
            f'SELECT * FROM "question" WHERE "tID" = {int(input.qtID())} ',
        )
        conn.close()          

        if q.shape[0] == 0:
            shared.elementDisplay(session, {"qGenerate": "e", "qArchive": "h", "qEditPanel": "h"})
        else:
            shared.elementDisplay(session, {"qGenerate": "e", "qArchive": "s", "qEditPanel": "s"})

        # Update the UI
        questions.set(q)
        qDisplayNames(q, input)
        #ui.update_select("qID", choices=dict(zip(q["qID"], q["question"])))

    # @reactive.effect
    # @reactive.event(input.qID)
    # def _():
        
    #     shared.elementDisplay(session, {"qGenerate": "e", "qArchive": "s"})
        
    #     # Get the question info from the DB
    #     conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    #     q = shared.pandasQuery(
    #         conn, f'SELECT * FROM "question" WHERE "qID" = {input.qID()}'
    #     ).iloc[0]
    #     conn.close()
    #     # Update the UI
    #     ui.update_text_area("rqQuestion", value=q["question"])
    #     ui.update_text("rqOA", value=q["optionA"])
    #     ui.update_text_area("rqOAexpl", value=q["explanationA"])
    #     ui.update_text("rqOB", value=q["optionB"])
    #     ui.update_text_area("rqOBexpl", value=q["explanationB"])
    #     ui.update_text("rqOC", value=q["optionC"])
    #     ui.update_text_area("rqOCexpl", value=q["explanationC"])
    #     ui.update_text("rqOD", value=q["optionD"])
    #     ui.update_text_area("rqODexpl", value=q["explanationD"])
    #     ui.update_radio_buttons("rqCorrect", selected=q["answer"])

    # # Save question edits
    # @reactive.effect
    # @reactive.event(input.qSaveChanges)
    # def _():
    #     # Get the original question
    #     conn = shared.appDBConn(postgresUser=shared.postgresAccorns)
    #     cursor = conn.cursor()
    #     q = shared.pandasQuery(
    #         conn,
    #         'SELECT "qID","question","answer","optionA","explanationA","optionB","explanationB","optionC",'
    #         f'"explanationC","optionD","explanationD" FROM "question" WHERE "qID" = {input.qID()}',
    #     ).iloc[0]
    #     qID = int(q.iloc[0])
    #     fields = [
    #         "rqQuestion",
    #         "rqCorrect",
    #         "rqOA",
    #         "rqOAexpl",
    #         "rqOB",
    #         "rqOBexpl",
    #         "rqOC",
    #         "rqOCexpl",
    #         "rqOD",
    #         "rqODexpl",
    #     ]
    #     now = shared.dt()

    #     # Backup any changes
    #     updates = []
    #     for i, v in enumerate(fields):
    #         if input[v].get() != q.iloc[i + 1]:
    #             accorns_shared.backupQuery(
    #                 cursor, sID, "question", qID, q.index[i + 1], None, now
    #             )
    #             updates.append(f"\"{q.index[i+1]}\" = '{input[v].get()}'")
    #     # Update the question
    #     if updates != []:
    #         updates = ",".join(updates) + f", \"modified\" = '{now}'"
    #         _ = shared.executeQuery(
    #             cursor, f'UPDATE "question" SET {updates} WHERE "qID" = ?', (qID,)
    #         )
    #         conn.commit()
    #         accorns_shared.modalMsg(
    #             "Your edits were successfully saved", "Update complete"
    #         )
    #     else:
    #         accorns_shared.modalMsg("No changes were detected")

    #     conn.close()   

    @reactive.effect
    @reactive.event(input.qEdit)
    def _():
        modal = ui.modal(
            div(
                    # Fields to edit any part of the question
                    ui.input_text_area(
                        "rqQuestion", "Question", width="100%",
                    ),br(),                
                    ui.input_text("rqOA", "Option A", width="100%",),
                    ui.input_text_area(
                        "rqOAexpl", "Explanation A", width="100%",
                    ),
                    ui.input_text("rqOB", "Option B", width="100%",),
                    ui.input_text_area(
                        "rqOBexpl", "Explanation B", width="100%",
                    ),
                    ui.input_text("rqOC", "Option C", width="100%",),
                    ui.input_text_area(
                        "rqOCexpl", "Explanation C", width="100%",
                    ),
                    ui.input_text("rqOD", "Option D", width="100%",),
                    ui.input_text_area(
                        "rqODexpl", "Explanation D", width="100%",
                    ),id="revise",),
                ui.input_radio_buttons(
                    "rqCorrect",
                    "Correct answer",
                    choices=["A", "B", "C", "D"],
                    inline=True,
                ),
                size = "xl"
        )
        ui.modal_show(modal)

    return

