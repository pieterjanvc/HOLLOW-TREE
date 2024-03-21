# TUTORIAL
# https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb

import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic

# DATA
dataPath = 'data/test/' 

# # Example data from tutorial
# if not os.path.exists('data/paul_graham'):
#     os.makedirs('data/paul_graham')
#     import requests
#     url = 'https://raw.githubusercontent.com/run-llama/llama_index/main/docs/examples/data/paul_graham/paul_graham_essay.txt'
#     r = requests.get(url)
#     open('data/paul_graham/paul_graham_essay.txt', "wb").write(r.content)

# Get the OpenAI API key and organistation
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.environ.get("OPENAI_ORGANIZATION")

# Use OpenAI LLM 
llm = OpenAI(model="gpt-3.5-turbo-0125") # use gpt-3.5-turbo-0125	or gpt-4

if not os.path.exists(dataPath + "default__vector_store.json"):
    # Build the vector store    
    data = SimpleDirectoryReader(input_dir= dataPath).load_data()
    index = VectorStoreIndex.from_documents(data)
    index.storage_context.persist(persist_dir = dataPath)
else:
    # Load the index from storage
    storage_context = StorageContext.from_defaults(persist_dir= dataPath)
    index = load_index_from_storage(storage_context)

chat_engine = index.as_chat_engine(chat_mode="best", llm=llm, verbose=True)

response = chat_engine.chat(
    "What is the difference between translation and transcription"
)
