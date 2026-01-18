from sqlmodel import Session, select, func, desc
from typing import Optional
from decimal import Decimal
import logging
import uuid

from app.models import Claim, ClaimLine, ClaimCreate, TopProviderResponse
from app.payment_service import PaymentServiceClient, PaymentRequest

logger = logging.getLogger(__name__)


class ClaimService:
    """Service for processing claims"""

    def __init__(self, session: Session):
        self.session = session
        self.payment_client = PaymentServiceClient()

    def calculate_net_fee(
        self,
        provider_fees: Decimal,
        member_coinsurance: Decimal,
        member_copay: Decimal,
        allowed_fees: Decimal,
    ) -> Decimal:
        """
        Calculate net fee per the formula:
        net_fee = provider_fees + member_coinsurance + member_copay - allowed_fees
        """
        net_fee = provider_fees + member_coinsurance + member_copay - allowed_fees
        logger.debug(
            f"Calculated net fee: {provider_fees} + {member_coinsurance} + "
            f"{member_copay} - {allowed_fees} = {net_fee}"
        )
        return net_fee

    def process_claim(self, claim_data: ClaimCreate) -> Claim:
        """
        Process a claim with multiple lines and store in database.

        This method:
        1. Creates a new claim with unique ID
        2. Processes each claim line and calculates net fees
        3. Stores the claim and lines in database
        4. Communicates with payment service (see payment_service.py)

        Returns:
            Claim: The processed claim with all lines
        """
        try:
            # Create claim with unique ID
            claim = Claim(
                claim_reference=claim_data.claim_reference,
                status="processing",
            )
            self.session.add(claim)
            self.session.flush()  # Get the claim ID

            logger.info(f"Processing claim {claim.id} - {claim.claim_reference}")

            # Process each line
            total_net_fee = Decimal("0.00")
            claim_lines = []

            for line_data in claim_data.lines:
                # Calculate net fee for this line
                net_fee = self.calculate_net_fee(
                    provider_fees=line_data.provider_fees,
                    member_coinsurance=line_data.member_coinsurance,
                    member_copay=line_data.member_copay,
                    allowed_fees=line_data.allowed_fees,
                )

                # Create claim line
                claim_line = ClaimLine(
                    **line_data.model_dump(),
                    claim_id=claim.id,
                    net_fee=net_fee,
                )
                self.session.add(claim_line)
                claim_lines.append(claim_line)

                total_net_fee += net_fee

            # Update claim with total net fee
            claim.total_net_fee = total_net_fee
            claim.status = "processed"

            # Flush to get updated claim data
            # Note: FastAPI's get_session dependency will handle the final commit
            self.session.flush()
            self.session.refresh(claim)

            logger.info(
                f"Claim {claim.id} processed successfully. "
                f"Total net fee: ${total_net_fee}"
            )

            # Send to payment service
            # This is async/fire-and-forget with retry mechanism
            self._send_to_payment_service(claim)

            return claim

        except Exception as e:
            logger.error(f"Error processing claim: {str(e)}")
            # Note: FastAPI's get_session dependency will handle rollback
            raise

    def _send_to_payment_service(self, claim: Claim):
        """
        Send processed claim to payment service.

        See app/payment_service.py for detailed implementation
        of the communication strategy including:
        - Asynchronous message queue (RabbitMQ/Kafka)
        - Retry mechanism with exponential backoff
        - Dead letter queue for failed messages
        - Idempotency handling
        - Distributed transaction management
        """
        try:
            payment_request = PaymentRequest(
                claim_id=claim.id,
                claim_reference=claim.claim_reference,
                total_net_fee=float(claim.total_net_fee),
                idempotency_key=f"claim-{claim.id}-{uuid.uuid4()}",
            )

            # This is a pseudo-implementation
            # See payment_service.py for actual async queue implementation
            self.payment_client.send_payment_request(payment_request)

        except Exception as e:
            logger.error(
                f"Failed to send claim {claim.id} to payment service: {str(e)}"
            )
            # Mark claim for retry (handled by background worker)
            claim.status = "payment_pending"
            # Note: Status change will be committed by the parent transaction
            # Don't commit here as it could interfere with the main transaction

    def get_top_providers_by_net_fees(
        self, limit: int = 10
    ) -> list[TopProviderResponse]:
        """
        Get top N providers by total net fees generated.

        Optimization Strategy:
        1. **Database-level aggregation**: Use SQL GROUP BY and SUM for efficiency
        2. **Indexing**: provider_npi column is indexed for fast lookups
        3. **Limit early**: Apply LIMIT at database level, not in application
        4. **Single query**: Avoid N+1 queries by using JOIN and aggregation

        Algorithm:
        - Time Complexity: O(n log n) where n is number of unique providers
          (due to sorting)
        - Space Complexity: O(k) where k is the limit (10 providers)
        - Database does the heavy lifting with indexed columns

        Data Structure:
        - Uses SQL result set (already optimized for large datasets)
        - Returns list of TopProviderResponse (lightweight DTOs)

        Performance Considerations:
        - For millions of claims: Add materialized view refreshed periodically
        - For real-time: Use Redis cache with TTL
        - For distributed systems: Use read replicas for analytics queries
        """
        logger.info(f"Fetching top {limit} providers by net fees")

        # SQL query with aggregation and ordering
        # This is optimized to run entirely in the database
        statement = (
            select(
                ClaimLine.provider_npi,
                func.sum(ClaimLine.net_fee).label("total_net_fees"),
                func.count(ClaimLine.id).label("claim_count"),
            )
            .group_by(ClaimLine.provider_npi)
            .order_by(desc("total_net_fees"))
            .limit(limit)
        )

        results = self.session.exec(statement).all()

        # Convert to response objects with ranking
        top_providers = [
            TopProviderResponse(
                provider_npi=row[0],
                total_net_fees=row[1],
                claim_count=row[2],
                rank=idx + 1,
            )
            for idx, row in enumerate(results)
        ]

        logger.info(f"Retrieved {len(top_providers)} top providers")
        return top_providers

    def get_claim_by_id(self, claim_id: int) -> Optional[Claim]:
        """Get a claim by ID"""
        statement = select(Claim).where(Claim.id == claim_id)
        return self.session.exec(statement).first()

    def get_claim_by_reference(self, claim_reference: str) -> Optional[Claim]:
        """Get a claim by reference"""
        statement = select(Claim).where(Claim.claim_reference == claim_reference)
        return self.session.exec(statement).first()
