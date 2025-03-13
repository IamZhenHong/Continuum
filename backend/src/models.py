from sqlalchemy import Column, BigInteger, Text, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class UserMessage(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)  # ✅ Change to BigInteger
    message = Column(Text, nullable=False)
    message_type = Column(String(10), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
