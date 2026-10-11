# Session History - FirearmsInventory

## Initial Architecture & Deployment (2026-10-11)
- Initialized dedicated FirearmsInventory service on port 8186 (`FirearmsInventory_8186` + `FirearmsInventory_api`).
- Configured data persistence with isolated `./data:/app/data` and `./uploads:/app/uploads` volumes.
- Setup Python 3.12 microservice backend with automatic 10-minute snapshot rolling backups and live code reloading.
- Integrated serial number masking toggle for discretion during display/sharing.
- Added multi-angle photo gallery, photo side-by-side comparison matrix, round counts & maintenance logs, and insurance replacement valuation reports.
