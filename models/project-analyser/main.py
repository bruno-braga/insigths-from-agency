#!/usr/bin/env python3

import json
import pika
import os

from agno.agent import Agent, RunOutput

from agno.db.sqlite import SqliteDb

from agno.models.deepseek import DeepSeek

from agno.tools.shell import ShellTools
from agno.tools.memory import MemoryTools

from agno.utils.pprint import pprint_run_response


rabbitmq_connection = pika.BlockingConnection(
    pika.ConnectionParameters("rabbitmq")
)

channel = rabbitmq_connection.channel()
channel.queue_declare(queue="project-analyser")

db = SqliteDb(db_file=os.getenv("DB_PATH"))

memory_tools = MemoryTools(db=db)

projectAnalyser = Agent(
    tools=[ShellTools(), memory_tools],
    model=DeepSeek(id="deepseek-chat"),
    instructions=[
        "You are the project analyser.",
        "Your goal is to fetch information about the project and save it to your memory.",
        "Do not run main.py.",
        "After running a command save its output to memory."
    ],
    db=db,
    stream=True,
    user_id="project-analyser",
)

s1: RunOutput = projectAnalyser.run(
    "Check what kind of project is this.",
)
pprint_run_response(s1)

if __name__ == "__main__":
    memories = projectAnalyser.get_user_memories(user_id="project-analyser")
    memories_json = json.dumps(
        [memory.to_dict() for memory in memories],
        indent=4
    )

    channel.basic_publish(
        exchange="",
        routing_key="router",
        body=memories_json
    )

    rabbitmq_connection.close()
