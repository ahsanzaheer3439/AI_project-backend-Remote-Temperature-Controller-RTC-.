import uuid
from sqlalchemy import Column, Numeric, DateTime, ForeignKey, UUID,Float,Boolean,Integer
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class AppSession(Base):
    __tablename__ = 'app_session'
    id = Column(Integer, primary_key=True,autoincrement=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    disconected_at = Column(DateTime, nullable=True)

    

class Readings(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True,autoincrement=True)
    temperature = Column(Numeric(5, 2), nullable=False)
    humidity = Column(Numeric(5, 2), nullable=False)
    recieved_at = Column(DateTime, nullable=False, server_default=func.now())
    session_id = Column(Integer, ForeignKey('app_session.id'), nullable=False)

class FanEvent(Base):
    __tablename__ = 'fan_events'
    id = Column(Integer, primary_key=True,autoincrement=True)
    session_id = Column(Integer, ForeignKey('app_session.id'), nullable=False, index=True)
    status = Column(Boolean, nullable=False)        # True = turned on, False = turned off
    changed_at = Column(DateTime, nullable=False)