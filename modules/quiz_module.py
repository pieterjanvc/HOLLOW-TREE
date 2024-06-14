# ------ Quiz Module ------
# -------------------------

import shared.shared as shared
from shared.shared import postgresScuirrel, elementDisplay
from SCUIRREL.scuirrel_shared import allowMultiGuess

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui, render
from htmltools import HTML, div

# --- UI ---

@module.ui
def quiz_ui():
    return ([
        ui.input_action_button("quizQuestion", "Take a quiz question", 
                               width="250px"),
    ])

@module.server
def quiz_server(input: Inputs, output: Outputs, session: Session, tID, sID, user):

    quizQuestion = reactive.value()

    @reactive.effect
    @reactive.event(tID)
    def _():
        # Get a random question on the topic from the DB
        conn = shared.appDBConn(postgresScuirrel)
        q = shared.pandasQuery(
            conn,
            f'SELECT "qID" FROM "question" WHERE "tID" = {tID()} AND "archived" = 0 LIMIT 1',
        )
        conn.close()

        if q.empty:
            elementDisplay("quizQuestion", "h", session)
            return
        else:
            elementDisplay("quizQuestion", "s", session)

    # Clicking the quiz button shows a modal
    @reactive.effect
    @reactive.event(input.quizQuestion)
    def _():
        # Get a random question on the topic from the DB
        conn = shared.appDBConn(postgresScuirrel)
        q = shared.pandasQuery(
            conn,
            f'SELECT * FROM "question" WHERE "tID" = {tID()} AND "archived" = 0',
        )
        conn.close()

        q = q.sample(1).iloc[0].to_dict()
        q["start"] = shared.dt()

        # UI for the quiz question popup (saved as a variable)
        @render.express
        def quizUI():
            HTML(f'<b>{q["question"]}</b><br><br>')
            ui.input_radio_buttons(
                "quizOptions",
                None,
                width="100%",
                choices={
                    "X": HTML("<i>Select an option below:</i>"),
                    "A": q["optionA"],
                    "B": q["optionB"],
                    "C": q["optionC"],
                    "D": q["optionD"],
                },
            )
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
        q["response"] = input.quizOptions()
        q["correct"] = correct + 0  # Convert to integer
        # Add the response to the database

        # Hide the answer button (don't allow for multiple guessing)
        if not allowMultiGuess:
            elementDisplay("checkAnswer", "h")

        # Add the timestamp the answer was checked
        q["check"] = shared.dt()
        quizQuestion.set(q)

        return HTML(
            f'<hr><h3>{"Correct!" if correct else "Incorrect..."}</h3>'
            f'{q["explanation" + input.quizOptions()]}'
        )


    @reactive.effect
    @reactive.event(input.qClose)
    def _():
        q = quizQuestion.get()

        # Handle the case where user returns before checking an answer
        if "check" not in q:
            q["check"] = None
            q["response"] = None
            q["correct"] = None

        # Add the response to the DB
        conn = shared.appDBConn(postgresScuirrel)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "response" ("sID", "qID", "response", "correct", "start", "check", "end")'
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                sID,
                q["qID"],
                q["response"],
                q["correct"],
                q["start"],
                q["check"],
                shared.dt(),
            ),
        )
        conn.commit()
        conn.close()
        ui.modal_remove()

    return
