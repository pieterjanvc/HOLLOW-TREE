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
