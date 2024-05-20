from sqlalchemy import (
    ARRAY,
    BigInteger,
    Column,
    Float,
    ForeignKey,
    String,
    Integer,
    JSON,
    Enum,
)
from sqlalchemy.orm import relationship
from .database import Base


class Assistant(Base):
    __tablename__ = "assistants"

    id = Column(String, primary_key=True)
    object = Column(String, nullable=False, default="assistant")
    created_at = Column(Integer, nullable=False)
    name = Column(String(256))
    description = Column(String(512))
    model = Column(String(256), nullable=False)
    instructions = Column(String(32768), default="")
    tools = Column(JSON)
    _metadata = Column("metadata", JSON, nullable=True)
    response_format = Column(
        String(256)
    )  # Assuming simple string to represent the format
    temperature = Column(Float)
    tool_resources = Column(JSON)
    top_p = Column(Float)

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
    created_at = Column(
        BigInteger, nullable=False
    )  # BigInteger to ensure no repreating timestamps
    thread_id = Column(String, ForeignKey('threads.id'))
    role = Column(Enum('user', 'assistant', name='role_types'), nullable=False)
    content = Column(
        ARRAY(JSON), nullable=False
    )  # Structured content (text/images)
    attachments = Column(JSON, nullable=True)
    assistant_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    _metadata = Column("metadata", JSON, nullable=True)
    status = Column(
        Enum('in_progress', 'incomplete', 'completed', name='status_types'),
        nullable=False,
        default='in_progress',
    )
    completed_at = Column(Integer, nullable=True)
    incomplete_at = Column(Integer, nullable=True)
    incomplete_details = Column(JSON, nullable=True)

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
    expires_at = Column(
        Integer, nullable=True
    )  # Changed from nullable=False to nullable=True
    failed_at = Column(Integer, nullable=True)
    incomplete_details = Column(JSON, nullable=True)  # Added field
    instructions = Column(String, nullable=False, default="")
    last_error = Column(JSON, nullable=True)
    max_completion_tokens = Column(Integer, nullable=True)  # Added field
    max_prompt_tokens = Column(Integer, nullable=True)  # Added field
    _metadata = Column(
        "metadata", JSON, nullable=True
    )  # Renamed _metadata to metadata
    model = Column(String, nullable=False)
    object = Column(String, nullable=False, default="thread.run")
    required_action = Column(JSON, nullable=True)  # Added field
    response_format = Column(JSON, nullable=True)  # Added field
    started_at = Column(Integer, nullable=True)
    status = Column(String, nullable=False)
    thread_id = Column(String, ForeignKey('threads.id'))
    tool_choice = Column(JSON, nullable=True)  # Added field
    tools = Column(
        JSON, nullable=True, default=[]
    )  # Modified default to match list in Pydantic schema
    truncation_strategy = Column(JSON, nullable=True)  # Added field
    usage = Column(JSON, nullable=True)
    temperature = Column(Float, nullable=True)  # Added field
    top_p = Column(Float, nullable=True)  # Added field

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
