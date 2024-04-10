# About

This applications aims to provide students with an LLM-based knowledge check on specific topics relevant to their coursework. Admins can set the topic and add sub-concepts to guide the conversation. By uplaoding specific and relevant files to a vector database, the app will use Retrieval Augmented Generation (RAG) to ensure the quality and accuracy of the LLM responses is high and on topic.

## Student facing app (app.py, app_shared.py)

* Select a topic to check their knowlege on relevant to the coursework
* Interact with the LLM in conversation led by the topic and consepts set by the instuctor
* The LLM should adapt the conversation to the student's anwers and keep them engaged and on topic

## Admin facing app (admin/admin.py, admin/admin_shared.py)

* Create / edit topics to be discussed
* Create / edit specific concepts for each topic to help guide the converstaion
* Upload new files to the vector database (RAG)

# ToDo

* Check with IRB to see what we can collect / study
* Implement Multiple-choice generator: Admin can generate multiple choice questiones based on a topic and concepts, then edit (track this) if needed and validate. This will be added to the DB and students can test themselves after finishing the conversation with the bot. 
* Flagging incorrect / weird   / bot responses for easier analysis

# App set-up and deployment

## Setting up the project in a virtual Python environment on Windows

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
