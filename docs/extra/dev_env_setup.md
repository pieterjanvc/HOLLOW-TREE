# Setting up the HOLLOW-TREE project development environment

## Get the code

Start by cloning the
[HOLLOW-TREE repository](https://github.com/pieterjanvc/HOLLOW-TREE) to your local
machine.

It is recommended to use a python virtual environment to manage the dependencies of the
project and ensure consistency across different machines.

## Set up a Virtual Python environment

1. Install uv

See the
[uv installation guide](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)
for help installing uv on your system.

2. Setup the environment

Navigate to the project root folder and run the following command:

```
uv sync --locked
```

_This will create a virtual environment and install all packages needed_

- You can add `--no-dev` to the command above to only install the packages needed to run

2. Activate the environment

Run `.venv\Scripts\activate.bat` on Windows or `source .venv/bin/activate` on Linux

_You should see (.venv) appear before the prompt_

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

## Updating dependencies

To install or update a package, you can use the following command:

```
uv add <package-name>
```
- Example `uv add ruff` or `uv add ruff==0.5.0` for specific version
- Add --dev to install as a development dependency

This will automatically update the [pyproject.toml](../../pyproject.toml) file and the
[uv.lock](../../uv.lock) file

Removing a package is done with `uv remove <package-name>`

## Testing apps and generating tutorials

See [Testing apps & Generating tutorials](testing.md)
