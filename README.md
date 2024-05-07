# SCUIRREL: Science Concept Understanding with Interactive Research RAG Educational LLM

This applications aims to provide students with an LLM-based knowledge check on specific topics relevant to their coursework. Admins can set the topic and add sub-concepts to guide the conversation. By uploading specific and relevant files to a vector database, the app will use Retrieval Augmented Generation (RAG) to ensure the quality and accuracy of the LLM responses is high and on topic.

# Apps and Data

## Software and Libraries

The apps are written in Python and use the following important libraries:

* The [Llamaindex](https://www.llamaindex.ai/) framework is a wrapper for working with 
various LLMs (e.g. ChatGPT) and implement Retrieval Augmented Generation for increasing
accuracy
* The [Shiny framework](https://shiny.posit.co/py/) is used for generating the 
apps' UI and Server components
* For a list of all dependencies, see the [requirements.txt](./requirements.txt) file

## The LLM
The app is currently configured to run with OpenAI's GPT models. This requires
your own active API key. If your are part of an organization, you will also need the 
organization ID. Make sure the keys are available to Python as environment
variables with the following names:

* OPENAI_API_KEY
* OPENAI_ORGANIZATION

They will be accessed in the code like this
```
os.environ["OPENAI_ORGANIZATION"]
os.environ.get("OPENAI_ORGANIZATION")
```
*You can read this [online guide](https://chlee.co/how-to-setup-environment-variables-for-windows-mac-and-linux/) 
for more info on how to set these up*

## Data storage

Data is stored in two separate databases

* The vector database used for RAG is implemented with DuckDB (note that original files uploaded to the app can be stored as well depending on the settings)
* All app data and logs are stored in a custom app database (schema below).
This data is used for app operation, monitoring and research
* IMPORTANT: Edit the config.toml for SCUIRREL and ACCORNS before running the apps

### Local app database (SQLite)

* This is the default and useful during app development or testing, but would likely not scale well
once many users need concurrent DB access. 
* Given this DB is shared between SCUIRREL and ACCORNS, you need to configure
the Shiny server or Posit connect to allow file access outside the app directory
* If the databases do not exist when the app is run, they will be created.
Note that the admin app needs to be run before the student app the first time.

### Remote app database (PostgreSQL)

This is the preferred option when the apps are deployed for production. 
However, it requires an additional Postgres server to be hosted somewhere.
Once the server has been setup and a database created, you can use the [createAppDB.sql](ACCORNS/appDB/createAppDB.sql) 
file (used for SQLite) with the following small modification:

Replace all `INTEGER PRIMARY KEY AUTOINCREMENT` with `SERIAL PRIMARY KEY`

Now this SQL can be used to initialise the PostgreSQL app DB.
Make sure to edit the 


![App DB Schema](https://drive.usercontent.google.com/download?id=1kOzuVdI-p1K5Ej6EaRh4dJZuxyCATCfT)

## Source code of the apps

The apps are written with the Shiny Express syntax. 

*Note: For scoping reasons, functions and variables that are shared between sessions
are in a separate file so they only have to be loaded once. All code put in the
main app files is run for each new session*

## SCUIRREL ([SCUIRREL/app.py](SCUIRREL/app.py))

SCUIRREL or Science Concept Understanding with Interactive Research RAG Educational LLM 
is the main application. In this app, users will interact  with the LLM exploring the 
topics and concepts setup in ACCORNS (admin app, see below)

Details can be found in the [SCUIRREL README](SCUIRREL/README.md)

## ACCORNS: Admin App ([ACCORNS/app.py](ACCORNS/app.py))

ACCORNS or Admin Control Center Overseeing RAG Needed for SCUIRREL, is a secondary
applications where instructors can set-up, manage and monitor SCUIRREL

Details can be found in the [ACCORNS README](ACCORNS/README.md)

# Set-up and deployment

## Setting up the project in a virtual Python environment 

### Windows

Tutorial for setting up Shiny within a virtual environment found on 
[website](https://shiny.posit.co/py/docs/install-create-run.html#install)

The command below should be run on the CMD on Windows (*not* PowerShell)

Move to the app root folder and run
```
python -m venv .venv
.venv\Scripts\activate.bat
```
*You should see (.venv) appear before the prompt*

To install any project dependencies run
```
py -m pip install -r requirements.txt
```

To run Shiny fir navigate to the SCUIRREL or ACCORNS folder (otherwise PATH errors) then run
```
shiny run --reload --launch-browser app.py
```
*Note: See below on how to run / debug Shiny from within VS code*

To deactivate the virtual environment run
```
deactivate
```
*You should see (.venv) disappear from the prompt*

## Working with Shiny apps in VS code

To easily run / debug the apps from within VS code and make use of the integrated 
[Shiny extensenion](https://marketplace.visualstudio.com/items?itemName=Posit.shiny-python) 
do the following:

### Create workspaces and add folders
1) Create a new workspace (save to the root project folder)
2) Add the following folders (File-> Add folder to workspace):
    * SCUIRREL (Main project folder)
    * SCUIRREL\SCUIRREL (Subfolder)
    * SCUIRREL\ACCORNS  (Subfolder)
This is needed because using the sub-folders it will change the working directory when running the Shiny apps
from within VS code
3) Install the Python and Shiny extensions
4) Set the default Python interpreter to be the one from the virtual environment.
In case of errors or not found, set it manually: 
`Python: Select interpreter -> Select at workspace level -> Enter interpreter Path -> find .venv\Scripts\python.exe`

### Run / Debug your Shiny apps

1) Open the app.py file in the SCUIRREL\SCUIRREL or SCUIRREL\ACCORNS folder in your environment
(Do *not* open it via the main SCUIRREL folder or the working directory will be incorrect)
2) You will see a 'Run Shiny App' button appear on the top-right 
3) Clicking the button should start the app in an integrated browser. 
Alternatively, choose the dropdown and choose 'Debug Shiny App' to run in debug mode

## Hosting the apps
*add details here ...*
