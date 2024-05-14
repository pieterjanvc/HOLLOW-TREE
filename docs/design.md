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
