# ADR-005: M-Pesa Daraja B2C Integration

**Status:** Accepted  
**Date:** 2026-03-01  
**Deciders:** Backend team

## Context

We must disburse farmer payments via M-Pesa (Safaricom's mobile money platform), the dominant payment channel in Kenya. The Daraja API provides B2C functionality but imposes strict rate limits, requires OAuth 2.0 token management, and uses asynchronous callback-based confirmation.

## Decision

We chose the Safaricom Daraja B2C API with:
- **OAuth 2.0** token management (tokens cached for their lifetime).
- **Chunked dispatch**: 50 transactions per batch with 30-second delays between chunks.
- **Blackout window**: No disbursements between 01:00–04:00 EAT.
- **Callback handling**: Separate endpoints for `Result` and `Timeout` callbacks with IP whitelist validation.
- **Idempotent processing**: Duplicate callback detection via `transaction_id` uniqueness.
- **Reconciliation**: Daily Celery task to check transaction status via `TransactionStatus` API.

## Alternatives Considered

- **M-Pesa Paybill (C2B):** Only handles incoming payments, not outgoing disbursements. Not suitable for farmer payments.
- **Bank transfer:** Fallback for farmers without M-Pesa. Implemented as CSV export (Equity/KCB/Generic formats) for manual bank upload.
- **Cash disbursement:** Implemented as PDF voucher generation for collection points without bank/M-Pesa access.

## Consequences

**Positive:**
- M-Pesa is the dominant payment channel in Kenya — 97% of farmers have access.
- B2C API supports bulk disbursement, reducing manual payment processing.
- Callback-based confirmation provides real-time status updates.
- Rate limiting (50 requests/minute) is respected via chunked dispatch with 30-second delays.

**Negative:**
- Daraja API has intermittent downtime — requires retry logic and reconciliation.
- B2C transactions can take up to 30 seconds to confirm (timeout callback).
- Callback URLs must be registered in the Daraja portal — cannot be changed dynamically.
- Sandbox environment differs from production — requires separate testing.
- IP whitelist for callbacks adds deployment complexity.
