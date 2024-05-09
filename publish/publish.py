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

### PART 2: MODIFY PATHS ###

# In the new app.py file, replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
# and replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
with open(os.path.join(newFolder, "app.py"), "r") as f:
    toEdit = f.read()
    toEdit = toEdit.replace(f"import {toGenerate}.{toGenerate.lower()}_shared as {toGenerate.lower()}_shared",
                            f"import {toGenerate.lower()}_shared")
    toEdit = toEdit.replace("import shared.shared as shared", "import shared")
    toEdit = toEdit.replace('"shared",', '')
    toEdit = toEdit.replace(f'"{toGenerate}",', '')

with open(os.path.join(newFolder, "app.py"), "w") as f:
    f.write(toEdit)

with open(os.path.join(newFolder, f"{toGenerate}_shared.py"), "r") as f:
    toEdit = f.read()
    toEdit = toEdit.replace("from shared import shared","import shared")

with open(os.path.join(newFolder, f"{toGenerate}_shared.py"), "w") as f:
    f.write(toEdit)

print(f"Publishing directory generated successfully at {os.path.join(publishDir, toGenerate)}")
