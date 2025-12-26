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
channel.queue_declare(queue="file-system-monitor")

db = SqliteDb(db_file=os.getenv("DB_PATH"))

memory_tools = MemoryTools(db=db)

fileSystemMonitor = Agent(
    tools=[ShellTools(), memory_tools],
    model=DeepSeek(id="deepseek-chat"),
    instructions=[
        "You are the file system monitor.",
        "Your goal is to fetch information about folder structures and files of project and save it to your memory.",
        "After running a command save its output to memory."
    ],
    stream=True,
    user_id="file-system-monitor",
    debug_mode=True
)

s1: RunOutput = fileSystemMonitor.run("Check the files in this folder.")
pprint_run_response(s1)

if __name__ == "__main__":
    memories = fileSystemMonitor.get_user_memories(user_id="fileSystemMonitor")
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
