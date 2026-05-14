"""Single source of truth for SQLAlchemy declarative Base.

All model modules MUST import Base from this file (via app.models)
so that metadata is unified and Alembic can autogenerate correctly.
"""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
