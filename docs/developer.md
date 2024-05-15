# Design and Implementation

## Software and Libraries

The apps are written in Python and use the following important libraries:

- The [Llamaindex](https://www.llamaindex.ai/) framework is a wrapper for working with
  various LLMs (e.g. ChatGPT) and implement Retrieval Augmented Generation for
  increasing accuracy
- The [Shiny framework](https://shiny.posit.co/py/) is used for generating the apps' UI
  and Server components
- For a list of all dependencies, see the [requirements.txt](./requirements.txt) file

## Large Language Models (LLM)

The app is currently configured to run with OpenAI's GPT models. This requires your own
active API key. If your are part of an organization, you will also need the organization
ID. Make sure the keys are available to Python as environment variables with the
following names:

- OPENAI_API_KEY
- OPENAI_ORGANIZATION

They will be accessed in the code like this

```
os.environ["OPENAI_ORGANIZATION"]
os.environ.get("OPENAI_ORGANIZATION")
```

_You can read this
[online guide](https://chlee.co/how-to-setup-environment-variables-for-windows-mac-and-linux/)
for more info on how to set these up_


## Source code of the apps

The apps are written with the Shiny Express syntax.

_Note: For scoping reasons, functions and variables that are shared between sessions are
in a separate file so they only have to be loaded once. All code put in the main app
files is run for each new session_

## Files and Folders SCUIRREL

* [app.py](app.py): Main app file
* [app_shared.py](app_shared.py): Shared variables and functions across different session 
* [config.toml](config.toml): App wide settings

## Installation and Setup

* See the main [README](../README.md) file for details on setting up the environment
* Make sure to set all paths and specific ACCORNS settings in the [config.toml](config.toml) file

## Files and Folders ACCORNS

* [app.py](app.py): Main app file
* [app_shared.py](app_shared.py): Shared variables and functions across different session 
* [config.toml](config.toml): App wide settings
* [appDB/createDB.sql](appDB/createDB.sql): SQL file used to generate the app database
* [www/](www/): Contains files needed to render the app properly 
(Don't add sensitive data as this folder is accessible by the client!)

# Local app development

## Setting up the project in a virtual Python environment

### Windows

Tutorial for setting up Shiny within a virtual environment found on
[website](https://shiny.posit.co/py/docs/install-create-run.html#install)

The command below should be run on the CMD on Windows (_not_ PowerShell)

Move to the app root folder and run

```
python -m venv .venv
.venv\Scripts\activate.bat
```

_You should see (.venv) appear before the prompt_

To install any project dependencies run

```
py -m pip install -r requirements.txt
```

To run Shiny fir navigate to the SCUIRREL or ACCORNS folder (otherwise PATH errors) then
run

```
shiny run --reload --launch-browser app.py
```

_Note: See below on how to run / debug Shiny from within VS code_

To deactivate the virtual environment run

```
deactivate
```

_You should see (.venv) disappear from the prompt_

## Working with Shiny apps in VS code

To easily run / debug the apps from within VS code and make use of the integrated
[Shiny extensenion](https://marketplace.visualstudio.com/items?itemName=Posit.shiny-python)
do the following:

### Create workspaces and add folders

1. Create a new workspace (save to the root project folder)
2. Add the following folders (File-> Add folder to workspace): _ SCUIRREL (Main project
   folder) _ SCUIRREL\SCUIRREL (Subfolder) \* SCUIRREL\ACCORNS (Subfolder) This is
   needed because using the sub-folders it will change the working directory when
   running the Shiny apps from within VS code
3. Install the Python and Shiny extensions
4. Set the default Python interpreter to be the one from the virtual environment. In
   case of errors or not found, set it manually:
   `Python: Select interpreter -> Select at workspace level -> Enter interpreter Path -> find .venv\Scripts\python.exe`

### Run / Debug your Shiny apps

1. Open the app.py file in the SCUIRREL\SCUIRREL or SCUIRREL\ACCORNS folder in your
   environment (Do _not_ open it via the main SCUIRREL folder or the working directory
   will be incorrect)
2. You will see a 'Run Shiny App' button appear on the top-right
3. Clicking the button should start the app in an integrated browser. Alternatively,
   choose the dropdown and choose 'Debug Shiny App' to run in debug mode
