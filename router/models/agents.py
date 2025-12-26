from sqlalchemy import Column, DateTime, String, Integer, func, Text

from .models import Base


class Agents(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    model_id = Column(String)
    memory = Column(Text)
    create_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"id: {self.id}, name: {self.name}"
