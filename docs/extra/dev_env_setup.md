# Setting up the HOLLOW-TREE project development environment

## Get the code

Start by cloning the
[HOLLOW-TREE repository](https://github.com/pieterjanvc/HOLLOW-TREE) to your local
machine.

It is recommended to use a python virtual environment to manage the dependencies of the
project and ensure consistency across different machines.

## Preparing

This project requires the use of [uv](https://github.com/astral-sh/uv) package manager for Python. See the
[uv installation guide](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)
for help installing uv on your system.

## Run a Shiny app locally

Make sure you are in the HOLLOW-TREE root folder with the virtual environment activated
and run the following command:

```
uv run shiny run --reload --launch-browser accorns_app.py
```

or

```
uv run shiny run --reload --launch-browser scuirrel_app.py
```

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

## Update dependencies

If you make any changes that require new or updated packages do the following:

- Update the dependencies in the [pyproject.toml](../../pyproject.toml) file
- Navigate to the project root folder
- Run `uv pip compile pyproject.toml > requirements.txt` to update the
  [requirements.txt](../../requirements.txt) file

## Testing apps and generating tutorials

See [Testing apps & Generating tutorials](testing.md)
