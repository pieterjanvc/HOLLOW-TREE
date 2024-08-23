# Setting up the HOLLOW-TREE project development environment

## Get the code

Start by cloning the
[HOLLOW-TREE repository](https://github.com/pieterjanvc/HOLLOW-TREE) to your local
machine.

It is recommended to use a python virtual environment to manage the dependencies of the
project and ensure consistency across different machines.

## Set up a Virtual Python environment

### Option 1: Using `uv` (recommended)

1. Install uv

See the
[uv installation guide](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)
for help installing uv on your system.

2. Setup the environment

Navigate to the project root folder and run the following command:

```
uv pip sync requirements.txt
```

_This will create a virtual environment and install all packages needed_

NOTE: If you make any changes that require new or updated packages, you need to update
the `requirements.txt` file by running `uv pip compile pyproject.toml`

2. Activate the environment

Run `.venv\Scripts\activate.bat` on Windows or `source .venv/bin/activate` on Linux

_You should see (.venv) appear before the prompt_

### Option 2: Using `venv`

Full tutorial for setting up Shiny within a virtual environment found on
[website](https://shiny.posit.co/py/docs/install-create-run.html#install)

The command below should be run on the CMD on Windows (_not_ PowerShell), or a terminal
on Linux or MacOS.

1. Navigate to the HOLLOW-TREE root folder and run

```
python -m venv .venv
```

_Depending on your PositConnect server, you might need to use a specific python version
in which case you use for example `path/to/python/python -m venv .venv`_

2. Activate the environment

Run `.venv\Scripts\activate.bat` on Windows or `source .venv/bin/activate` on Linux

_You should see (.venv) appear before the prompt_

3. Install any project dependencies

```
py -m pip install -r requirements.txt
```

NOTE: If you make any changes that require new or updated packages, you need to update
the `requirements.txt` file.

## Run a Shiny app locally

Make sure you are in the HOLLOW-TREE root folder with the virtual environment activated
and run the following command:

```
shiny run --reload --launch-browser accorns_app.py
```

or

```
shiny run --reload --launch-browser scuirrel_app.py
```

## Deactivate the virtual environment

When finished you can deactivate the virtual environment by running:

```
deactivate
```

_You should see (.venv) disappear from the prompt_

NOTE: After the initial setup, you only need to activate the environment and run the app

## Developing Shiny apps in VS code

To easily test and debug the apps from within [VS code](https://code.visualstudio.com/)
you can install the
[Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
and the
[Shiny extension](https://marketplace.visualstudio.com/items?itemName=Posit.shiny-python)

Before trying to use the debugger, make sure your virtual environment is activated in
the terminal and you are in the project root folder

You can set the default Python interpreter to be the one from the virtual environment.
In case of errors or not found, set it manually:
`Python: Select interpreter -> Select at workspace level -> Enter interpreter Path -> find .venv\Scripts\python.exe`

### Run / Debug your Shiny apps

1. Open the accorns_app.py file or the scuirrel_app.py file in VS code
2. You will see a 'Run Shiny App' button appear on the top-right of the screen
3. Clicking the button should start the app in an integrated browser. Alternatively,
   choose the dropdown and choose 'Debug Shiny App' to run the in debug mode (it will
   automatically stop at breakpoints)
