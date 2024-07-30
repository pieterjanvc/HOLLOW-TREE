# ------ Login Reset Password Module ------
# -----------------------------------------

# -- General
import bcrypt

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui
from htmltools import HTML

import shared.shared as shared


# --- UI
@module.ui
def login_reset_ui():
    return [
        ui.card(
            ui.card_header("Reset password"),
            ui.input_text("rUsername", "Username"),
            ui.input_action_button("request", "Request reset code", width="250px"),
            HTML("""<p><i>You will need to request a new access code from your 
                        administrator before resetting your password.</i></p>"""),
            ui.input_password("rPassword", "New password"),
            ui.input_password("rPassword2", "Repeat new password"),
            ui.input_text("rAccessCode", "Reset code"),
            ui.input_action_button("reset", "Reset password", width="250px"),
        ),
    ]


# --- Server
@module.server
def login_reset_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    postgresUser,
):
    # Default to anonymous
    conn = shared.appDBConn(postgresUser=postgresUser)
    user = shared.pandasQuery(conn, 'SELECT * FROM "user" WHERE "uID" = 1')
    conn.close()
    user = reactive.value(user.to_dict(orient="records")[0])

    # Request reset code
    @reactive.effect
    @reactive.event(input.request)
    def _():
        username = input.rUsername()

        conn = shared.appDBConn(postgresUser=postgresUser)
        checkUser = shared.authCheck(conn, username, "")

        invalid = checkUser["user"] is None
        shared.inputNotification(
            session, "rUsername", "This username does not exist", invalid
        )

        if invalid:
            conn.close()
            return

        # Generate a new access code to be used for resetting password
        cursor = conn.cursor()
        uID = checkUser["user"]["uID"].iloc[0]

        # Check if there are any existing, unused reset codes
        existing = shared.pandasQuery(
            conn,
            'SELECT * FROM "accessCode" WHERE "uID_user" = ? AND "codeType" = 1 AND "used" IS NULL',
            (uID,),
        )

        invalid = existing.shape[0] > 0
        shared.inputNotification(
            session,
            "request",
            "You already requested a new reset code, please contact your admin to get it",
            invalid,
        )

        if invalid:
            conn.close()
            return

        # Generate a new reset code
        code = shared.generate_access_codes(cursor=cursor, codeType = 1, creatorID=uID, userID=uID)
        conn.commit()
        conn.close()

        # Clear the input fields
        ui.update_text_area("rUsername", value="")
        ui.update_text_area("rPassword", value="")
        ui.update_text_area("rPassword2", value="")
        ui.update_text_area("rAccessCode", value="")

        shared.inputNotification(
            session,
            "request",
            "SUCCESS: Contact an admin to get your reset code",
            colour="blue",
        )

    # Reset password
    @reactive.effect
    @reactive.event(input.reset)
    def _():
        username = input.rUsername()
        accessCode = input.rAccessCode()

        conn = shared.appDBConn(postgresUser=postgresUser)
        checkUser = shared.authCheck(conn, username, "")

        invalid = checkUser["user"] is None
        shared.inputNotification(
            session, "rUsername", "This username does not exist", invalid
        )

        if invalid:
            conn.close()
            return

        # Check the passwords
        pCheck = shared.passCheck(input.rPassword(), input.rPassword2())
        shared.inputNotification(session, "rPassword2", pCheck, pCheck)
        if pCheck:
            conn.close()
            return

        # Check the access code
        code = shared.accessCodeCheck(
            conn=conn,
            accessCode=accessCode,
            codeType=1,
            uID=checkUser["user"]["uID"].iloc[0],
        )

        invalid = code is None
        shared.inputNotification(session, "rAccessCode", "Invalid reset code", invalid)
        if invalid:
            conn.close()
            return

        # Update the password
        cursor = conn.cursor()
        uID = int(checkUser["user"]["uID"].iloc[0])
        dt = shared.dt()

        hashed = bcrypt.hashpw(input.rPassword().encode("utf-8"), bcrypt.gensalt())
        _ = shared.executeQuery(
            cursor,
            'UPDATE "user" SET "password" = ?, "modified" = ? WHERE "uID" = ?',
            (hashed.decode("utf-8"), dt, uID),
        )

        # Update the access code to show it has been used
        _ = shared.executeQuery(
            cursor,
            'UPDATE "accessCode" SET "uID_user" = ?, "used" = ? WHERE "aID" = ?',
            (uID, dt, int(code["aID"].iloc[0])),
        )
        conn.commit()
        conn.close()

        # Clear the input fields
        ui.update_text_area("rUsername", value="")
        ui.update_text_area("rPassword", value="")
        ui.update_text_area("rPassword2", value="")
        ui.update_text_area("rAccessCode", value="")

        shared.inputNotification(
            session, "reset", "Successfully updated password", colour="blue"
        )

    return
