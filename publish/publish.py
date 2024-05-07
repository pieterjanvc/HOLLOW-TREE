# ---------------------------------------------------------------
# ------------ GENERATE SHINY PUBLISHING DIRECTORY ------------
# ---------------------------------------------------------------

import os
from shutil import copyfile, copytree, rmtree

toGenerate = "SCUIRREL" # Set to "SCUIRREL"  or"ACCORNS" to generate its publishing directory

### PART 1: Copy the necessary files to the publish directory ###

# Create publish/SCUIRREL or publish/ACCORNS directory if needed otherwise delete all files in the directory and subdirectories
if not os.path.exists(f"publish/{toGenerate}"):
    os.makedirs(f"publish/{toGenerate}")
else:
    rmtree(f"publish/{toGenerate}")
    os.makedirs(f"publish/{toGenerate}")

# Copy the scuirrel_app.py or accorns_app.py file to the publish directory and rename it to app.py
copyfile(f"{toGenerate.lower()}_app.py", f"publish/{toGenerate}/app.py")

# Copy the requirements.txt file to the publish directory
copyfile("requirements.txt", f"publish/{toGenerate}/requirements.txt")

# Copy the shared.py file to the publish directory
copyfile("shared/shared.py", f"publish/{toGenerate}/shared.py")

# Copy the SCUIRREL/scuirrel_shared.py or accorns_shared.py file to the publish directory
copyfile(f"{toGenerate.lower()}/{toGenerate.lower()}_shared.py", f"publish/{toGenerate}/{toGenerate.lower()}_shared.py")

# Copy the shared/www directory to the publish directory
copytree("shared/www", f"publish/{toGenerate}/www", dirs_exist_ok=True)

# Copy the files in SCUIRREL or ACCORNS www directory to the existing www publish directory
copytree(f"{toGenerate.lower()}/www", f"publish/{toGenerate}/www", dirs_exist_ok=True)

# Copy the shared/shared-config.toml file to the publish directory
copyfile("shared/shared_config.toml", f"publish/{toGenerate}/shared_config.toml")

# Add the SCUIRREL/scuirrel_config.toml or SCUIRREL/scuirrel_config.toml file to the publish directory
copyfile(f"{toGenerate.lower()}/{toGenerate.lower()}_config.toml", 
         f"publish/{toGenerate}/{toGenerate.lower()}_config.toml")

### PART 2: MODIFY PATHS ###

# In the new app.py file, replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
# and replace import SCUIRREL.scuirrel_shared as scuirrel_shared with import shared as shared
with open(f"publish/{toGenerate}/app.py", "r") as f:
    app_py = f.read()
    app_py = app_py.replace(f"import {toGenerate}.{toGenerate.lower()}_shared as {toGenerate.lower()}_shared",
                            f"import {toGenerate.lower()}_shared")
    app_py = app_py.replace("import import shared.shared as shared", "import shared")
    app_py = app_py.replace("SCUIRREL/www/", "www/")
    app_py = app_py.replace("shared/www/", "www/")

with open(f"publish/{toGenerate}/app.py", "w") as f:
    f.write(app_py)

with open(f"publish/{toGenerate}/shared.py", "r") as f:
    shared_py = f.read()
    shared_py = shared_py.replace("shared/shared_config.toml","shared_config.toml")

with open(f"publish/{toGenerate}/shared.py", "w") as f:
    f.write(shared_py)

with open(f"publish/{toGenerate}/{toGenerate.lower()}_shared.py", "r") as f:
    shared_py = f.read()
    shared_py = shared_py.replace(f"{toGenerate}/{toGenerate.lower()}_config.toml",f"{toGenerate.lower()}_config.toml")

with open(f"publish/{toGenerate}/{toGenerate.lower()}_shared.py", "w") as f:
    f.write(shared_py)
