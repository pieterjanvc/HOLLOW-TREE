#------ BOT LOGIC
# TUTORIAL
# https://github.com/run-llama/llama_index/blob/main/docs/examples/chat_engine/chat_engine_best.ipynb

import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI

# DATA
dataPath = 'data/test/' 


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

# Prompt engineering
# https://docs.llamaindex.ai/en/stable/examples/customization/prompts/chat_prompts/

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core import ChatPromptTemplate

qa_prompt_str = (
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context information and not prior knowledge, "
    "answer the question: {query_str}\n"
)

refine_prompt_str = (
    "We have the opportunity to refine the original answer "
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "Given the new context, refine the original answer to better "
    "answer the question: {query_str}. "
    "If the context isn't useful, output the original answer again.\n"
    "Original Answer: {existing_answer}"
)

chat_text_qa_msgs = [
    ChatMessage(
        role=MessageRole.SYSTEM,
        content=(
            """
            Your goal is to check wether the user (a student) has an understanding of the following topic: 
            'The central dogma of molecular biology'
            ----
            These are the sub-concepts that the user should understand:
            * DNA is made up of 4 bases that encode all information needed for life
            * A protein is encoded in the DNA as a seqeunce of bases
            * To create a protein, you first have to transcribe the DNA into RNA
            * RNA is similar to DNA but instead of ACTG it has ACUG and is single stranded
            * RNA is processed by removing introns, keeping only exons
            * RNA is translated into protein. 3 RNA bases form a codon, and each codon represents an amino acid,
            or the start / stop of the seqeunce
            * Based on RNA codons, amino acids are chained together into a single protrein strand
            * Finally, the protein will fold into a 3D shape to become functional, with optional post-translational processing
            ----
            Remember that you are not lecturing, i.e. giving definitions or giving away all the concepts.
            Rather, you will ask a series of questions (or generate a multiple choice question if it fits) and look
            at the answers to refine your next question according to the current understanding of the user.
            Try to make the user think and reason critically, but do help out if they get stuck. 
            You will adapt the conversation until you feel all sub-concepts are understood.
            Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
            message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!
            """
        ),
    ),
    ChatMessage(role=MessageRole.USER, content=qa_prompt_str),
]
text_qa_template = ChatPromptTemplate(chat_text_qa_msgs)

# Refine Prompt
chat_refine_msgs = [
    ChatMessage(
        role=MessageRole.SYSTEM,
        content=(
            """
            Remember that you are not lecturing, i.e. giving definitions or giving away all the concepts.
            Rather, you will ask a series of questions (or generate a multiple choice question if it fits) and look
            at the answers to refine your next question according to the current understanding of the user.
            Try to make the user think and reason critically, but do help out if they get stuck. 
            You will adapt the conversation until you feel all sub-concepts are understood.
            Do not go beyond what is expected, as this is not your aim. Make sure to always check any user
            message for mistakes, like the use of incorrect terminology and correct if needed, this is very important!
            Finally, your output will be rendered as HTML, so format accordinly 
            (e.g. make a list of multiple choice questions using <ul> and <li> tags).
            """
        ),
    ),
    ChatMessage(role=MessageRole.USER, content=refine_prompt_str),
]
refine_template = ChatPromptTemplate(chat_refine_msgs)

chat_engine = index.as_query_engine(
            text_qa_template=text_qa_template,
            refine_template=refine_template,
            llm=llm,
            streaming = True
        )

# ------- SHINY APP
from shiny import reactive
from shiny.express import input, render, ui
from htmltools import HTML, div

userLog = reactive.value(f"""<b>--- BOT:</b><br>Hello, I'm here to help you get a basic understanding of the 
                     'central dogma of molecular biology'. Have you heard about this before?""")

botLog = reactive.value(f"""---- PREVIOUS CONVERSATION ----\n--- YOU:\nHello, I'm here to help 
                        you get a basic understanding of the 'central dogma of molecular biology'. 
                        Have you heard about this before?""")

@reactive.effect
@reactive.event(input.send)
def _():
    botIn = botLog.get() + "\n---- NEW RESPONSE FROM USER ----\n" + input.newChat()    
    botOut = str(chat_engine.query(botIn))
    userLog.set(userLog.get() + "<br>--- YOU:<br>" + input.newChat() + "<br>--- BOT:<br>" + botOut)
    botLog.set(botLog.get() + f"\n--- USER:\n{input.newChat()}" + f"\n--- YOU:\n" + botOut)   
    ui.update_text("newChat", value = "")

@render.ui
def chatLog():
    return HTML(userLog.get())

ui.input_text("newChat", "", value="")
ui.input_action_button("send", "Send")
