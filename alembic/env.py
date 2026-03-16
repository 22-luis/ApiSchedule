from logging.config import fileConfig
import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.shared.db.database import Base
# Import all models here so Alembic can see them
from app.modules.codes.models.code import Code
from app.modules.codes.models.preparation import Preparation
from app.modules.organization.models.user import User
from app.modules.organization.models.team import Team, UserTeam, task_team_association
from app.modules.orders.models.order import Order
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.programming.models.task_creation_notification import TaskCreationNotification
from app.modules.programming.models.task_status_log import TaskStatusLog
from app.modules.orders.models.order_surplus import OrderSurplus
from app.modules.quality.models.test_record import TestRecord
from app.modules.quality.models.catalog_test import CatalogTest
from app.modules.quality.models.code_test import CodeTest
from app.modules.quality.models.catalog_test_question import CatalogTestQuestion
from app.modules.quality.models.test_results import TestResults
from app.modules.quality.models.code_test_parameter_specification import CodeTestParameterSpecification
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.models.quality_manual import QualityManual
from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.reports.models.compare import ProductionReport
from app.modules.reports.models.historico_comparacion_fechas import HistoricoComparacionFechas
from app.modules.timer.models.stopwatch import Stopwatch
from app.modules.timer.models.record_stopwatch import RecordStopwatch
from app.modules.warehouse.models.history import WarehouseHistory
from app.modules.available.models.availableModel import Available
from app.modules.supervisor.models import SupStopwatch, SupRecordStopwatch

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Construir URL desde variables de entorno
    url = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Configurar URL desde variables de entorno
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 30}
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()