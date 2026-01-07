from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class LotWf(Base):
    __tablename__ = "lot_wf"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lot_name = Column(String(128), nullable=False)
    wf_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("lot_name", "wf_number", name="uk_lot_wf"),)


class SpasNode(Base):
    __tablename__ = "spas_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="1")


class SpasModule(Base):
    __tablename__ = "spas_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="1")


class SpasSite(Base):
    __tablename__ = "spas_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="1")


class MeasurementRecipe(Base):
    __tablename__ = "measurement_recipe"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    version = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("name", "version", name="uk_recipe_name_version"),)


class ProductName(Base):
    __tablename__ = "product_names"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="1")


class SpasReference(Base):
    __tablename__ = "spas_references"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product_names.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("spas_sites.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("spas_nodes.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("spas_modules.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "site_id",
            "node_id",
            "module_id",
            name="uk_ref_combo",
        ),
    )


class MeasurementFile(Base):
    __tablename__ = "measurement_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_path = Column(String(2048), nullable=False)
    file_name = Column(String(255), nullable=False)
    reference_id = Column(BigInteger, ForeignKey("spas_references.id"), nullable=False)
    lot_wf_id = Column(Integer, ForeignKey("lot_wf.id"), nullable=True)
    recipe_id = Column(Integer, ForeignKey("measurement_recipe.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("file_path", "recipe_id", name="uk_files_path_recipe"),)


class MetricType(Base):
    __tablename__ = "metric_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    unit = Column(String(32), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")


class MeasurementItem(Base):
    __tablename__ = "measurement_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    class_name = Column(String(64), nullable=False)
    measure_item = Column(String(64), nullable=False)
    metric_type_id = Column(Integer, ForeignKey("metric_types.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="1")

    __table_args__ = (
        UniqueConstraint(
            "class_name",
            "measure_item",
            "metric_type_id",
            name="uk_item_class_key",
        ),
    )


class MeasurementRawData(Base):
    __tablename__ = "measurement_raw_data"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_id = Column(BigInteger, ForeignKey("measurement_files.id"), nullable=False)
    item_id = Column(BigInteger, ForeignKey("measurement_items.id"), nullable=False)
    measurable = Column(Boolean, nullable=False, server_default="1")
    x_index = Column(Integer, nullable=False)
    y_index = Column(Integer, nullable=False)
    x_0 = Column(Float, nullable=False)
    y_0 = Column(Float, nullable=False)
    x_1 = Column(Float, nullable=False)
    y_1 = Column(Float, nullable=False)
    value = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "file_id", "item_id", "x_index", "y_index", name="uk_raw_file_item_xy"
        ),
    )
