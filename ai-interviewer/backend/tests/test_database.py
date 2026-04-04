"""Tests for database configuration and utilities."""

import inspect

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from app.database import (
    Base,
    engine,
    async_session_factory,
    init_db,
    get_session,
    check_db_connection,
)


class TestDatabaseConfiguration:
    """Tests for database configuration."""

    def test_engine_exists(self):
        """Test that async engine is created."""
        assert engine is not None
        assert isinstance(engine, AsyncEngine)

    def test_session_factory_exists(self):
        """Test that async session factory is created."""
        assert async_session_factory is not None

    def test_base_class_exists(self):
        """Test that declarative base class exists."""
        assert Base is not None


class TestDatabaseBase:
    """Tests for SQLAlchemy Base class."""

    def test_base_is_declarative_base(self):
        """Test that Base is a proper declarative base."""
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)

    def test_models_inherit_from_base(self):
        """Test that all models inherit from Base."""
        from app.models.user import User
        from app.models.consent import ConsentEvent
        from app.models.interview import InterviewSession, InterviewModule, InterviewTurn

        models = [
            User, ConsentEvent,
            InterviewSession, InterviewModule, InterviewTurn,
        ]

        for model in models:
            assert issubclass(model, Base), f"{model.__name__} should inherit from Base"


class TestGetSessionFunction:
    """Tests for get_session dependency function."""

    def test_get_session_is_async_generator(self):
        """Test that get_session is an async generator function."""
        assert inspect.isasyncgenfunction(get_session)

    def test_get_session_can_be_used_as_dependency(self):
        """Test that get_session has correct signature for FastAPI dependency."""
        sig = inspect.signature(get_session)
        # Should have no required parameters for a simple dependency
        params = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty]
        assert len(params) == 0


class TestCheckDbConnectionFunction:
    """Tests for check_db_connection function."""

    def test_check_db_connection_is_async(self):
        """Test that check_db_connection is an async function."""
        assert inspect.iscoroutinefunction(check_db_connection)

    def test_check_db_connection_returns_bool(self):
        """Test that check_db_connection has correct return type annotation."""
        hints = check_db_connection.__annotations__
        assert hints.get("return") == bool


class TestInitDbFunction:
    """Tests for init_db function."""

    def test_init_db_is_async(self):
        """Test that init_db is an async function."""
        assert inspect.iscoroutinefunction(init_db)

    def test_init_db_returns_none(self):
        """Test that init_db returns None."""
        hints = init_db.__annotations__
        assert hints.get("return") is None


class TestEngineConfiguration:
    """Tests for engine configuration settings."""

    def test_engine_uses_async_driver(self):
        """Test that engine URL uses asyncpg driver."""
        url_str = str(engine.url)
        assert "asyncpg" in url_str or "postgresql" in url_str

    def test_engine_has_pool(self):
        """Test that engine has connection pool."""
        assert engine.pool is not None

    def test_engine_database_name(self):
        """Test that engine connects to darpan database."""
        assert "darpan" in str(engine.url)


class TestSessionFactoryConfiguration:
    """Tests for session factory configuration."""

    def test_session_factory_uses_async_session(self):
        """Test that factory creates AsyncSession instances."""
        assert async_session_factory.class_ == AsyncSession

    def test_session_factory_expire_on_commit_disabled(self):
        """Test that expire_on_commit is disabled."""
        assert async_session_factory.kw.get("expire_on_commit") is False

    def test_session_factory_autocommit_disabled(self):
        """Test that autocommit is disabled."""
        assert async_session_factory.kw.get("autocommit") is False

    def test_session_factory_autoflush_disabled(self):
        """Test that autoflush is disabled."""
        assert async_session_factory.kw.get("autoflush") is False


class TestDatabaseModuleExports:
    """Tests for database module exports."""

    def test_all_required_exports(self):
        """Test that all required items are exported from database module."""
        import app.database as db_module

        required_exports = [
            "Base",
            "engine",
            "async_session_factory",
            "init_db",
            "get_session",
            "check_db_connection",
        ]

        for export in required_exports:
            assert hasattr(db_module, export), f"Missing export: {export}"

    def test_base_has_metadata(self):
        """Test that Base has metadata for table definitions."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None
