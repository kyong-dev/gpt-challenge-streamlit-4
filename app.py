from typing import Any, Type
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from langchain.agents import initialize_agent, AgentType
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper, WikipediaAPIWrapper
import openai as client
import json
import time
import streamlit as st


st.set_page_config(
    page_title="Assistant",
    page_icon="❓",
)

st.title("Assistant")
openai_api_key = ""

def search_duck(inputs):
    ddg = DuckDuckGoSearchAPIWrapper()
    topic = inputs["topic"]
    return ddg.run(f"The query you will search for. Example query: General research about {topic}")

def search_wiki(inputs):
    wiki = WikipediaAPIWrapper()
    topic = inputs["topic"]
    return wiki.run(f"The query you will search for. Example query: General research about {topic}")



functions_map = {
    "search_duck": search_duck,
    "search_wiki": search_wiki,
}

functions = [
    {
        "type": "function",
        "function": {
            "name": "search_duck",
            "description": "search for information on DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic you will search for. Example query: General research about the topic.",
                    }
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_wiki",
            "description": "search for information on Wikipedia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic you will search for. Example query: General research about the topic.",
                    }
                },
                "required": ["topic"],
            },
        },
    }
]

def get_run(run_id, thread_id):
    return client.beta.threads.runs.retrieve(
        run_id=run_id,
        thread_id=thread_id,
        
    )

def send_message(thread_id, content):
    return client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=content
    )


def get_messages(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    messages = list(messages)
    messages.reverse()
    for message in messages:
        print(f"{message.role}: {message.content[0].text.value}")
    return messages


def get_tool_outputs(run_id, thread_id):
    run = get_run(run_id, thread_id)
    outputs = []
    for action in run.required_action.submit_tool_outputs.tool_calls:
        action_id = action.id
        function = action.function
        print(f"Calling function: {function.name} with arg {function.arguments}")
        outputs.append(
            {
                "output": functions_map[function.name](json.loads(function.arguments)),
                "tool_call_id": action_id,
            }
        )
    return outputs

def submit_tool_outputs(run_id, thread_id):
    outpus = get_tool_outputs(run_id, thread_id)
    return client.beta.threads.runs.submit_tool_outputs(
        run_id=run_id,
        thread_id=thread_id,
        tool_outputs=outpus,
    )


with st.sidebar:
    openai_api_key = st.text_input("Write down your OpenAI key", placeholder="sk-proj-NDE*********")

    st.write("<a href='https://github.com/kyong-dev/gpt-challenge-streamlit-3'>https://github.com/kyong-dev/gpt-challenge-streamlit-3</a>", unsafe_allow_html=True)
    


assistant = client.beta.assistants.create(
    name="Search topic assistant",
    instructions="Search for information on DuckDuckGo and Wikipedia.",
    model="gpt-4-1106-preview",
    tools=functions,
)

inputs = st.text_input("Ask a question to the assistant.")

if inputs:
    st.write("Assistant is running...")

    thread = client.beta.threads.create(
        messages=[
            {
            "role": "user",
            "content": inputs,
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    with st.spinner("Assistant is generating..."):
            while get_run(run.id, thread.id).status in [
                "queued",
                "in_progress",
                "requires_action",
            ]:
                if get_run(run.id, thread.id).status == "requires_action":
                    submit_tool_outputs(run.id, thread.id)
                    time.sleep(0.5)
                else:
                    time.sleep(0.5)
            message = (
                get_messages(thread.id)[-1].content[0].text.value.replace("$", "\$")
            )

            st.markdown(message)



