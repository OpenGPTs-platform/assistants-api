from sqlalchemy import Column, String, Integer, JSON, Enum
from .database import Base


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(String, primary_key=True, index=True)
    object = Column(
        Enum("assistant", name="assistant_object"),
        nullable=False,
        default="assistant",
    )  # Since "object" is a reserved keyword in Python, consider renaming or handle appropriately # noqa
    created_at = Column(Integer, nullable=False)
    name = Column(String(256), nullable=True)
    description = Column(String(512), nullable=True)
    model = Column(String, nullable=False)
    instructions = Column(String(32768), nullable=True)
    tools = Column(
        JSON, default=[]
    )  # Ensure your database supports JSON type; otherwise, consider storing as String and serializing/deserializing # noqa
    file_ids = Column(JSON, default=[])
    _metadata = Column("metadata", JSON, nullable=True)

    # # If there's a relationship with users (assuming one assistant can belong to one user) # noqa
    # user_id = Column(String, ForeignKey('users.id'))
    # owner = relationship("User", back_populates="user_gpts")
