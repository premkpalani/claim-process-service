"""
Payment Service Communication Module

This module handles communication between claim_process and payments service.

ARCHITECTURE OVERVIEW:
=====================
We use an asynchronous message queue (RabbitMQ/Kafka) for reliable,
decoupled communication between services.

DESIGN DECISIONS:
=================
1. Asynchronous messaging (not synchronous HTTP) because:
   - Services can process at their own pace
   - No tight coupling or cascading failures
   - Built-in retry and DLQ mechanisms
   - Handles high volumes with backpressure

2. Idempotency to handle duplicate processing
3. Saga pattern for distributed transactions
4. Circuit breaker to prevent cascading failures

FAILURE HANDLING:
=================
1. claim_process fails after sending message:
   - Message already in queue, payments will process it
   - Use transaction outbox pattern to ensure atomicity

2. payments service fails to process:
   - Message goes to retry queue with exponential backoff
   - After N retries, moves to Dead Letter Queue (DLQ)
   - Alert team for manual intervention
   - claim_process can query status via status API

3. Network partition:
   - Messages persist in queue
   - Consumers reconnect and continue processing
   - Idempotency prevents duplicate charges

CONCURRENT INSTANCES:
=====================
Multiple instances of both services can run concurrently:
- Queue ensures each message processed exactly once
- Idempotency keys prevent duplicate processing
- Database locks prevent race conditions
- Distributed locks (Redis) for critical sections
"""

from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class PaymentRequest(BaseModel):
    """Payment request sent to payments service"""

    claim_id: int
    claim_reference: str
    total_net_fee: float
    idempotency_key: str  # Unique key to prevent duplicate processing


class PaymentServiceClient:
    """
    Client for sending payment requests to the payments service.

    In production, this would use:
    - RabbitMQ/Kafka for message queue
    - Celery/RQ for async task processing
    - Redis for distributed locks
    """

    def __init__(self):
        """Initialize payment service client"""
        # PSEUDO CODE: Initialize message queue connection
        # self.queue = RabbitMQClient(
        #     host=settings.RABBITMQ_HOST,
        #     queue_name="payment_requests",
        #     retry_queue="payment_requests_retry",
        #     dlq="payment_requests_dlq"
        # )
        pass

    def send_payment_request(self, payment_request: PaymentRequest):
        """
        Send payment request to payments service.

        PSEUDO CODE IMPLEMENTATION:
        ===========================

        def send_payment_request(self, payment_request: PaymentRequest):
            '''
            Send payment request via message queue with retry logic.
            '''

            try:
                # 1. TRANSACTION OUTBOX PATTERN
                # ============================
                # Store message in outbox table within same DB transaction as claim
                # Background worker publishes messages from outbox to queue
                # This ensures atomicity: if claim save fails, message not sent

                outbox_message = OutboxMessage(
                    aggregate_id=payment_request.claim_id,
                    aggregate_type="claim",
                    event_type="payment_requested",
                    payload=payment_request.model_dump_json(),
                    idempotency_key=payment_request.idempotency_key,
                    status="pending"
                )
                db.session.add(outbox_message)
                db.session.commit()

                # 2. BACKGROUND WORKER PUBLISHES TO QUEUE
                # ========================================
                # Separate process polls outbox table and publishes messages

                # Background Worker Code:
                while True:
                    pending_messages = db.query(OutboxMessage).filter(
                        OutboxMessage.status == "pending"
                    ).limit(100).all()

                    for message in pending_messages:
                        try:
                            # Publish to message queue
                            self.queue.publish(
                                message=message.payload,
                                routing_key="payment.process",
                                headers={
                                    "idempotency-key": message.idempotency_key,
                                    "retry-count": 0,
                                    "max-retries": 3
                                }
                            )

                            # Mark as published
                            message.status = "published"
                            db.session.commit()

                        except Exception as e:
                            logger.error(f"Failed to publish message: {e}")
                            # Will retry on next poll
                            continue

                    time.sleep(1)  # Poll interval

                # 3. PAYMENTS SERVICE CONSUMPTION
                # ===============================
                # payments service listens to queue

                @queue.consumer(queue="payment_requests")
                def process_payment(message):
                    '''
                    Process payment in payments service.
                    '''
                    try:
                        payment_request = PaymentRequest.parse_raw(message.body)

                        # CHECK IDEMPOTENCY
                        # =================
                        # Prevent duplicate processing
                        if redis.exists(f"payment:{payment_request.idempotency_key}"):
                            logger.info(f"Payment already processed: {payment_request.idempotency_key}")
                            message.ack()  # Acknowledge without reprocessing
                            return

                        # PROCESS PAYMENT
                        # ===============
                        with db.transaction():
                            payment = Payment(
                                claim_id=payment_request.claim_id,
                                amount=payment_request.total_net_fee,
                                status="pending"
                            )
                            db.session.add(payment)

                            # Call payment gateway
                            response = payment_gateway.charge(
                                amount=payment_request.total_net_fee,
                                reference=payment_request.claim_reference
                            )

                            if response.success:
                                payment.status = "completed"
                                payment.transaction_id = response.transaction_id

                                # Set idempotency key with TTL (24 hours)
                                redis.setex(
                                    f"payment:{payment_request.idempotency_key}",
                                    86400,
                                    "processed"
                                )

                                # SEND SUCCESS EVENT BACK
                                # =======================
                                self.queue.publish(
                                    message={
                                        "claim_id": payment_request.claim_id,
                                        "status": "payment_completed",
                                        "transaction_id": response.transaction_id
                                    },
                                    routing_key="claim.payment_completed"
                                )

                                message.ack()
                                logger.info(f"Payment processed: {payment_request.claim_id}")

                            else:
                                # Payment failed - retry or move to DLQ
                                raise PaymentProcessingError(response.error)

                        db.session.commit()

                    except PaymentProcessingError as e:
                        # RETRY LOGIC
                        # ===========
                        retry_count = message.headers.get("retry-count", 0)
                        max_retries = message.headers.get("max-retries", 3)

                        if retry_count < max_retries:
                            # Exponential backoff: 2^retry seconds
                            delay = 2 ** retry_count

                            message.headers["retry-count"] = retry_count + 1

                            # Publish to retry queue with delay
                            self.queue.publish_delayed(
                                message=message.body,
                                delay=delay,
                                routing_key="payment.process.retry",
                                headers=message.headers
                            )

                            message.ack()  # Remove from original queue
                            logger.warning(
                                f"Payment retry {retry_count + 1}/{max_retries} "
                                f"for claim {payment_request.claim_id}"
                            )

                        else:
                            # MAX RETRIES EXCEEDED - MOVE TO DLQ
                            # ===================================
                            self.queue.publish(
                                message=message.body,
                                routing_key="payment.process.dlq",
                                headers=message.headers
                            )

                            message.ack()

                            # SEND FAILURE EVENT
                            self.queue.publish(
                                message={
                                    "claim_id": payment_request.claim_id,
                                    "status": "payment_failed",
                                    "error": str(e)
                                },
                                routing_key="claim.payment_failed"
                            )

                            # Alert operations team
                            alerting.send_alert(
                                severity="high",
                                message=f"Payment DLQ: Claim {payment_request.claim_id}",
                                details=str(e)
                            )

                            logger.error(f"Payment moved to DLQ: {payment_request.claim_id}")

                    except Exception as e:
                        # Unexpected error - reject and requeue
                        message.reject(requeue=True)
                        logger.error(f"Unexpected error processing payment: {e}")

                # 4. CLAIM SERVICE LISTENS FOR STATUS UPDATES
                # ============================================
                @queue.consumer(queue="claim_updates")
                def handle_payment_status(message):
                    '''
                    Update claim status based on payment result.
                    '''
                    event = json.loads(message.body)

                    with db.transaction():
                        claim = db.query(Claim).filter(
                            Claim.id == event["claim_id"]
                        ).with_for_update().first()  # Lock row for update

                        if event["status"] == "payment_completed":
                            claim.status = "completed"
                            claim.payment_transaction_id = event["transaction_id"]

                        elif event["status"] == "payment_failed":
                            claim.status = "payment_failed"
                            claim.error_message = event["error"]

                        db.session.commit()
                        message.ack()

                # 5. SAGA PATTERN FOR ROLLBACK
                # =============================
                # If payment fails after multiple retries, compensate:

                def compensate_failed_payment(claim_id):
                    '''
                    Compensating transaction for failed payments.
                    '''
                    with db.transaction():
                        claim = db.query(Claim).get(claim_id)

                        # Reverse any side effects
                        claim.status = "payment_failed"

                        # Log for reconciliation
                        audit_log = AuditLog(
                            entity_type="claim",
                            entity_id=claim_id,
                            action="payment_compensation",
                            details="Payment failed after max retries"
                        )
                        db.session.add(audit_log)

                        # Notify customer service
                        notification_service.send(
                            recipient="customer_service@example.com",
                            subject=f"Manual review needed: Claim {claim_id}",
                            body="Payment processing failed. Please review."
                        )

                        db.session.commit()

                # 6. CIRCUIT BREAKER PATTERN
                # ===========================
                # Prevent cascading failures

                circuit_breaker = CircuitBreaker(
                    failure_threshold=5,
                    recovery_timeout=60,
                    expected_exception=PaymentServiceError
                )

                @circuit_breaker
                def call_payment_gateway(amount, reference):
                    '''
                    Call external payment gateway with circuit breaker.
                    '''
                    return payment_gateway.charge(amount, reference)

                # If circuit is open (too many failures):
                # - Don't call payment gateway
                # - Return cached response or fail fast
                # - After timeout, allow one request to test if service recovered

                # 7. MONITORING AND OBSERVABILITY
                # ================================

                # Metrics to track:
                metrics.increment("payment.requests.total")
                metrics.increment(f"payment.requests.{status}")
                metrics.histogram("payment.processing_time", processing_time)
                metrics.gauge("payment.queue.depth", queue_depth)

                # Distributed tracing:
                with tracer.start_span("process_payment") as span:
                    span.set_tag("claim_id", payment_request.claim_id)
                    span.set_tag("amount", payment_request.total_net_fee)

                # Structured logging:
                logger.info(
                    "Payment processed",
                    extra={
                        "claim_id": payment_request.claim_id,
                        "amount": payment_request.total_net_fee,
                        "status": "success",
                        "transaction_id": transaction_id,
                        "processing_time_ms": processing_time
                    }
                )

            except Exception as e:
                logger.error(f"Failed to send payment request: {e}")
                raise
            '''

        """
        # Actual implementation would go here
        # For now, just log
        logger.info(
            f"PSEUDO: Sending payment request for claim {payment_request.claim_id} "
            f"with net fee ${payment_request.total_net_fee}"
        )
