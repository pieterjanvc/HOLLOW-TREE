# ------ Login Module ------
# --------------------------

# -- General
import bcrypt
from re import search as re_search

# -- Shiny
from shiny import Inputs, Outputs, Session, module, reactive, ui
from htmltools import HTML

import shared.shared as shared

# --- UI
@module.ui
def login_ui():
    return ([
        ui.layout_columns(
                ui.card(
                    ui.card_header("Login"),
                    ui.input_text("lUsername", "Username"),
                    ui.input_password("lPassword", "Password"),
                    ui.input_action_button("login", "Login", width="200px"),
                    ui.input_action_link("showReset", "Reset password", width="250px")),
                ui.card(               
                    ui.card_header("Create an account"),              
                    HTML("""<i>NOTE: This application has been built for research purposes 
                        and has not been extensively tested for security. We recommend
                        you create a unique password for this you are not using anywhere else</i>"""),
                    ui.input_text("cUsername", "Username"),
                    ui.input_password("cPassword", "Password"),
                    ui.input_password("cPassword2", "Repeat password"),
                    ui.input_text("cAccessCode", "Access code"),
                    ui.input_action_button("createAccount", "Create", width="200px")),
            ui.panel_conditional("input.showReset > 0",
                    ui.card(
                        ui.card_header("Reset password"),
                        HTML("""<p><i>You will need to request a new access code from your 
                            administrator before resetting your password.</i></p>"""),
                        ui.input_text("rUsername", "Username"),
                        ui.input_password("rPassword", "New password"),
                        ui.input_password("rPassword2", "Repeat new password"),
                        ui.input_text("rAccessCode", "Access code"),
                        ui.input_action_button("reset", "Reset password", width="250px"),
                    )),col_widths=6)
    ])

# --- Server
@module.server
def login_server(input: Inputs, output: Outputs, session: Session, sessionID, minAdminLevel = 0):

    # Default to anonymous
    conn = shared.appDBConn()
    user = shared.pandasQuery(conn,'SELECT * FROM "user" WHERE "uID" = 1')
    conn.close()
    user = reactive.value(user.to_dict(orient="records")[0]) 
    
    # Login
    @reactive.effect
    @reactive.event(input.login)
    def _():
        username = input.lUsername()
        password = input.lPassword().encode("utf-8")
        conn = shared.appDBConn()
        checkUser = shared.pandasQuery(
            conn,
            'SELECT * FROM "user" WHERE "username" = ? AND "username" != "anonymous"',
            (username,),
        )

        #Somehow the manually added test admin has a password that is not a byte string
        passw = checkUser.password.iloc[0]
        passw = str.encode(passw) if not isinstance(passw, bytes) else passw
        
        if checkUser.shape[0] == 1:
            if bcrypt.checkpw(password, passw):
                if int(checkUser.adminLevel.iloc[0]) < minAdminLevel:
                    ui.notification_show("You do not have the required permissions to access this application")
                    conn.close()
                    return
                
                ui.notification_show("Logged in successfully")
                cursor = conn.cursor()
                # For now we only have anonymous users (appID 0 -> SCUIRREL)
                _ = shared.executeQuery(
                    cursor,
                    'UPDATE "session" SET "uID" = ? WHERE sID = ?',
                    (int(checkUser.uID.iloc[0]), sessionID)
                )
                conn.commit()
            else:
                ui.notification_show("Incorrect password")
                conn.close()
                return
        else:
            ui.notification_show("Invalid username")
            conn.close()
            return

        conn.close()
        # Clear the input fields
        ui.update_text_area("lUsername", value="")
        ui.update_text_area("lPassword", value="")

        user.set(checkUser.to_dict(orient="records")[0])

    # Create an account
    @reactive.effect
    @reactive.event(input.createAccount)
    def _():
        username = input.cUsername()
        accessCode = input.cAccessCode()

        # Check if the password is strong enough
        if re_search(r"^\w{6,20}$", username) is None:
            ui.notification_show("Username must be between 6 and 20 characters")
            return
        
        # Check if the username already exists
        conn = shared.appDBConn()
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

        # Check the password
        pCheck = shared.passCheck(input.cPassword(), input.cPassword2())
        if pCheck:
            ui.notification_show(pCheck)
            conn.close()
            return    

        code = shared.accessCodeCheck(conn, accessCode)

        if code is None:
            ui.notification_show("Invalid access code")
            conn.close()
            return    

        # Create the user
        hashed = bcrypt.hashpw(input.cPassword().encode("utf-8"), bcrypt.gensalt())
        newuID = shared.executeQuery(
            cursor,
            'INSERT INTO "user" ("username", "password", "adminLevel", "created", "modified")'
            "VALUES(?, ?, ?, ?, ?)",
            (username, hashed, int(code["adminLevel"].iloc[0]), shared.dt(), shared.dt()),
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
    @reactive.event(input.reset)
    def _():
        username = input.rUsername()
        accessCode = input.rAccessCode()

        # Check if the username already exists
        conn = shared.appDBConn()
        cursor = conn.cursor()
        user = shared.pandasQuery(
            conn,
            'SELECT * FROM "user" WHERE "username" = ?',
            (username,),
        )    

        if user.shape[0] == 0:
            ui.notification_show("This username does not exist")
            conn.close()
            return
        
        uID = int(user["uID"].iloc[0])

        # Check the password
        pCheck = shared.passCheck(input.rPassword(), input.rPassword2())
        if pCheck:
            ui.notification_show(pCheck)
            return
        
        # Check the access code
        code = shared.accessCodeCheck(conn, accessCode)

        if code is None:
            ui.notification_show("Invalid access code")
            conn.close()
            return
        
        # Update the password
        hashed = bcrypt.hashpw(input.rPassword().encode("utf-8"), bcrypt.gensalt())
        _ = shared.executeQuery(
            cursor,
            'UPDATE "user" SET "password" = ?, "modified" = ? WHERE "uID" = ?',
            (hashed, shared.dt(), uID),
        )

        # Update the access code to show it has been used
        _ = shared.executeQuery(
            cursor,
            'UPDATE "accessCode" SET "uID_user" = ?, "used" = ? WHERE "code" = ?',
            (uID, shared.dt(), accessCode),
        )
        conn.commit()
        conn.close()

        # Clear the input fields
        ui.update_text_area("rUsername", value="")
        ui.update_text_area("rPassword", value="")
        ui.update_text_area("rPassword2", value="")
        ui.update_text_area("rAccessCode", value="")
        
        ui.notification_show("Password reset successfully, please login again")

    return user
