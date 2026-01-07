import pika
# import sqlite3
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from models.agents import Agents, Base
from models.memories import Memories

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.tools.memory import MemoryTools
from agno.memory import MemoryManager, UserMemory
from agno.models.deepseek import DeepSeek
from agno.tools.shell import ShellTools
from agno.team import Team
from agno.utils.pprint import pprint_run_response


engine = create_engine("sqlite:///discussion_room.db")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq")
)

channel = connection.channel()
channel.queue_declare(queue="discussion-room")


db = SqliteDb(db_file="discussion_room_agno.db")

memory_tools = MemoryTools(db=db)
memory_manager = MemoryManager(
    model=DeepSeek(),
    db=db
)


def callback(ch, method, properties, body):
    print("entering discussion_room")

    data = json.loads(body.decode())
    user_id = data[0]['user_id']

    Base.metadata.create_all(engine)

    session = Session(engine)

    select_agents = select(Agents).where(Agents.model_id == user_id)
    is_agent_out = len(session.execute(select_agents).scalars().all()) == 0

    if is_agent_out:
        agent = Agents(model_id=data[0]['user_id'])
        session.add_all([agent])

        for item in data:
            memory = Memories(model_id=item['user_id'], memory=item["memory"])
            session.add_all([memory])
            session.commit()

    count_agents = select(func.count()).select_from(Agents)
    amount_of_agents = session.execute(count_agents).scalar_one()

    if amount_of_agents >= 2:
        query = (
            select(Agents, Memories)
            .join(Memories, Agents.model_id == Memories.model_id)
        )

        rows = session.execute(query).scalars().all()

        agents = []
        for agent in rows:
            for memory in agent.memories:
                memory_manager.add_user_memory(
                    memory=UserMemory(memory=memory.memory),
                    user_id=agent.model_id
                )

            agents.append(Agent(user_id=agent.model_id, tools=[ShellTools()]))

        team = Team(
            model=DeepSeek(),
            name="Mediator",
            members=agents,
            delegate_to_all_members=True,
            instructions=["Stop when consensus is reached"],
        )

        response = team.run(
            input=[
                """
                    You coordinate the team members allowing them to generate new knowledge about projects
                    Tell the agents on the team check the folder insights-from-agency_2 that is at /app
                    and, with their past experience, analyse it
                """,
            ],
            stream=True
        )
        pprint_run_response(response, markdown=True)

    else:
        print('...')


if __name__ == "__main__":
    channel.basic_consume(
        queue="discussion-room",
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()
