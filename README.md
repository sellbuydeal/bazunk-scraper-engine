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

## AliExpress adapter (experimental, October 2026)

The service now includes authenticated endpoints:
- `GET /v1/aliexpress/search?q=wireless+headphones&page=1`
- `GET /v1/aliexpress/products/{numeric-id}`

Set `SCRAPER_API_TOKEN` to a strong secret in the scraper service. Requests must include `Authorization: Bearer <token>`. Product lookup extracts JSON-LD from public HTML; search discovers item IDs in search-page HTML, and may return empty titles/prices. **This is not yet a reliable catalogue search or tested production integration.** The adapter does not bypass login, CAPTCHA, anti-bot checks, or redirects.

Configure BOTH downstream servers:
- Bazunk marketplace API: `ALIEXPRESS_SCRAPER_URL=https://<scraper-service>`, `ALIEXPRESS_SCRAPER_TOKEN=<same-token>`.
- Bazunk Data API: same scraper URL/token, plus `ALIEXPRESS_PROVIDER_ENABLED=true` and `ALIEXPRESS_RESALE_LICENSE_CONFIRMED=true` only after validating the scope of your AliExpress authorization.

The marketplace admin uses the scraper when configured, otherwise its existing RapidAPI integration. Bazunk Data likewise prefers the scraper and can fall back to RapidAPI if scraper credentials are not configured. Never expose tokens to browsers.
