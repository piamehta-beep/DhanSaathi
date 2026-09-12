import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_pk():
    return Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


class Customer(Base):
    __tablename__ = "customers"

    id = uuid_pk()
    external_id = Column(String(50), unique=True)
    persona = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    preferred_language = Column(String(10), nullable=False, default="hi")
    monthly_income_mean = Column(Numeric(12, 2), nullable=False)
    monthly_income_std = Column(Numeric(12, 2), nullable=False)
    liquid_savings = Column(Numeric(14, 2), nullable=False)
    credit_limit = Column(Numeric(14, 2), nullable=True)
    credit_outstanding = Column(Numeric(14, 2), nullable=True)
    life_stage = Column(String(20), nullable=False)
    distress_state = Column(Boolean, nullable=False, default=False)
    distress_event_month = Column(Integer, nullable=True)
    distress_event_type = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    transactions = relationship("Transaction", back_populates="customer")
    obligations = relationship("RecurringObligation", back_populates="customer")
    loans = relationship("Loan", back_populates="customer")

    __table_args__ = (Index("idx_customers_persona", "persona"),)


class Transaction(Base):
    __tablename__ = "transactions"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    txn_date = Column(Date, nullable=False)
    txn_time = Column(Time, nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(6), nullable=False)
    category = Column(String(50), nullable=False)
    merchant = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_recurring = Column(Boolean, default=False)
    recurring_id = Column(UUID(as_uuid=True), ForeignKey("recurring_obligations.id"), nullable=True)
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("type IN ('credit','debit')", name="ck_transactions_type"),
        Index("idx_txns_customer_date", "customer_id", "txn_date"),
        Index("idx_txns_customer_category", "customer_id", "category"),
        Index("idx_txns_customer_recurring", "customer_id", "is_recurring"),
        Index("idx_txns_anomalies", "customer_id"),
    )


class RecurringObligation(Base):
    __tablename__ = "recurring_obligations"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    type = Column(String(20), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    frequency = Column(String(10), nullable=False)
    day_of_month = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    linked_loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="obligations")

    __table_args__ = (
        CheckConstraint(
            "type IN ('emi','rent','insurance_premium','sip','subscription')",
            name="ck_obligations_type",
        ),
        CheckConstraint("frequency IN ('monthly','quarterly','annual')", name="ck_obligations_frequency"),
        Index("idx_obligations_customer_active", "customer_id", "active"),
    )


class Loan(Base):
    __tablename__ = "loans"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    product_type = Column(String(30), nullable=False)
    principal = Column(Numeric(14, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    tenure_months = Column(Integer, nullable=False)
    emi_amount = Column(Numeric(12, 2), nullable=False)
    outstanding = Column(Numeric(14, 2), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(15), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="loans")

    __table_args__ = (
        CheckConstraint("status IN ('active','closed','defaulted')", name="ck_loans_status"),
        Index("idx_loans_customer_status", "customer_id", "status"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    product_type = Column(String(30), nullable=False)
    amount = Column(Numeric(14, 2), nullable=True)
    tenure_months = Column(Integer, nullable=True)
    cbs_score = Column(Numeric(8, 4), nullable=False)
    cbs_components = Column(JSONB, nullable=False)
    constraints_passed = Column(JSONB, nullable=False)
    constraints_failed = Column(JSONB, nullable=False)
    shap_values = Column(JSONB, nullable=False)
    simulation_summary = Column(JSONB, nullable=False)
    distress_probability = Column(Numeric(6, 4), nullable=False)
    confidence_level = Column(String(25), nullable=False)
    confidence_interval = Column(JSONB, nullable=False)
    status = Column(String(15), nullable=False)
    veto_reason = Column(String(100), nullable=True)
    llm_explanation = Column(Text, nullable=True)
    language = Column(String(10), nullable=False, default="hi")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('recommended','vetoed','no_action')", name="ck_recommendations_status"),
        Index("idx_recs_customer_created", "customer_id", "created_at"),
    )


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=True)
    scenario = Column(String(50), nullable=False)
    n_paths = Column(Integer, nullable=False)
    months_projected = Column(Integer, nullable=False)
    p_shortfall_12m = Column(Numeric(6, 4), nullable=False)
    expected_liquidity = Column(JSONB, nullable=False)
    liquidity_percentiles = Column(JSONB, nullable=False)
    parameters = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_sim_customer_created", "customer_id", "created_at"),)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    detection_method = Column(String(20), nullable=False)
    anomaly_score = Column(Numeric(6, 4), nullable=False)
    confidence = Column(Numeric(6, 4), nullable=False)
    features = Column(JSONB, nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed = Column(Boolean, default=False)
    is_true_positive = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_anomalies_customer_detected", "customer_id", "detected_at"),)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    scope = Column(String(30), nullable=False)
    granted = Column(Boolean, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    purpose = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "scope IN ('transaction_analysis','credit_assessment','product_recommendation',"
            "'marketing','anomaly_monitoring')",
            name="ck_consent_scope",
        ),
        Index("idx_consent_customer_scope", "customer_id", "scope"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    action = Column(String(50), nullable=False)
    module = Column(String(30), nullable=False)
    input_hash = Column(String(64), nullable=False)
    output_summary = Column(JSONB, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_customer_ts", "customer_id", "timestamp"),
        Index("idx_audit_action", "action"),
    )


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    features = Column(JSONB, nullable=False)
    model_version = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_features_customer_date", "customer_id", "snapshot_date"),)


class BankProduct(Base):
    """Real-bank product reference data used to ground recommender output.

    Seeded from data/bank_products_seed.csv — see source_note/source_url per row
    for provenance; rate bands are illustrative unless a source_url is verified.
    """

    __tablename__ = "bank_products"

    id = uuid_pk()
    bank_name = Column(String(80), nullable=False)
    product_type = Column(String(30), nullable=False)
    product_name = Column(String(150), nullable=False)
    min_amount = Column(Numeric(14, 2), nullable=False)
    max_amount = Column(Numeric(14, 2), nullable=False)
    interest_rate_min = Column(Numeric(5, 2), nullable=False)
    interest_rate_max = Column(Numeric(5, 2), nullable=False)
    tenure_options = Column(JSONB, nullable=False)
    processing_fee_pct = Column(Numeric(5, 2), nullable=True)
    annual_fee = Column(Numeric(10, 2), nullable=True)
    eligibility_notes = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    source_note = Column(Text, nullable=False)
    last_verified_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "product_type IN ('personal_loan','credit_card','term_insurance','mutual_fund_sip')",
            name="ck_bank_products_type",
        ),
        Index("idx_bank_products_type", "product_type"),
    )
