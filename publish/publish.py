# ---------------------------------------------------------------
# ------------ GENERATE SHINY PUBLISHING DIRECTORY ------------
# ---------------------------------------------------------------

import os
from shutil import copyfile, copytree, rmtree

# If an argument is passed to the script, use it as the publishing directory name
# Otherwise, use "SCUIRREL" as the publishing directory name
if len(os.sys.argv) > 1:
    toGenerate = os.sys.argv[1]
    # IF the argument is not "SCUIRREL" or "ACCORNS", print an error message and exit
    if toGenerate != "SCUIRREL" and toGenerate != "ACCORNS":
        print("Error: The argument must be 'SCUIRREL' or 'ACCORNS'")
        exit()
else:
    toGenerate = "ACCORNS" # Set to "SCUIRREL"  or"ACCORNS" to generate its publishing 

# Get the path to this script as base directory
publishDir = os.path.dirname(os.path.realpath(__file__))
baseFolder = os.path.abspath(os.path.join(publishDir, ".."))
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

# Copy the shared/www directory to the publish directory
copytree(os.path.join(baseFolder, "shared","www"), 
         os.path.join(newFolder, "www"), dirs_exist_ok=True)

# Copy the files in SCUIRREL or ACCORNS www directory to the existing www publish directory
copytree(os.path.join(baseFolder, toGenerate.lower(), "www"), 
         os.path.join(newFolder, "www"), dirs_exist_ok=True)

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

### PART 2: MODIFY PATHS ###

# In the new app.py file, replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
# and replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
with open(os.path.join(newFolder, "app.py"), "r") as f:
    app_py = f.read()
    app_py = app_py.replace(f"import {toGenerate}.{toGenerate.lower()}_shared as {toGenerate.lower()}_shared",
                            f"import {toGenerate.lower()}_shared")
    app_py = app_py.replace("import shared.shared as shared", "import shared")
    app_py = app_py.replace(f"{toGenerate}/www/", "www/")
    app_py = app_py.replace("shared/www/", "www/")

with open(os.path.join(newFolder, "app.py"), "w") as f:
    f.write(app_py)

with open(os.path.join(newFolder, "shared.py"), "r") as f:
    shared_py = f.read()
    shared_py = shared_py.replace("from shared import shared","import shared")
    shared_py = shared_py.replace("shared/shared_config.toml","shared_config.toml")

with open(os.path.join(newFolder, "shared.py"), "w") as f:
    f.write(shared_py)

with open(os.path.join(newFolder, f"{toGenerate.lower()}_shared.py"), "r") as f:
    shared_py = f.read()
    shared_py = shared_py.replace(f"{toGenerate}/{toGenerate.lower()}_config.toml",f"{toGenerate.lower()}_config.toml")

with open(os.path.join(newFolder, f"{toGenerate.lower()}_shared.py"), "w") as f:
    f.write(shared_py)

print(f"Publishing directory generated successfully at {os.path.join(publishDir, toGenerate)}")
