# Setting up the project in a virtual Python environment on Windows
Tutorial for setting up Shiny within a virtual enviroment found on 
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

To run Shiny run
```
shiny run --reload --launch-browser app.py
```
*Note: Using the Run Python File button in VS code to start the app will likely cause a weird error*

To deactivate the virtual environment run
```
deactivate
```
*You should see (.venv) disappear from the prompt*

If workin in VS Code, the enviroment can be set to default to the virtual environment for this project without the need for (de)activation. To select an environment open the Command Palette and type “Python: Select Interpreter”
