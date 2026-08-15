from __future__ import annotations

from typing import Optional
import uuid

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, Uuid

from app.storage.db import Base
from app.storage.models.enums import MessageRole
from app.storage.models.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Conversation(TimestampMixin,Base):
    __tablename__="conversation"


    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="新对话")
    root_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey(
            "messages.id",
            use_alter=True,
            ondelete="SET NULL",
            name="fk_conversation_root_name",
        ),
        nullable=True,
    )
    max_depth:Mapped[int]=mapped_column(Integer,nullable=False,default=3)
    messages:Mapped[list[Message]]=relationship(
        "Message",
        back_populates="conversation",
        cascade="all,delete-orphan",
        foreign_keys="Message.conversation_id",
    )
    snapshots: Mapped[list[ContextSnapshot]] = relationship(
        "ContextSnapshot", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(TimestampMixin, Base):
    #树的节点：parent_message_id 指向父消息，NULL 表示树根

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    branch_path: Mapped[str] = mapped_column(String(200), nullable=False, default="root")
    anchor_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MessageRole.USER.value
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    branch_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_conversation_parent", "conversation_id", "parent_message_id"),
    )

    parent: Mapped[Optional[Message]] = relationship(
        "Message", remote_side=[id], back_populates="children"
    )
    children: Mapped[list[Message]] = relationship("Message", back_populates="parent")
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
        foreign_keys=[conversation_id],
    )


class ContextSnapshot(TimestampMixin, Base):
    #会话快照：继承祖先链摘要 + 关键引用，控制分支上下文 Token 消耗。

    __tablename__ = "context_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anchor_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_citations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="snapshots")