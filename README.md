# README.md

# CryptoSafe Manager

A secure, extensible password manager built with Python, featuring encrypted storage, audit logging, and a modular architecture designed for future enhancements.

## Project Vision
CryptoSafe Manager aims to provide a professional-grade, open-source password management solution with a focus on security, extensibility, and user experience. The project is structured across 8 development sprints:

| Sprint | Focus |
|--------|-------|
| **Sprint 1** | Secure Foundation (Encrypted DB, Modular Architecture, GUI Shell) |
| Sprint 2 | Master Password & Key Management |
| Sprint 3 | Strong Encryption (AES-GCM) |
| Sprint 4 | Clipboard Protection & Auto-clear |
| Sprint 5 | Audit Logging & Integrity Verification |
| Sprint 6 | Import/Export & Backup |
| Sprint 7 | Auto-lock & Session Management |
| Sprint 8 | Packaging & Distribution |

## Architecture
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ GUI Layer │────▶│ Event Bus │────▶│ Business Logic │
│ (Tkinter/PyQt) │◀────│ (pub/sub) │◀────│ (Core) │
└─────────────────┘ └─────────────────┘ └─────────────────┘
│ │ │
▼ ▼ ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Reusable │ │ State Manager │ │ Database │
│ Widgets │ │ (Session/Clip) │ │ (SQLite) │
└─────────────────┘ └─────────────────┘ └─────────────────┘

### Key Components
- **MVC Separation**: Clear separation between GUI, business logic, and data layers
- **Event-Driven**: Central event bus for loose coupling between components
- **Extensible Crypto**: Abstract encryption service with placeholder implementation
- **Future-Proof DB**: Database schema designed to support all planned features
- **Thread-Safe**: Connection pooling and thread-local storage for database operations

## Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/katarsis435/Passw_Manage.git
   cd PM
