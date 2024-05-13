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
    object = Column(String, nullable=False, default="thread")
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
    "Message", order_by=Message.created_at, back_populates="thread"
)


class Run(Base):
    __tablename__ = 'runs'

    id = Column(String, primary_key=True, index=True)
    assistant_id = Column(String, index=False)
    cancelled_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False)
    expires_at = Column(Integer, nullable=False)
    failed_at = Column(Integer, nullable=True)
    file_ids = Column(JSON, default=[])
    instructions = Column(String, nullable=False, default="")
    last_error = Column(JSON, nullable=True)
    _metadata = Column("metadata", JSON, nullable=True)
    model = Column(String, nullable=False)
    object = Column(String, nullable=False, default="thread.run")
    started_at = Column(Integer, nullable=True)
    status = Column(String, nullable=False)
    thread_id = Column(String, ForeignKey('threads.id'))
    tools = Column(JSON, nullable=True, default=[])
    usage = Column(JSON, nullable=True)

    thread = relationship("Thread", back_populates="runs")


Thread.runs = relationship(
    "Run", order_by=Run.created_at, back_populates="thread"
)


class RunStep(Base):
    __tablename__ = "run_steps"

    id = Column(String, primary_key=True, index=True)
    assistant_id = Column(String, ForeignKey('assistants.id'))
    cancelled_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False)
    expired_at = Column(Integer, nullable=True)
    failed_at = Column(Integer, nullable=True)
    last_error = Column(JSON, nullable=True)
    _metadata = Column("metadata", JSON, nullable=True)
    object = Column(String, nullable=False, default="thread.run.step")
    run_id = Column(String, ForeignKey('runs.id'))
    status = Column(
        Enum(
            "in_progress",
            "cancelled",
            "failed",
            "completed",
            "expired",
            name="run_step_status",
        ),
        nullable=False,
    )
    step_details = Column(
        JSON, nullable=False
    )  # To store details refer to https://github.com/OpenGPTs-platform/assistants-api/issues/12 # noqa
    thread_id = Column(String, ForeignKey('threads.id'))
    type = Column(
        Enum("message_creation", "tool_calls", name="run_step_type"),
        nullable=False,
    )
    usage = Column(JSON, nullable=True)

    # assistant = relationship("Assistant", back_populates="run_steps")
    # run = relationship("Run", back_populates="run_steps")
    thread = relationship("Thread", back_populates="run_steps")


Thread.run_steps = relationship(
    "RunStep", order_by=RunStep.created_at, back_populates="thread"
)


class VectorStore(Base):
    __tablename__ = 'vector_stores'

    id = Column(String, primary_key=True, index=True)
    created_at = Column(Integer, nullable=False)
    last_active_at = Column(Integer, nullable=True)
    _metadata = Column("metadata", JSON, nullable=True)
    name = Column(String(256), nullable=False)
    object = Column(String, nullable=False, default="vector_store")
    status = Column(
        Enum(
            "in_progress",
            "completed",
            "expired",
            name="vector_store_status",
        ),
        nullable=False,
    )
    usage_bytes = Column(Integer, nullable=False)
    file_counts = Column(JSON, nullable=False)
    expires_after = Column(JSON, nullable=True)
    expires_at = Column(Integer, nullable=True)


class VectorStoreFileBatch(Base):
    __tablename__ = "vector_store_file_batches"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(Integer, nullable=False)
    vector_store_id = Column(String, index=True, nullable=False)
    object = Column(String, nullable=False, default="vector_store.files_batch")
    status = Column(
        Enum(
            "in_progress",
            "completed",
            "cancelled",
            "failed",
            name="batch_status",
        ),
        default="in_progress",
    )
    file_counts = Column(JSON, nullable=False)
