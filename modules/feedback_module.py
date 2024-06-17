# ------ Feedback Module ------
# -----------------------------

import shared.shared as shared

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui

# --- UI
@module.ui
def feedback_ui():
    return ui.input_action_button("feedback", "Provide Feedback"),

@module.server
def feedback_server(input: Inputs, output: Outputs, session: Session, sID, postgresUser):

    @reactive.effect
    @reactive.event(input.feedback)
    def _():
        # Show a modal asking for more details
        m = ui.modal(
            ui.input_radio_buttons(
                "feedbackCode",
                "Pick a feedback category",
                choices={
                    1: "User experience (overall functionality, intuitiveness)",
                    2: "Content (descriptions, labels, messages, ...)",
                    3: "Design (layout, accessibility)",
                    4: "Performance (speed, crashes, unexpected behavior)",
                    5: "Suggestion for improvement / new feature",
                    6: "Other",
                },
                inline=False,
                width="100%",
            ),
            ui.tags.p(
                "Please note that if you have chat specific feedback to use the dedicated button instead!",
                style="color:red;",
            ),
            ui.input_text_area(
                "feedbackDetails", "Please provide more details", width="100%"
            ),
            ui.input_text(
                "feedbackContact", "(optional) Contact email address", width="100%"
            ),
            ui.tags.i(
                "Please note that providing your email address will link all session details "
                "to this feedback report (no longer anonymous)"
            ),
            title="Please provide some more information",
            size="l",
            footer=[
                ui.input_action_button("feedbackSubmit", "Submit"),
                ui.modal_button("Cancel"),
            ],
        )
        ui.modal_show(m)


    # Register feedback in the appDB
    @reactive.effect
    @reactive.event(input.feedbackSubmit)
    def _():
        conn = shared.appDBConn(postgresUser)
        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'INSERT INTO "feedback_general"("sID","code","created","email","details") VALUES(?,?,?,?,?)',
            (
                sID,
                input.feedbackCode(),
                shared.dt(),
                input.feedbackContact(),
                input.feedbackDetails(),
            ),
        )
        conn.commit()
        conn.close()
        ui.modal_remove()
        ui.notification_show("Thank you for sharing feedback", duration=3)
    
    return


