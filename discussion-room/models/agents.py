from sqlalchemy import Column, DateTime, String, Integer, func, Text
from sqlalchemy.orm import relationship

from .models import Base


class Agents(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    model_id = Column(String)
    create_at = Column(DateTime, default=func.now())

    memories = relationship(
        "Memories",
        primaryjoin="foreign(Memories.model_id) == Agents.model_id",
        back_populates="agent",
    )

    def __repr__(self):
        return f"id: {self.id}, model_id: {self.model_id}"
