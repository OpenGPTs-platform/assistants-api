from sqlalchemy import ARRAY, Column, ForeignKey, String, Integer, JSON, Enum
from sqlalchemy.orm import relationship
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


class FilePurpose(Enum):
    FINE_TUNE = "fine-tune"
    ASSISTANTS = "assistants"


class FileStatus(Enum):
    UPLOADED = "uploaded"
    PROCESSED = "processed"
    ERROR = "error"


class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, index=True)
    bytes = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False)
    filename = Column(String(256), nullable=False)
    object = Column(
        Enum("file", name="file_object"),
        nullable=False,
        default="file",
    )
    purpose = Column(
        Enum("assistants", name="file_purpose"),
        nullable=False,
    )
    status = Column(
        Enum("uploaded", name="file_status"),
        nullable=False,
    )
    status_details = Column(String(512), nullable=True)


class Thread(Base):
    __tablename__ = "threads"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(Integer, nullable=False)
    _metadata = Column("metadata", JSON, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    object = Column(String, nullable=False, default="thread.message")
    created_at = Column(Integer, nullable=False)
    thread_id = Column(String, ForeignKey('threads.id'))
    role = Column(Enum('user', 'assistant', name='role_types'), nullable=False)
    content = Column(
        ARRAY(JSON), nullable=False
    )  # To store structured content including text and images
    assistant_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    file_ids = Column(ARRAY(String), nullable=True)  # Stores up to 10 file IDs
    _metadata = Column("metadata", JSON, nullable=True)

    # Establish a relationship to the Thread model
    thread = relationship("Thread", back_populates="messages")


Thread.messages = relationship(
    "Message", order_by=Message.id, back_populates="thread"
)
