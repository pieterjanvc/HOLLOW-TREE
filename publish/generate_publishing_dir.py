# ---------------------------------------------------------------
# ------------ GENERATE SHINY PUBLISHING DIRECTORY ------------
# ---------------------------------------------------------------

import os
from shutil import copyfile, copytree, rmtree
import toml
import argparse

# Get the path to this script as base directory
publishDir = os.path.dirname(os.path.realpath(__file__))
baseFolder = os.path.abspath(os.path.join(publishDir, ".."))

# Parse arguments
# Get the shared_config settings TOML file
with open(os.path.join(os.path.join(baseFolder, "shared"), "shared_config.toml"), 'r') as f:
    config = toml.load(f)

parser = argparse.ArgumentParser(description='Command line arguments for the publishing directory script')
# App to generate
parser.add_argument('--app', default = "", type=str, help='App to generate (SCUIRREL or ACCORNS)')

# Setitngs
parser.add_argument('--remoteAppDB', action='store_true', help='Use postgres databases for the app')
parser.add_argument('--addDemo', action='store_true', help='Add the demo to the app')
parser.add_argument('--personalInfo', action='store_true', help='Require personal information when signing up')

parser.add_argument('--sqliteDB', default = config['localStorage']['sqliteDB'], type=str, help='Path to a local SQLite database')
parser.add_argument('--duckDB', default = config['localStorage']['duckDB'], type=str, help='Path to a local duckDB database')
parser.add_argument('--pHost', default = config['postgres']['host'], type=str, help='Postgres host for databases')
parser.add_argument('--pPort', default = config['postgres']['port'], type=int, help='Postgres port for databases')
parser.add_argument('--gptModel', default = config['LLM']['gptModel'], type=str, help='GPT model to use')
parser.add_argument('--validEmail', default = config['auth']['validEmail'], type=str, help='Which email addresses can register')

args = parser.parse_args()

# Check which apps to generate
apps = ["ACCORNS", "SCUIRREL"]
if args.app not in apps and args.app != "":
    print("Error: The --app argument must be 'SCUIRREL' or 'ACCORNS' or not set for both")
    exit()
elif args.app != "":
    apps = [args.app]

for toGenerate in apps:

    newFolder = os.path.join(publishDir, toGenerate)

    ### PART 1: Copy the necessary files to the publish directory ###

    # Create publishDir/SCUIRREL or publishDir/ACCORNS directory if needed otherwise delete all files in the directory and subdirectories
    if not os.path.exists(newFolder):
        os.makedirs(newFolder)
    else:
        rmtree(newFolder)
        os.makedirs(newFolder)

    # Copy the scuirrel_app.py or accorns_app.py file to the publish directory and rename it to app.py
    copyfile(os.path.join(baseFolder,f"{toGenerate.lower()}_app.py"), 
            os.path.join(newFolder, "app.py"))

    # Copy the requirements.txt file to the publish directory
    copyfile(os.path.join(baseFolder, "requirements.txt"), 
            os.path.join(newFolder, "requirements.txt"))

    # Copy the shared.py file to the publish directory
    copyfile(os.path.join(baseFolder, "shared","shared.py"), 
            os.path.join(newFolder, "shared.py"))

    # Copy the SCUIRREL/scuirrel_shared.py or accorns_shared.py file to the publish directory
    copyfile(os.path.join(baseFolder, toGenerate.lower(),f"{toGenerate.lower()}_shared.py"), 
            os.path.join(newFolder, f"{toGenerate.lower()}_shared.py"))

    # Copy the shared css and js directory to the publish directory
    copytree(os.path.join(baseFolder, "shared","shared_css"), 
            os.path.join(newFolder, "shared_css"), dirs_exist_ok=True)
    copytree(os.path.join(baseFolder, "shared","shared_js"), 
            os.path.join(newFolder, "shared_js"), dirs_exist_ok=True)

    # Copy the files in SCUIRREL or ACCORNS css and js directory to the publish directory
    copytree(os.path.join(baseFolder, toGenerate,f"{toGenerate.lower()}_css"), 
            os.path.join(newFolder, f"{toGenerate.lower()}_css"), dirs_exist_ok=True)
    copytree(os.path.join(baseFolder, toGenerate,f"{toGenerate.lower()}_js"), 
            os.path.join(newFolder, f"{toGenerate.lower()}_js"), dirs_exist_ok=True)

    # Copy the shared/shared-config.toml file to the publish directory
    copyfile(os.path.join(baseFolder,"shared","shared_config.toml"), 
            os.path.join(newFolder, "shared_config.toml"))

    # Add the SCUIRREL/scuirrel_config.toml or SCUIRREL/scuirrel_config.toml file to the publish directory
    copyfile(os.path.join(baseFolder, toGenerate.lower(), f"{toGenerate.lower()}_config.toml"), 
            os.path.join(newFolder, f"{toGenerate.lower()}_config.toml"))

    # In case of ACCORNS, create the appDB directory in the publish directory and copy over all .sql files
    if toGenerate == "ACCORNS":
        os.makedirs(os.path.join(newFolder, "appDB"))
        for file in os.listdir(os.path.join(baseFolder, "ACCORNS","appDB")):
            if file.endswith(".sql"):
                copyfile(os.path.join(baseFolder, "ACCORNS","appDB", file),
                        os.path.join(newFolder, "appDB", file))

    # Create a new modules directory in the publish directory
    os.makedirs(os.path.join(newFolder, "modules"))

    # Copy relevant modules depending on the app
    if toGenerate == "SCUIRREL":
        modules = ["login_module.py", "feedback_module.py", "chat_module.py", "quiz_module.py", 
                   "login_reset_module.py", "group_join_module.py"]
        for module in modules:
            copyfile(os.path.join(baseFolder, "modules", module), 
                    os.path.join(newFolder, "modules", module))
        
    else:
        modules = ["login_module.py", "feedback_module.py", "vectorDB_management_module.py", 
                "topics_module.py", "quiz_generation_module.py", "user_management_module.py",
                "login_reset_module.py","groups_module.py", "group_join_module.py"]
        for module in modules:
            copyfile(os.path.join(baseFolder, "modules", module), 
                    os.path.join(newFolder, "modules", module))

    ### PART 2: MODIFY PATHS ###

    # In the new app.py file, replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
    # and replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
    with open(os.path.join(newFolder, "app.py"), "r") as f:
        toEdit = f.read()
        toEdit = toEdit.replace(f"import {toGenerate}.{toGenerate.lower()}_shared as {toGenerate.lower()}_shared",
                                f"import {toGenerate.lower()}_shared")
        toEdit = toEdit.replace("import shared.shared as shared", "import shared")
        toEdit = toEdit.replace('curDir, "shared",', 'curDir, ')
        toEdit = toEdit.replace(f'curDir, "{toGenerate}",', 'curDir, ')

    with open(os.path.join(newFolder, "app.py"), "w") as f:
        f.write(toEdit)

    # Fix shared imports for relevant files
   
    # get all files in the new modules directory
    files = os.listdir(os.path.join(newFolder, "modules"))
    files.append(os.path.join(newFolder, "app.py"))

    for file in files:
        
        file = os.path.join(newFolder, "modules", file)
        
        # If the file does not exist, skip it
        if not os.path.exists(file):
            continue

        with open(file, "r") as f:
            toEdit = f.read()
            toEdit = toEdit.replace("shared.shared", "shared")
            toEdit = toEdit.replace("ACCORNS.accorns_shared","accorns_shared")
            toEdit = toEdit.replace("SCUIRREL.scuirrel_shared","scuirrel_shared")

        with open(os.path.join(newFolder, "modules", file), "w") as f:
            f.write(toEdit)

    # Fix the shared file
    with open(os.path.join(newFolder, f"{toGenerate}_shared.py"), "r") as f:
        toEdit = f.read()
        toEdit = toEdit.replace("from shared import shared","import shared")    

    with open(os.path.join(newFolder, f"{toGenerate}_shared.py"), "w") as f:
        f.write(toEdit)

    ### PART 3: MODIFY SETTINGS ###

    #p = "C:/Users/pj/Documents/LocalProjects/HOLLOW-TREE/publish/ACCORNS/shared_config.toml"
    
    # Modify values in the config
    config['general']['remoteAppDB'] = args.remoteAppDB
    config['general']['addDemo'] = args.addDemo
    config['auth']['personalInfo'] = args.personalInfo
    config['localStorage']['sqliteDB'] = args.sqliteDB
    config['localStorage']['duckDB'] = args.duckDB
    config['postgres']['host'] = args.pHost
    config['postgres']['port'] = args.pPort
    config['LLM']['gptModel'] = args.gptModel
    config['auth']['validEmail'] = args.validEmail

    
    # Write the modified config back to the file
    with open(os.path.join(newFolder, "shared_config.toml"), 'w') as f:
        toml.dump(config, f)

    print(f"Publishing {toGenerate} directory generated successfully at {os.path.join(publishDir, toGenerate)}")