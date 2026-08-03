# Security Policy

## Reporting a vulnerability

Do not open a public issue for vulnerabilities that expose files, execute commands, bypass upload restrictions, or leak OCR images/results. Use GitHub private vulnerability reporting or contact the maintainer privately.

Include affected version, operating system, reproduction steps, impact, and a minimal proof of concept without real private data.

## Privacy and deployment

Local OCR Studio is designed for local processing. Do not expose the default development server directly to the public internet. Bind to `127.0.0.1` unless you intentionally deploy behind authentication, TLS, upload limits, and a reverse proxy.

Never submit confidential images or real identifiers in public issues. Redact examples before sharing.
