import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class UserRole(enum.IntEnum):
    unapproved = 0
    normal = 1
    editor = 2
    admin = 3


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(Integer, default=UserRole.unapproved, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    refreshtokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"User id={self.id} username={self.username} hashed_pwd={self.hashed_password}"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="refreshtokens")


class SongUsage(Base):
    __tablename__ = "song_usage"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    used_date = Column(Date, nullable=False)
    used_at = Column(String(15), nullable=False)

    __table_args__ = (
        Index("idx_songusage_song_id", "song_id"),
        Index("idx_songusage_songid_date", "song_id", "used_date"),
        Index("idx_songusage_used_date", "used_date"),
        Index("idx_songusage_song_venue_date", "song_id", "used_at", "used_date"),
    )

    # Relationship to Song
    song = relationship("Song", back_populates="usages")

    def __repr__(self):
        return f"<SongUsage(id={self.id}, song_id={self.song_id}, used_date={self.used_date}, used_at='{self.used_at}')>"


class SongUsageStats(Base):
    __tablename__ = "song_usage_stats"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    used_at = Column(String(15), nullable=False)
    first_used = Column(Date, nullable=False)
    last_used = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("song_id", "used_at", name="uq_song_usage_stats_song_venue"),
        Index("idx_song_usage_stats_song", "song_id"),
        Index("idx_song_usage_stats_used_at", "used_at"),
    )

    # Relationship to Song
    song = relationship("Song", back_populates="usage_stats")

    def __repr__(self):
        return (
            f"<SongUsageStats("
            f"song_id={self.song_id}, "
            f"used_at='{self.used_at}', "
            f"first_used={self.first_used}, "
            f"last_used={self.last_used})>"
        )


class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True)
    first_line = Column(String(200), nullable=False)
    song_key = Column(String(5), nullable=True)  # to allow for Ab/Bb etc.
    is_hymn = Column(Boolean, nullable=False)
    copyright = Column(String(255), nullable=True)
    author = Column(String(150), nullable=True)
    duration = Column(Integer, nullable=False, default=0)

    # Relationship to SongUsage
    usages = relationship(
        "SongUsage", back_populates="song", cascade="all, delete-orphan"
    )
    usage_stats = relationship(
        "SongUsageStats", back_populates="song", cascade="all, delete-orphan"
    )
    lyrics = relationship(
        "SongLyrics", back_populates="song", uselist=False, cascade="all, delete-orphan"
    )
    resources = relationship(
        "SongResources",
        back_populates="song",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Song(id={self.id}, first_line='{self.first_line}')>"


class SongLyrics(Base):
    __tablename__ = "song_lyrics"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, unique=True)
    content = Column(Text, nullable=False)

    # Relationship to Song
    song = relationship("Song", back_populates="lyrics")

    def __repr__(self):
        return f"<SongLyrics(id={self.id}, song_id={self.song_id}, content='{self.content[:10]}...')>"


class SongResources(Base):
    __tablename__ = "song_resources"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, unique=True)
    sheet_music = Column(String, nullable=True)
    harmony_vid = Column(String, nullable=True)
    harmony_pdf = Column(String, nullable=True)
    harmony_ms = Column(String, nullable=True)

    # Relationship to Song
    song = relationship("Song", back_populates="resources")

    def __repr__(self):
        return (
            f"<SongResources(id={self.id}, song_id={self.song_id}, "
            f"sheet_music='{self.sheet_music}', harmony_vid='{self.harmony_vid}', "
            f"harmony_pdf='{self.harmony_pdf}', harmony_ms='{self.harmony_ms}')>"
        )
