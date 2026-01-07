from sqlalchemy import Column, DateTime, String, Integer, func, Text, ForeignKey
from sqlalchemy.orm import relationship

from .models import Base


class Memories(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True)
    model_id = Column(String)
    memory = Column(Text)
    create_at = Column(DateTime, default=func.now())

    agent = relationship(
        "Agents",
        primaryjoin="foreign(Memories.model_id) == Agents.model_id",
        back_populates="memories",
    )

    def __repr__(self):
        return f"id: {self.id}, model_id: {self.model_id}, memory: {self.memory}"
