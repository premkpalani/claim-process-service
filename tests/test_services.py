from decimal import Decimal
from datetime import date

from app.services import ClaimService
from app.models import ClaimCreate, ClaimLineCreate


class TestNetFeeCalculation:
    """Test net fee calculation logic"""

    def test_net_fee_formula(self, session):
        """Test that net fee is calculated correctly using the formula:
        net_fee = provider_fees + member_coinsurance + member_copay - allowed_fees
        """
        service = ClaimService(session)

        # Test case 1: Zero coinsurance and copay
        net_fee1 = service.calculate_net_fee(
            provider_fees=Decimal("100.00"),
            member_coinsurance=Decimal("0.00"),
            member_copay=Decimal("0.00"),
            allowed_fees=Decimal("100.00"),
        )
        assert net_fee1 == Decimal("0.00")  # 100 + 0 + 0 - 100 = 0

        # Test case 2: With coinsurance
        net_fee2 = service.calculate_net_fee(
            provider_fees=Decimal("130.00"),
            member_coinsurance=Decimal("16.25"),
            member_copay=Decimal("0.00"),
            allowed_fees=Decimal("65.00"),
        )
        assert net_fee2 == Decimal("81.25")  # 130 + 16.25 + 0 - 65 = 81.25

        # Test case 3: With coinsurance and copay
        net_fee3 = service.calculate_net_fee(
            provider_fees=Decimal("178.00"),
            member_coinsurance=Decimal("35.60"),
            member_copay=Decimal("10.00"),
            allowed_fees=Decimal("178.00"),
        )
        assert net_fee3 == Decimal("45.60")  # 178 + 35.60 + 10 - 178 = 45.60


class TestClaimProcessing:
    """Test claim processing service"""

    def test_process_single_line_claim(self, session):
        """Test processing a claim with a single line"""
        service = ClaimService(session)

        claim_data = ClaimCreate(
            claim_reference="test_claim_001",
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
                )
            ],
        )

        claim = service.process_claim(claim_data)

        assert claim.id is not None
        assert claim.claim_reference == "test_claim_001"
        assert claim.status == "processed"
        assert len(claim.lines) == 1
        assert claim.total_net_fee == Decimal("0.00")
        assert claim.lines[0].net_fee == Decimal("0.00")

    def test_process_multi_line_claim(self, session):
        """Test processing a claim with multiple lines"""
        service = ClaimService(session)

        claim_data = ClaimCreate(
            claim_reference="test_claim_002",
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
                ClaimLineCreate(
                    service_date=date(2018, 3, 28),
                    submitted_procedure="D4346",
                    plan_group="GRP-1000",
                    subscriber_number="3730189502",
                    provider_npi="1497775530",
                    provider_fees=Decimal("130.00"),
                    allowed_fees=Decimal("65.00"),
                    member_coinsurance=Decimal("16.25"),
                    member_copay=Decimal("0.00"),
                ),
            ],
        )

        claim = service.process_claim(claim_data)

        assert claim.id is not None
        assert len(claim.lines) == 3
        # Total: 0 + 0 + 81.25 = 81.25
        assert claim.total_net_fee == Decimal("81.25")

    def test_get_claim_by_id(self, session):
        """Test retrieving a claim by ID"""
        service = ClaimService(session)

        # Create a claim
        claim_data = ClaimCreate(
            claim_reference="test_claim_003",
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
                )
            ],
        )
        created_claim = service.process_claim(claim_data)

        # Retrieve it
        retrieved_claim = service.get_claim_by_id(created_claim.id)

        assert retrieved_claim is not None
        assert retrieved_claim.id == created_claim.id
        assert retrieved_claim.claim_reference == "test_claim_003"

    def test_get_claim_by_reference(self, session):
        """Test retrieving a claim by reference"""
        service = ClaimService(session)

        # Create a claim
        claim_data = ClaimCreate(
            claim_reference="test_claim_004",
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
                )
            ],
        )
        service.process_claim(claim_data)

        # Retrieve it
        retrieved_claim = service.get_claim_by_reference("test_claim_004")

        assert retrieved_claim is not None
        assert retrieved_claim.claim_reference == "test_claim_004"


class TestTopProviders:
    """Test top providers functionality"""

    def test_top_providers_empty_database(self, session):
        """Test getting top providers when database is empty"""
        service = ClaimService(session)
        top_providers = service.get_top_providers_by_net_fees(limit=10)

        assert len(top_providers) == 0

    def test_top_providers_single_provider(self, session):
        """Test getting top providers with single provider"""
        service = ClaimService(session)

        # Create a claim
        claim_data = ClaimCreate(
            claim_reference="test_claim_005",
            lines=[
                ClaimLineCreate(
                    service_date=date(2018, 3, 28),
                    submitted_procedure="D0180",
                    plan_group="GRP-1000",
                    subscriber_number="3730189502",
                    provider_npi="1497775530",
                    provider_fees=Decimal("100.00"),
                    allowed_fees=Decimal("50.00"),
                    member_coinsurance=Decimal("10.00"),
                    member_copay=Decimal("5.00"),
                ),
            ],
        )
        service.process_claim(claim_data)

        top_providers = service.get_top_providers_by_net_fees(limit=10)

        assert len(top_providers) == 1
        assert top_providers[0].provider_npi == "1497775530"
        assert top_providers[0].total_net_fees == Decimal("65.00")  # 100 + 10 + 5 - 50
        assert top_providers[0].claim_count == 1
        assert top_providers[0].rank == 1

    def test_top_providers_multiple_providers(self, session):
        """Test getting top providers with multiple providers"""
        service = ClaimService(session)

        # Create claims for different providers
        for i, npi in enumerate(["1111111111", "2222222222", "3333333333"]):
            claim_data = ClaimCreate(
                claim_reference=f"test_claim_{100 + i}",
                lines=[
                    ClaimLineCreate(
                        service_date=date(2018, 3, 28),
                        submitted_procedure="D0180",
                        plan_group="GRP-1000",
                        subscriber_number="3730189502",
                        provider_npi=npi,
                        provider_fees=Decimal(str(100 * (i + 1))),
                        allowed_fees=Decimal("50.00"),
                        member_coinsurance=Decimal("0.00"),
                        member_copay=Decimal("0.00"),
                    )
                ],
            )
            service.process_claim(claim_data)

        top_providers = service.get_top_providers_by_net_fees(limit=10)

        assert len(top_providers) == 3
        # Should be sorted by net fees (descending)
        assert top_providers[0].provider_npi == "3333333333"  # 300 - 50 = 250
        assert top_providers[1].provider_npi == "2222222222"  # 200 - 50 = 150
        assert top_providers[2].provider_npi == "1111111111"  # 100 - 50 = 50
        assert top_providers[0].rank == 1
        assert top_providers[1].rank == 2
        assert top_providers[2].rank == 3

    def test_top_providers_limit(self, session):
        """Test that limit parameter works correctly"""
        service = ClaimService(session)

        # Create 15 providers
        for i in range(15):
            npi = str(1000000000 + i).zfill(10)
            claim_data = ClaimCreate(
                claim_reference=f"test_claim_{200 + i}",
                lines=[
                    ClaimLineCreate(
                        service_date=date(2018, 3, 28),
                        submitted_procedure="D0180",
                        plan_group="GRP-1000",
                        subscriber_number="3730189502",
                        provider_npi=npi,
                        provider_fees=Decimal(str(100 * (i + 1))),
                        allowed_fees=Decimal("0.00"),
                        member_coinsurance=Decimal("0.00"),
                        member_copay=Decimal("0.00"),
                    )
                ],
            )
            service.process_claim(claim_data)

        # Request only top 5
        top_providers = service.get_top_providers_by_net_fees(limit=5)

        assert len(top_providers) == 5
        # Should have ranks 1-5
        assert [p.rank for p in top_providers] == [1, 2, 3, 4, 5]
