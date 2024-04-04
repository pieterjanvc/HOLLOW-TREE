# Installing

Tutorial for setting up Shiny in VS code with vitual enviroment found on 
[website](https://shiny.posit.co/py/docs/install-create-run.html#install)

To activate the environment use the CMD on Windows (not PowerShell)

Move to the app root folder and run
```
.\venv\Scripts\activate.bat
```
*You should see (.venv) appear before the prompt*

To install any dependencies run
```
py -m pip install -r requirements.txt
```

To run Shiny run
```
shiny run --reload --launch-browser app.py
```

To deactivate the virtual environment simply run
```
deactivate
```
*You should see (.venv) disappear from the prompt*
