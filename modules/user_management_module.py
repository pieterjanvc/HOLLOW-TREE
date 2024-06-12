# ------ User Management Module ------
# ------------------------------------
# This module is used to generate access codes for new users or to update passwords for existing users.

from shiny import Inputs, Outputs, Session, module, reactive, render, ui, req
import pandas as pd
import string
import secrets
from io import BytesIO

import shared.shared as shared

#  ---- FUNCTIONS ----

# Function to generate a unique hash
def generate_hash():
    alphanumeric_characters = string.ascii_letters + string.digits
    hash_parts = []
    for _ in range(3):
        hash_part = ''.join(secrets.choice(alphanumeric_characters) for _ in range(3))
        hash_parts.append(hash_part)
    return '-'.join(hash_parts)

# Function to generate a list of unique hash values
def generate_hash_list(n = 1):
    hash_values = []
    for _ in range(n):
        hash_value = generate_hash()
        hash_values.append(hash_value)
    
    # CHeck if all the hash values are unique otherwise generate new hash values
    while len(hash_values) != len(set(hash_values)):
        # Only generate the number of hash values that are not unique
        hash_values = list(set(hash_values)) + generate_hash_list(n - len(set(hash_values)))            

    return hash_values

# Function to generate access codes
def generate_access_codes(n, uID, adminLevel):
    # Check if n and unID are set
    if not n:
        raise ValueError("Please provide the number of access codes to generate")
    if not uID:
        raise ValueError("Please provide the uID of the user generating the access codes")

    codes = []
    conn = shared.appDBConn()
    cursor = conn.cursor()
    x = n
    while len(codes) < n:
        codes = codes + (generate_hash_list(x))
        # Check if the accessCode does not exist in the database
        cursor.execute("SELECT code FROM accessCode WHERE code IN ({})".format(','.join(['?']*len(codes))), codes)
        existing_codes = cursor.fetchall()
        
        if existing_codes:
            # remove the existing codes from the list
            codes = [code for code in codes if code not in existing_codes[0]]
            x = n - len(codes)
    
    # Insert the new codes into the database
    _ = shared.executeQuery(cursor, 'INSERT INTO "accessCode"("code", "uID_creator", "adminLevel", "created") VALUES(?, ?, ?, ?)',
                            [(code, uID, adminLevel, shared.dt()) for code in codes])
    conn.commit()
    conn.close()

    return codes

# ---- UI ----

@module.ui
def user_management_ui():
    return ([
            # Generate access codes to create new users or update passwords
            ui.card(
                ui.card_header("Generate access codes"),
                ui.input_numeric("numCodes", "Number of codes to generate", value=1, min=1, max=500),
                ui.input_select("role", "Role", choices={0: "User", 1: "Instructor", 2: "Admin"}),
                ui.input_action_button("generateCodes", "Generate codes", width="180px"),
                
                ui.output_data_frame("codesTable"),
                ui.panel_conditional("input.generateCodes > 0",
                    ui.download_link("downloadCodes", "Download as CSV")
                ))
    ])

# ---- SERVER ----

@module.server
def user_management_server(input: Inputs, output: Outputs, session: Session, user):

    @reactive.calc
    @reactive.event(input.generateCodes)
    def accessCodes():
        req(user.get()["uID"] != 1)
        newCodes = generate_access_codes(n = input.numCodes(), uID= user.get()["uID"], adminLevel=int(input.role()))
        role = ["user", "instructor", "admin"][int(input.role())]
        # create a pandas dataframe form the dictionary
        return pd.DataFrame({"accessCode": newCodes, "role": role})
    
    @render.data_frame
    def codesTable():
        return accessCodes()
    
    @render.download(filename = "hollow-tree_accessCodes.csv")
    async def downloadCodes():
        with BytesIO() as buf:
            accessCodes().to_csv(buf, index=False)
            yield buf.getvalue()

    return
