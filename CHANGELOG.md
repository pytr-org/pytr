# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `timeout` and `debug` parameters on the `TradeRepublic` client for configurable request timeouts and verbose debug logging.
- Session serialization and deserialization methods (`serialize_session` / `resume_session`) to persist and restore authentication state without manual cookie handling.
- New error subclasses (`OtpRequired`, `SessionExpired`, `NetworkError`) under a unified `PytrError` taxonomy, each indicating retryability and recommended backoff.
- `InstrumentMetadata` model and `client.instrument_details(isin)` for one-call retrieval of instrument name, ticker, sector, country, and other metadata.
- Async backoff generator (`backoff_intervals`) and retry helper (`retry_async`) to standardize exponential-jitter retry logic across client operations.

### Changed
- Guard optional dependencies (`coloredlogs`, `requests`, `packaging`) in `pytr/utils.py` to allow minimal installs and avoid import errors when features aren’t needed.

### Removed
- Removed direct export of `TradeRepublicApi` from the package root to promote the single `TradeRepublic` entry point.

### Added
- Sanitizer module (`pytr.sanitize`) leveraging DataSON's `RedactionEngine` to scrub sensitive fields (IBAN, ISIN, currency amounts, phone, PIN) and optionally produce an audit trail.

## [0.4.3] - 2025-08-15
- Initial release matching v0.4.3 on PyPI
