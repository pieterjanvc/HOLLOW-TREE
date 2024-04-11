# About

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
* App wide settings are listed in the [config.toml](./config.toml) file

## Data storage

Data is stored in two separate databases

* The vector database used for RAG is implemented with DuckDB (note that original files uploaded to the app can be stored as well depending on the settings)
* All app data and logs are stored in a custom SQLite database (schema below).
This data is used for app operation, monitoring and research
* If the databases to not exist when the app is run, they will be created.
Note that the admin app needs to be run before the student app the first time.

![App DB Schema](https://drive.usercontent.google.com/download?id=1kOzuVdI-p1K5Ej6EaRh4dJZuxyCATCfT)

## Source code of the apps

The apps are written with the Shiny Express syntax. 

*Note: For scoping reasons, functions and variables that are shared between sessions
are in a separate file so they only have to be loaded once. All code put in the
main app files is run for each new session*

## Admin App ([admin/admin.py](./admin/admin.py))

*Shared variables and functions are sources in from [admin/admin_shared.py](./admin/admin_shared.py)*

* Create / edit topics to be discussed
* Create / edit specific concepts (facts) for each topic to help guide the conversation
* Upload new files to the vector database (RAG)


## Student App ([app.py](./app.py))

*Shared variables and functions are sources in from [app_shared.py](./app_shared.py)*

* Students can select a topic to check their knowledge on
* Interact with the LLM in conversation led by the topic and concepts set by the instructor
* The LLM should adapt the conversation to the student's answers and keep them engaged and on topic

# Set-up and deployment

## Setting up the project in a virtual Python environment on Windows

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

If working in VS Code, the environment can be set to default to the virtual environment for this project without the need for (de)activation. To select an environment open the Command Palette and type “Python: Select Interpreter”

## Hosting the app
<todo>
