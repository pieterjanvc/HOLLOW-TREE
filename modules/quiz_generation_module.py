# ------ Quiz Generation Module ------
# ------------------------------------

import shared.shared as shared
import ACCORNS.accorns_shared as accorns_shared

# -- General
import os
import pandas as pd
import json

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render, req
from htmltools import HTML, div

# -- Llamaindex
from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

# --- UI ---

@module.ui
def quiz_generation_ui():
    return ([
        ui.card(
                ui.card_header("Questions by Topic"),
                # Dropdown of topics and questions per topic
                ui.input_select(
                    "qtID", "Pick a topic", choices=[], width="400px"
                ),
                ui.input_select("qID", "Question", choices=[], width="400px"),
                # Buttons to add or archive questions and message when busy generating
                div(
                    ui.input_action_button("qGenerate", "Generate new", width="180px"),
                    ui.input_action_button("qArchive", "Archive selected", width="180px"),
                    id="qBtnSet",
                    style="display:inline",
                ),
                div(
                    HTML("<i>Generating a new question...</i>"),
                    id="qBusyMsg",
                    style="display: none;",
                )),

            # Only show this panel if there is at least one question
            ui.panel_conditional("input.qID",
                ui.card(
                    ui.card_header("Review question"),
                    # Show a preview of the question
                    ui.output_ui("quizQuestionPreview", style="display: none;"),
                    # Save updates
                    div(
                        ui.input_action_button("qSaveChanges", "Save Changes"),
                        ui.input_action_button("qDiscardChanges", "Discard Changes"),
                    ),
                    # Fields to edit any part of the question
                    ui.input_text_area(
                        "rqQuestion", "Question", width="100%", autoresize=True
                    ),
                    ui.input_radio_buttons(
                        "rqCorrect",
                        "Correct answer",
                        choices=["A", "B", "C", "D"],
                        inline=True,
                    ),
                    ui.input_text("rqOA", "Option A", width="100%"),
                    ui.input_text_area(
                        "rqOAexpl", "Explanation A", width="100%", autoresize=True
                    ),
                    ui.input_text("rqOB", "Option B", width="100%"),
                    ui.input_text_area(
                        "rqOBexpl", "Explanation B", width="100%", autoresize=True
                    ),
                    ui.input_text("rqOC", "Option C", width="100%"),
                    ui.input_text_area(
                        "rqOCexpl", "Explanation C", width="100%", autoresize=True
                    ),
                    ui.input_text("rqOD", "Option D", width="100%"),
                    ui.input_text_area(
                        "rqODexpl", "Explanation D", width="100%", autoresize=True
                    )))
    ])

# --- Server ---
@module.server
def quiz_generation_server(input: Inputs, output: Outputs, session: Session, sID, index,topics, user):
    
    # Set the topics
    @reactive.effect
    @reactive.event(topics)
    def _():
        ui.update_select("qtID", choices=dict(zip(topics.get()["tID"], topics.get()["topic"])))

    @render.ui
    def quizQuestionPreview():
        return HTML(
            f"<b>{input.rqQuestion()}</b><ol type='A'><li>{input.rqOA()}</li>"
            f"<li>{input.rqOB()}</li><li>{input.rqOC()}</li>"
            f"<li>{input.rqOD()}</li></ol><i>Correct answer: {input.rqCorrect()}</i><hr>"
        )

    # LLM engine for generation
    @reactive.calc
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
    * Generate 4 possible answers, with only ONE correct option, and an explanation why each option is correct or incorrect.

    You will output a python dictionary string according to this template:
    {{"question":"<add question>","answer":"<e.g. A>","optionA":"","explanationA":"","optionB":"","explanationB":"","optionC":"","explanationC":"","optionD":"","explanationD":""}}"""
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
                    "Make sure the provided response is a Python dictionary. Double check correct use of quotes"
                ),
            ),
            ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
        ]
        refine_template = ChatPromptTemplate(chat_refine_msgs)

        return index.get().as_query_engine(
            text_qa_template=text_qa_template,
            refine_template=refine_template,
            llm=shared.llm,
        )


    # When the generate button is clicked...
    @reactive.effect
    @reactive.event(input.qGenerate)
    def _():
        shared.elementDisplay("qBusyMsg", "s", session)
        shared.elementDisplay("qBtnSet", "h", session)

        topic = topics.get()[topics.get()["tID"] == int(input.qtID())].iloc[0]["topic"]

        conn = shared.appDBConn()       
        # topic = shared.pandasQuery(
        #     conn, f'SELECT "topic" FROM "topic" WHERE "tID" = {input.qtID()}'
        # )
        conceptList = shared.pandasQuery(
            conn,
            'SELECT "cID", max("concept") as "concept", count(*) as n FROM '
            f'(SELECT "cID", "concept" FROM "concept" WHERE "tID" = {int(input.qtID())} '
            f'UNION ALL SELECT "cID", \'\' as concept FROM "question" where "tID" = {int(input.qtID())}) GROUP BY "cID"',
        )
        cID = int(
            conceptList[conceptList["n"] == min(conceptList["n"])].sample(1)["cID"].iloc[0]
        )
        prevQuestions = shared.pandasQuery(
            conn,
            f'SELECT "question" FROM "question" WHERE "cID" = {cID} AND "archived" = 0',
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


    # Async Shiny task waiting for LLM reply
    @reactive.extended_task
    async def botResponse(quizEngine, info, cID):
        # Given the LLM output might not be correct format (or fails to convert to a DF, try again if needed)
        valid = False
        tries = 0
        while not valid:
            try:
                resp = str(quizEngine.query(info))
                resp = pd.json_normalize(json.loads(resp))
                valid = True
            except Exception:
                print(("Failed to generate quiz question"))
                if tries > 1:
                    return {"resp": None, "cID": cID}
                tries += 1

        return {"resp": resp, "cID": cID}


    # Processing LLM response
    @reactive.effect
    def _():
        # Populate the respective UI outputs with the questions details
        resp = botResponse.result()
        shared.elementDisplay("qBusyMsg", "h", session)
        shared.elementDisplay("qBtnSet", "s", session)

        if resp["resp"] is None:
            accorns_shared.modalMsg(
                "The generation of a question with the LLM failed, try again later", "Error"
            )
            return

        with reactive.isolate():
            q = resp["resp"].iloc[0]  # For now only processing one
            # Save the questions in the appAB
            conn = shared.appDBConn()
            cursor = conn.cursor()
            # Insert question
            qID = shared.executeQuery(
                cursor,
                'INSERT INTO "question"("sID","tID","cID","question","answer","archived","created","modified",'
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
                f'SELECT "qID", "question" FROM "question" WHERE "tID" = {int(input.qtID())} AND "archived" = 0',
            )
            conn.commit()
            conn.close()
            # Update the UI
            ui.update_select(
                "qID", choices=dict(zip(q["qID"], q["question"])), selected=qID
            )


    @reactive.effect
    @reactive.event(input.qtID)
    def _():
        # Get the question info from the DB
        conn = shared.appDBConn()
        q = shared.pandasQuery(
            conn,
            f'SELECT "qID", "question" FROM "question" WHERE "tID" = {int(input.qtID())} AND "archived" = 0',
        )
        conn.close()
        # Update the UI
        ui.update_select("qID", choices=dict(zip(q["qID"], q["question"])))


    @reactive.effect
    @reactive.event(input.qID, input.qDiscardChanges)
    def _():
        # Get the question info from the DB
        conn = shared.appDBConn()
        q = shared.pandasQuery(
            conn, f'SELECT * FROM "question" WHERE "qID" = {input.qID()}'
        ).iloc[0]
        conn.close()
        # Update the UI
        ui.update_text_area("rqQuestion", value=q["question"])
        ui.update_text("rqOA", value=q["optionA"])
        ui.update_text_area("rqOAexpl", value=q["explanationA"])
        ui.update_text("rqOB", value=q["optionB"])
        ui.update_text_area("rqOBexpl", value=q["explanationB"])
        ui.update_text("rqOC", value=q["optionC"])
        ui.update_text_area("rqOCexpl", value=q["explanationC"])
        ui.update_text("rqOD", value=q["optionD"])
        ui.update_text_area("rqODexpl", value=q["explanationD"])
        ui.update_radio_buttons("rqCorrect", selected=q["answer"])


    # Save question edits
    @reactive.effect
    @reactive.event(input.qSaveChanges)
    def _():
        # Get the original question
        conn = shared.appDBConn()
        cursor = conn.cursor()
        q = shared.pandasQuery(
            conn,
            'SELECT "qID","question","answer","optionA","explanationA","optionB","explanationB","optionC",'
            f'"explanationC","optionD","explanationD" FROM "question" WHERE "qID" = {input.qID()}',
        ).iloc[0]
        qID = int(q.iloc[0])
        fields = [
            "rqQuestion",
            "rqCorrect",
            "rqOA",
            "rqOAexpl",
            "rqOB",
            "rqOBexpl",
            "rqOC",
            "rqOCexpl",
            "rqOD",
            "rqODexpl",
        ]
        now = shared.dt()

        # Backup any changes
        updates = []
        for i, v in enumerate(fields):
            if input[v].get() != q.iloc[i + 1]:
                accorns_shared.backupQuery(
                    cursor, sID, "question", qID, q.index[i + 1], None, now
                )
                updates.append(f"\"{q.index[i+1]}\" = '{input[v].get()}'")
        # Update the question
        if updates != []:
            updates = ",".join(updates) + f", \"modified\" = '{now}'"
            _ = shared.executeQuery(
                cursor, f'UPDATE "question" SET {updates} WHERE "qID" = ?', (qID,)
            )
            conn.commit()
            accorns_shared.modalMsg("Your edits were successfully saved", "Update complete")
        else:
            accorns_shared.modalMsg("No changes were detected")

        conn.close()

    return
