import pytest
from pydantic import ValidationError
from decimal import Decimal
from datetime import date

from app.models import ClaimLineCreate, ClaimCreate


class TestClaimLineValidation:
    """Test data validation for claim lines"""

    def test_valid_submitted_procedure(self):
        """Test that valid procedure codes starting with D are accepted"""
        claim_line = ClaimLineCreate(
            service_date=date(2018, 3, 28),
            submitted_procedure="D0180",
            plan_group="GRP-1000",
            subscriber_number="3730189502",
            provider_npi="1497775530",
            provider_fees=Decimal("100.00"),
            allowed_fees=Decimal("100.00"),
            member_coinsurance=Decimal("0.00"),
            member_copay=Decimal("0.00"),
        )
        assert claim_line.submitted_procedure == "D0180"

    def test_invalid_submitted_procedure_no_d(self):
        """Test that procedure codes not starting with D are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ClaimLineCreate(
                service_date=date(2018, 3, 28),
                submitted_procedure="X0180",  # Invalid: doesn't start with D
                plan_group="GRP-1000",
                subscriber_number="3730189502",
                provider_npi="1497775530",
                provider_fees=Decimal("100.00"),
                allowed_fees=Decimal("100.00"),
                member_coinsurance=Decimal("0.00"),
                member_copay=Decimal("0.00"),
            )
        assert "Submitted procedure must start with 'D'" in str(exc_info.value)

    def test_submitted_procedure_case_insensitive(self):
        """Test that procedure codes are normalized to uppercase"""
        claim_line = ClaimLineCreate(
            service_date=date(2018, 3, 28),
            submitted_procedure="d0180",  # Lowercase
            plan_group="GRP-1000",
            subscriber_number="3730189502",
            provider_npi="1497775530",
            provider_fees=Decimal("100.00"),
            allowed_fees=Decimal("100.00"),
            member_coinsurance=Decimal("0.00"),
            member_copay=Decimal("0.00"),
        )
        assert claim_line.submitted_procedure == "D0180"

    def test_valid_provider_npi(self):
        """Test that valid 10-digit NPIs are accepted"""
        claim_line = ClaimLineCreate(
            service_date=date(2018, 3, 28),
            submitted_procedure="D0180",
            plan_group="GRP-1000",
            subscriber_number="3730189502",
            provider_npi="1497775530",  # Valid: 10 digits
            provider_fees=Decimal("100.00"),
            allowed_fees=Decimal("100.00"),
            member_coinsurance=Decimal("0.00"),
            member_copay=Decimal("0.00"),
        )
        assert claim_line.provider_npi == "1497775530"

    def test_invalid_provider_npi_too_short(self):
        """Test that NPIs with less than 10 digits are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ClaimLineCreate(
                service_date=date(2018, 3, 28),
                submitted_procedure="D0180",
                plan_group="GRP-1000",
                subscriber_number="3730189502",
                provider_npi="123456789",  # Invalid: 9 digits
                provider_fees=Decimal("100.00"),
                allowed_fees=Decimal("100.00"),
                member_coinsurance=Decimal("0.00"),
                member_copay=Decimal("0.00"),
            )
        assert "Provider NPI must be exactly 10 digits" in str(exc_info.value)

    def test_invalid_provider_npi_too_long(self):
        """Test that NPIs with more than 10 digits are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ClaimLineCreate(
                service_date=date(2018, 3, 28),
                submitted_procedure="D0180",
                plan_group="GRP-1000",
                subscriber_number="3730189502",
                provider_npi="12345678901",  # Invalid: 11 digits
                provider_fees=Decimal("100.00"),
                allowed_fees=Decimal("100.00"),
                member_coinsurance=Decimal("0.00"),
                member_copay=Decimal("0.00"),
            )
        # Pydantic returns its own validation message for max_length
        assert "provider_npi" in str(exc_info.value).lower()
        assert "10" in str(exc_info.value)  # Should mention the max length of 10

    def test_invalid_provider_npi_non_numeric(self):
        """Test that NPIs with non-numeric characters are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ClaimLineCreate(
                service_date=date(2018, 3, 28),
                submitted_procedure="D0180",
                plan_group="GRP-1000",
                subscriber_number="3730189502",
                provider_npi="149A775530",  # Invalid: contains letter
                provider_fees=Decimal("100.00"),
                allowed_fees=Decimal("100.00"),
                member_coinsurance=Decimal("0.00"),
                member_copay=Decimal("0.00"),
            )
        assert "Provider NPI must be exactly 10 digits" in str(exc_info.value)

    def test_quadrant_optional(self):
        """Test that quadrant field is optional"""
        # Without quadrant
        claim_line1 = ClaimLineCreate(
            service_date=date(2018, 3, 28),
            submitted_procedure="D0180",
            plan_group="GRP-1000",
            subscriber_number="3730189502",
            provider_npi="1497775530",
            provider_fees=Decimal("100.00"),
            allowed_fees=Decimal("100.00"),
            member_coinsurance=Decimal("0.00"),
            member_copay=Decimal("0.00"),
        )
        assert claim_line1.quadrant is None

        # With quadrant
        claim_line2 = ClaimLineCreate(
            service_date=date(2018, 3, 28),
            submitted_procedure="D4211",
            quadrant="UR",
            plan_group="GRP-1000",
            subscriber_number="3730189502",
            provider_npi="1497775530",
            provider_fees=Decimal("178.00"),
            allowed_fees=Decimal("178.00"),
            member_coinsurance=Decimal("35.60"),
            member_copay=Decimal("0.00"),
        )
        assert claim_line2.quadrant == "UR"


class TestClaimCreate:
    """Test claim creation with multiple lines"""

    def test_valid_claim_with_multiple_lines(self):
        """Test creating a valid claim with multiple lines"""
        claim_data = ClaimCreate(
            claim_reference="claim_1234",
            lines=[
                ClaimLineCreate(
                    service_date=date(2018, 3, 28),
                    submitted_procedure="D0180",
                    plan_group="GRP-1000",
                    subscriber_number="3730189502",
                    provider_npi="1497775530",
                    provider_fees=Decimal("100.00"),
                    allowed_fees=Decimal("100.00"),
                    member_coinsurance=Decimal("0.00"),
                    member_copay=Decimal("0.00"),
                ),
                ClaimLineCreate(
                    service_date=date(2018, 3, 28),
                    submitted_procedure="D0210",
                    plan_group="GRP-1000",
                    subscriber_number="3730189502",
                    provider_npi="1497775530",
                    provider_fees=Decimal("108.00"),
                    allowed_fees=Decimal("108.00"),
                    member_coinsurance=Decimal("0.00"),
                    member_copay=Decimal("0.00"),
                ),
            ],
        )
        assert claim_data.claim_reference == "claim_1234"
        assert len(claim_data.lines) == 2
