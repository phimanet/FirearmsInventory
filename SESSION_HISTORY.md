# Session History - FirearmsInventory

## Initial Architecture & Deployment (2026-10-11)
- Initialized dedicated FirearmsInventory service on port 8186 (`FirearmsInventory_8186` + `FirearmsInventory_api`).
- Configured data persistence with isolated `./data:/app/data` and `./uploads:/app/uploads` volumes.
- Setup Python 3.12 microservice backend with automatic 10-minute snapshot rolling backups and live code reloading.
- Integrated serial number masking toggle for discretion during display/sharing.
- Added multi-angle photo gallery, photo side-by-side comparison matrix, round counts & maintenance logs, and insurance replacement valuation reports.

## CCW Permit Compliance, Renewal Tracking & Gmail Alerts (2026-10-12)
- Added full California CCW permit compliance tracker specifically tailored for the San Diego County Sheriff's Department (SDSO).
- Added Gmail SMTP integration (`smtp.gmail.com:465`) sending responsive executive email alerts starting 120 days prior to expiration and recurring every 30 days.
- Implemented background milestone checker (`check_and_send_ccw_reminders`) and test email trigger (`POST /api/ccw/test-email`).
- Added sequential 3-step renewal milestone checklist:
  1. LiveScan fingerprinting (required before qualification class).
  2. CCW renewal class & live-fire shooting qualification.
  3. Uploading all documents and training certificates to the San Diego Sheriff (Permitium) at the critical 90-day mark before expiration.
- Added CCW permit indicators & weapon tagging:
  - Gold `🛡️ CCW` badge on cards for firearms listed on permit.
  - Spec detail indicator in popup specs grid.
  - Form checkbox toggle `🛡️ Listed on CCW Permit` when adding or editing firearms.
  - Filter bar chip `🛡️ On CCW Permit` to view all weapons authorized on the permit.
- Added comprehensive CCW management modal (`#ccwModal`) with expiration countdown, checklist tracking, and test email button.

## Alphabetical Sorting by Manufacturer & Sort Selector (2026-10-12)
- **Alphabetical Manufacturer Sorting (`server.py` & `index.html`)**:
  - Implemented automatic alphabetical sorting by Manufacturer (`make` A → Z), sub-sorted by Model (`model` A → Z).
  - Applied server-side in `handle_get_firearms()` so all API responses, scripts, and exports are sorted alphabetically.
  - Applied client-side in `fetchFirearms()` so master inventory arrays, Insurance Valuation reports, and Compare matrices inherit alphabetical Manufacturer ordering.
- **Dynamic Sort Selector Control (`index.html`)**:
  - Added responsive Sort dropdown alongside classification chips in the filter bar.
  - Supports sorting by:
    - `Manufacturer (A → Z)` *(Default)*
    - `Manufacturer (Z → A)`
    - `Model (A → Z)`
    - `Value (High to Low)`
    - `Round Count (High to Low)`
    - `Recently Updated`
  - Re-sorts filtered inventory live on change without page reloads.
- **Git Deployment Pipeline**:
  - Committed and pushed to `phimanet/FirearmsInventory` (`origin main`) for auto-deployment to `192.168.72.10:8186`.

