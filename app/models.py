from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import field_validator, ValidationInfo
import re


class ClaimLineBase(SQLModel):
    """Base model for claim line items"""

    service_date: date
    submitted_procedure: str = Field(max_length=50)
    quadrant: Optional[str] = Field(default=None, max_length=10)
    plan_group: str = Field(max_length=50)
    subscriber_number: str = Field(max_length=50)
    provider_npi: str = Field(max_length=10)
    provider_fees: Decimal = Field(decimal_places=2)
    allowed_fees: Decimal = Field(decimal_places=2)
    member_coinsurance: Decimal = Field(decimal_places=2)
    member_copay: Decimal = Field(decimal_places=2)

    @field_validator("submitted_procedure")
    @classmethod
    def validate_submitted_procedure(cls, v: str, info: ValidationInfo) -> str:
        """Validate that submitted procedure starts with 'D'"""
        if not v or not v.upper().startswith('D'):
            raise ValueError(
                f"Submitted procedure must start with 'D', got: {v}"
            )
        return v.upper()

    @field_validator("provider_npi")
    @classmethod
    def validate_provider_npi(cls, v: str, info: ValidationInfo) -> str:
        """Validate that provider NPI is exactly 10 digits"""
        if not v or not re.match(r'^\d{10}$', v):
            raise ValueError(
                f"Provider NPI must be exactly 10 digits, got: {v}"
            )
        return v


class ClaimLine(ClaimLineBase, table=True):
    """Claim line item stored in database"""

    __tablename__ = "claim_lines"

    id: Optional[int] = Field(default=None, primary_key=True)
    claim_id: Optional[int] = Field(default=None, foreign_key="claims.id")
    net_fee: Decimal = Field(decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    claim: Optional["Claim"] = Relationship(back_populates="lines")


class ClaimBase(SQLModel):
    """Base model for claims"""

    claim_reference: str = Field(max_length=100, unique=True)
    status: str = Field(default="pending", max_length=50)


class Claim(ClaimBase, table=True):
    """Claim stored in database"""

    __tablename__ = "claims"

    id: Optional[int] = Field(default=None, primary_key=True)
    total_net_fee: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationship
    lines: list["ClaimLine"] = Relationship(back_populates="claim")


class ClaimLineCreate(ClaimLineBase):
    """Schema for creating a claim line"""
    pass


class ClaimCreate(SQLModel):
    """Schema for creating a claim with multiple lines"""

    claim_reference: str = Field(max_length=100)
    lines: list[ClaimLineCreate]


class ClaimResponse(ClaimBase):
    """Response schema for a claim"""

    id: int
    total_net_fee: Decimal
    created_at: datetime
    lines: list[ClaimLine]

    class Config:
        from_attributes = True


class TopProviderResponse(SQLModel):
    """Response schema for top providers by net fees"""

    provider_npi: str
    total_net_fees: Decimal
    claim_count: int
    rank: int
