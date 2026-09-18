
from app.db import Base, engine

# Import models so SQLAlchemy knows about all tables.
from app.models import (  # noqa: F401
    Alert,
    Customer,
    SanctionsEntity,
    Transaction,
)


def main():
    print("Creating AML Investigator database...")

    Base.metadata.create_all(bind=engine)

    print("Database created successfully.")
    print(f"Location: {engine.url.database}")


if __name__ == "__main__":
    main()

