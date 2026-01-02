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


class ActivityType(enum.IntEnum):
    service = 0
    other = 1


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
        return f"User id={self.id} username={self.username}"


class UserNetworkAccess(Base):
    __tablename__ = "user_network_access"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    network_id = Column(
        Integer,
        ForeignKey("networks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user = relationship("User", lazy="joined")
    network = relationship("Network", lazy="joined")
    __table_args__ = (Index("idx_user_network_access_user", "user_id"),)

    def __repr__(self):
        return (
            f"<UserNetworkAccess user_id={self.user_id} network_id={self.network_id}>"
        )


class UserChurchAccess(Base):
    __tablename__ = "user_church_access"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user = relationship("User", lazy="joined")
    church = relationship("Church", lazy="joined")
    __table_args__ = (Index("idx_user_church_access_user", "user_id"),)

    def __repr__(self):
        return f"<UserChurchAccess user_id={self.user_id} church_id={self.church_id}>"


class UserChurchActivityAccess(Base):
    __tablename__ = "user_church_activity_access"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    church_activity_id = Column(
        Integer,
        ForeignKey("church_activities.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user = relationship("User", lazy="joined")
    church_activity = relationship("ChurchActivity", lazy="joined")
    __table_args__ = (Index("idx_user_activity_access_user", "user_id"),)

    def __repr__(self):
        return (
            f"<UserChurchActivityAccess user_id={self.user_id} "
            f"church_activity_id={self.church_activity_id}>"
        )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
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
    song_id = Column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False
    )
    used_date = Column(Date, nullable=False)
    church_activity_id = Column(
        Integer, ForeignKey("church_activities.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    song = relationship("Song", back_populates="usages")
    church_activity = relationship("ChurchActivity", back_populates="song_usages")

    __table_args__ = (
        Index("idx_songusage_song_id", "song_id"),
        Index("idx_songusage_activity_date", "church_activity_id", "used_date"),
        Index(
            "idx_songusage_song_activity_date",
            "song_id",
            "church_activity_id",
            "used_date",
        ),
    )

    def __repr__(self):
        return (
            f"<SongUsage(id={self.id}, song_id={self.song_id}, "
            f"used_date={self.used_date}, "
            f"church_activity_id={self.church_activity_id})>"
        )


class SongUsageStats(Base):
    __tablename__ = "song_usage_stats"

    id = Column(Integer, primary_key=True)
    song_id = Column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False
    )
    church_activity_id = Column(
        Integer, ForeignKey("church_activities.id", ondelete="CASCADE"), nullable=False
    )
    first_used = Column(Date, nullable=False)
    last_used = Column(Date, nullable=False)

    # Relationships
    song = relationship("Song", back_populates="usage_stats")
    church_activity = relationship("ChurchActivity", back_populates="usage_stats")

    __table_args__ = (
        UniqueConstraint(
            "song_id",
            "church_activity_id",
            name="uq_song_usage_stats_song_activity",
        ),
        Index("idx_song_usage_stats_song", "song_id"),
        Index("idx_song_usage_stats_activity", "church_activity_id"),
    )

    def __repr__(self):
        return (
            f"<SongUsageStats("
            f"song_id={self.song_id}, "
            f"church_activity_id={self.church_activity_id}, "
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

    # Relationships
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
    song_id = Column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    content = Column(Text, nullable=False)

    # Relationship to Song
    song = relationship("Song", back_populates="lyrics")

    def __repr__(self):
        return (
            f"<SongLyrics(id={self.id}, song_id={self.song_id}, "
            f"content='{self.content[:10]}...')>"
        )


class SongResources(Base):
    __tablename__ = "song_resources"

    id = Column(Integer, primary_key=True)
    song_id = Column(
        Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
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


class Network(Base):
    __tablename__ = "networks"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)

    # Relationship to churches
    churches = relationship(
        "Church", back_populates="network", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Network id={self.id} name={self.name}>"


class Church(Base):
    __tablename__ = "churches"

    id = Column(Integer, primary_key=True)
    network_id = Column(
        Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(20), nullable=False)
    slug = Column(String(20), nullable=False)

    # Relationships
    network = relationship("Network", back_populates="churches")
    activities = relationship(
        "ChurchActivity", back_populates="church", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Church id={self.id} network_id={self.network_id} name={self.name}>"


class ChurchActivity(Base):
    __tablename__ = "church_activities"
    __table_args__ = (
        UniqueConstraint("church_id", "slug", name="uq_church_activity_slug"),
        UniqueConstraint("church_id", "name", name="uq_church_activity_name"),
        Index("idx_church_activity_church", "church_id"),
    )

    id = Column(Integer, primary_key=True)
    church_id = Column(
        Integer, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(50), nullable=False)
    slug = Column(String(50), nullable=False)
    type = Column(Integer, default=ActivityType.service, nullable=False)

    # Relationship to Church
    church = relationship("Church", back_populates="activities")
    song_usages = relationship("SongUsage", back_populates="church_activity")
    usage_stats = relationship("SongUsageStats", back_populates="church_activity")

    def __repr__(self):
        return f"<ChurchActivity id={self.id} name={self.name}>"
