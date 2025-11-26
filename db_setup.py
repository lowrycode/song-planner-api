from app.database import engine
from app.models import Base


def create_db_tables():
    # Create all tables defined in models (if they don't already exist)
    Base.metadata.create_all(bind=engine)
    print("Tables created (if not already existing).")


if __name__ == "__main__":
    create_db_tables()
