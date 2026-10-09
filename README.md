# Bazunk Scraper Engine (experimental)

Standalone test service for authorised product-data retrieval and normalisation. This repository is intentionally isolated from the live Bazunk marketplace and Data Platform.

## Status

**Scaffold only.** No live Amazon, AliExpress, Mercado Livre, Shein or Shopee scraping has been implemented or validated here. Existing Bazunk RapidAPI importers remain unchanged.

## Planned interface

- `GET /health` for service health
- `POST /v1/preview` for a permitted product URL, returning a normalised product or an explicit unsupported-provider error
- Future provider adapters may be integrated individually after verifying permissions, licence terms, security and real-world reliability

## Security principles

Use API authentication before deployment, restrict allowed hosts and URL schemes, block requests to internal networks, impose request limits, never commit account sessions or credentials, and do not bypass CAPTCHA or other access restrictions.

The previously uploaded five-platform scraper is an evaluation reference, **not yet imported into this repository**.
