# ------ Login Module ------
# --------------------------

# -- General
import bcrypt
from re import search as re_search
from re import compile as re_compile

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui
from htmltools import HTML

import shared.shared as shared
from modules.login_reset_module import login_reset_ui, login_reset_server


# --- UI
@module.ui
def login_ui():
    return [
        ui.layout_columns(
            ui.card(
                ui.card_header("Login"),
                ui.input_text("lUsername", "Username"),
                ui.input_password("lPassword", "Password"),
                ui.input_action_button("login", "Login", width="200px"),
                ui.input_action_link("showReset", "Reset password"),
            ),
            ui.card(
                ui.card_header("Create an account"),
                HTML("""<i>NOTE: This application has been built for research purposes 
                        and has not been extensively tested for security. We recommend
                        you create a unique password for this you are not using anywhere else</i>"""),
                ui.input_text("cUsername", "Username"),
                ui.panel_conditional(
                    "true" if shared.personalInfo else "false",
                    ui.input_text("cFirstName", "First name"),
                    ui.input_text("cLastName", "Last name"),
                    ui.input_text("cEmail", "Email"),
                ),
                ui.input_password("cPassword", "Password"),
                ui.input_password("cPassword2", "Repeat password"),
                ui.input_text("cAccessCode", "Access code"),
                ui.input_action_button("createAccount", "Create", width="200px"),
            ),
            col_widths=6,
        )
    ]


# --- Server
@module.server
def login_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    postgresUser,
    sessionID,
    minAdminLevel=0,
):
    # Default to anonymous
    conn = shared.appDBConn(postgresUser=postgresUser)
    user = shared.pandasQuery(conn, 'SELECT * FROM "user" WHERE "uID" = 1')
    conn.close()
    user = reactive.value(user.to_dict(orient="records")[0])

    # Login
    @reactive.effect
    @reactive.event(input.login)
    def _():
        conn = shared.appDBConn(postgresUser=postgresUser)
        userCheck = shared.authCheck(conn, input.lUsername(), input.lPassword())

        if userCheck["user"] is None:
            ui.notification_show("Invalid username")
            conn.close()
            return

        if userCheck["adminLevel"] < minAdminLevel:
            ui.notification_show(
                "You do not have the required permissions to access this application"
            )
            conn.close()
            return

        if not userCheck["password_check"]:
            ui.notification_show("Incorrect password")
            conn.close()
            return

        userCheck = userCheck["user"]

        cursor = conn.cursor()
        _ = shared.executeQuery(
            cursor,
            'UPDATE "session" SET "uID" = ? WHERE "sID" = ?',
            (int(userCheck.uID.iloc[0]), sessionID),
        )
        conn.commit()
        conn.close()

        # Clear the input fields
        ui.update_text_area("lUsername", value="")
        ui.update_text_area("lPassword", value="")

        user.set(userCheck.to_dict(orient="records")[0])

        return

    # Create an account
    @reactive.effect
    @reactive.event(input.createAccount)
    def _():
        username = input.cUsername()
        accessCode = input.cAccessCode()

        # Check if the username is long enough
        if re_search(r"^\w{6,20}$", username) is None:
            ui.notification_show("Username must be between 6 and 20 characters")
            return

        # Check if the username already exists
        conn = shared.appDBConn(postgresUser=postgresUser)
        cursor = conn.cursor()
        checkUser = shared.pandasQuery(
            conn,
            'SELECT * FROM "user" WHERE "username" = ?',
            (username,),
        )

        if checkUser.shape[0] > 0:
            ui.notification_show("Username already exists")
            conn.close()
            return

        if shared.personalInfo:
            # Check if the personal information is long enough
            fName = input.cFirstName().strip()
            lName = input.cLastName().strip()
            email = input.cEmail().strip()

            if len(fName) == 0:
                ui.notification_show("First name cannot be empty")
                conn.close()
                return
            if len(lName) == 0:
                ui.notification_show("Last name cannot be empty")
                conn.close()
                return
            if re_search(shared.validEmail, email) is None:
                ui.notification_show("Invalid email address")
                conn.close()
                return

        # Check the password
        pCheck = shared.passCheck(input.cPassword(), input.cPassword2())
        if pCheck:
            ui.notification_show(pCheck)
            conn.close()
            return

        code = shared.accessCodeCheck(conn = conn, accessCode = accessCode, codeType = 0)

        if code is None:
            ui.notification_show("Invalid access code")
            conn.close()
            return

        # Create the user
        hashed = bcrypt.hashpw(input.cPassword().encode("utf-8"), bcrypt.gensalt())

        if shared.personalInfo:
            newuID = shared.executeQuery(
                cursor,
                'INSERT INTO "user" ("username", "password", "adminLevel", "created", "modified", "fName", "lName", "email")'
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    username,
                    hashed.decode("utf-8"),
                    int(code["adminLevel"].iloc[0]),
                    shared.dt(),
                    shared.dt(),
                    fName,
                    lName,
                    email,
                ),
                lastRowId="uID",
            )
        else:
            newuID = shared.executeQuery(
                cursor,
                'INSERT INTO "user" ("username", "password", "adminLevel", "created", "modified")'
                "VALUES(?, ?, ?, ?, ?)",
                (
                    username,
                    hashed.decode("utf-8"),
                    int(code["adminLevel"].iloc[0]),
                    shared.dt(),
                    shared.dt(),
                ),
                lastRowId="uID",
            )

        # Update the access code to show it has been used
        _ = shared.executeQuery(
            cursor,
            'UPDATE "accessCode" SET "uID_user" = ?, "used" = ? WHERE "code" = ?',
            (int(newuID), shared.dt(), accessCode),
        )

        newUser = shared.pandasQuery(
            conn,
            'SELECT * FROM "user" WHERE "uID" = ?',
            (int(newuID),),
        )

        conn.commit()
        conn.close()

        user.set(newUser.to_dict(orient="records")[0])

        # Clear the input fields
        ui.update_text_area("cUsername", value="")
        ui.update_text_area("cPassword", value="")
        ui.update_text_area("cPassword2", value="")
        ui.update_text_area("cAccessCode", value="")

        ui.notification_show("Account created successfully")

    # Reset password
    @reactive.effect
    @reactive.event(input.showReset)
    def _():
        ui.modal_show(ui.modal(login_reset_ui("login_reset")))
        _ = login_reset_server("login_reset", postgresUser=postgresUser)

    return user
