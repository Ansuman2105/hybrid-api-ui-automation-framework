# 📺 STB Launcher Hybrid Automation Framework

> Production-ready Python hybrid automation framework combining **Appium UI testing**, **CMS REST API automation**, and a **real-time Streamlit dashboard**.

---

## 🏗 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    Test Layer (pytest)                           │
│   test_tile_from_cms.py  │  test_launcher_ui.py  │  test_cms_api│
└────────────┬─────────────┴───────────┬───────────┴──────────────┘
             │                         │
   ┌─────────▼──────────┐   ┌──────────▼──────────┐
   │   API Layer         │   │   UI Layer (POM)     │
   │  cms_service.py     │   │  launcher_page.py    │
   │  api_client.py      │   │  base_page.py        │
   └─────────┬───────────┘   └──────────┬──────────┘
             │                          │
   ┌─────────▼───────────┐   ┌──────────▼──────────┐
   │  requests.Session   │   │  Appium WebDriver    │
   │  (CMS REST API)     │   │  (UiAutomator2/STB)  │
   └─────────────────────┘   └─────────────────────┘
             │                          │
   ┌─────────▼──────────────────────────▼──────────┐
   │             Utilities                          │
   │  config_loader │ reporter │ logger │ screenshot│
   └────────────────────────────────────────────────┘
             │
   ┌─────────▼──────────────────────────────────────┐
   │       reports/results.json                     │
   └─────────┬──────────────────────────────────────┘
             │
   ┌─────────▼──────────────────────────────────────┐
   │    Streamlit Dashboard (real-time)             │
   │    dashboard/dashboard.py                      │
   └────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
stb_framework/
│
├── config/
│   ├── config.json            # All non-secret config (device, API, timeouts)
│   ├── config_loader.py       # Singleton config + env-var override loader
│   └── .env.example           # Template — copy to .env and fill secrets
│
├── driver/
│   └── driver_manager.py      # Appium driver factory + ADB TCP/IP setup
│
├── pages/
│   ├── base_page.py           # Abstract POM base (waits, DPAD, screenshots)
│   └── launcher_page.py       # STB Launcher POM (tile visibility, nav)
│
├── api/
│   ├── api_client.py          # Base HTTP client (retry, auth, error handling)
│   └── cms_service.py         # CMS tile CRUD operations (create/get/delete)
│
├── tests/
│   ├── test_tile_from_cms.py  # 🌟 Hybrid E2E tests (API + UI)
│   ├── test_launcher_ui.py    # UI-only launcher tests
│   └── test_cms_api.py        # Pure API tests (no Appium)
│
├── utils/
│   ├── logger.py              # Colourised + rotating file logger
│   ├── reporter.py            # Thread-safe JSON results writer
│   ├── screenshot.py          # Appium screenshot capture
│   └── retry.py               # Configurable retry decorator
│
├── dashboard/
│   └── dashboard.py           # Streamlit real-time dashboard
│
├── reports/
│   ├── results.json           # Auto-generated test results
│   └── screenshots/           # Failure screenshots (auto-created)
│
├── logs/
│   └── automation.log         # Rotating log file (auto-created)
│
├── conftest.py                # Pytest fixtures (driver, cms, reporting)
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python dependencies
└── Makefile                   # Developer shortcuts
```

---

## 🚀 Quick Start

### 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Appium | 2.x | `npm install -g appium` |
| UiAutomator2 driver | latest | `appium driver install uiautomator2` |
| Android SDK / adb | latest | Android Studio or SDK tools |

### 2. Install Python dependencies

```bash
cd stb_framework
pip install -r requirements.txt
```

### 3. Configure secrets

```bash
cp config/.env.example config/.env
# Edit config/.env and set CMS_API_KEY, CMS_USERNAME, CMS_PASSWORD
```

### 4. Update config.json

Edit `config/config.json` and set:
- `device.device_ip` — your STB's IP address
- `device.app_package` — your launcher's package name
- `device.app_activity` — your launcher's main activity
- `api.base_url` — your CMS API base URL

### 5. Start Appium

```bash
appium --port 4723 --log-level info
```

### 6. Connect STB via ADB

```bash
adb connect 192.168.1.100:5555
adb devices   # verify device appears
```

---

## 🧪 Running Tests

### All tests
```bash
pytest
# or
make test
```

### By marker / test type
```bash
# Fast smoke tests
pytest -m smoke
make test-smoke

# API-only (no device needed)
pytest -m api
make test-api

# UI-only
pytest -m ui
make test-ui

# Full hybrid E2E
pytest -m hybrid
make test-hybrid
```

### Parallel execution (pytest-xdist)
```bash
pytest -n 2           # 2 workers
pytest -n auto        # auto-detect CPU count
make test-parallel
```

### With retries on flaky tests
```bash
pytest --reruns 3 --reruns-delay 2
make test-rerun
```

### Specific test file or function
```bash
pytest tests/test_tile_from_cms.py -v
pytest tests/test_tile_from_cms.py::TestTileFromCMS::test_tile_from_cms -v
```

### Override device at runtime
```bash
pytest --device-ip=192.168.1.200 --device-port=5555 -v
```

---

## 📊 Streamlit Dashboard

```bash
streamlit run dashboard/dashboard.py
# or
make dashboard
```

Open: **http://localhost:8501**

### Dashboard Features

| Feature | Description |
|---------|-------------|
| 📊 KPI Metrics | Total / Passed / Failed / Error counts + pass % |
| 📈 Bar Chart | Test results per module (stacked) |
| 🥧 Pie Chart | Status distribution |
| ⏱ Timeline | Test duration scatter over time |
| 📋 Results Table | Colour-coded, filterable, sortable |
| 🔍 Failure Drill-down | Expandable error messages + screenshots |
| 🔄 Auto-refresh | Configurable 2–60 second interval |
| 🎛 Sidebar Filters | Filter by status, module, device, tag |

---

## 📄 Sample results.json

```json
[
  {
    "test_name": "tests/test_tile_from_cms.py::TestTileFromCMS::test_tile_from_cms",
    "status": "PASS",
    "duration_sec": 14.832,
    "timestamp": "2025-01-15T09:12:03.441+00:00",
    "device": "STB_DEVICE_001",
    "screenshot": null,
    "error_msg": null,
    "tags": ["hybrid", "smoke"]
  },
  {
    "test_name": "tests/test_tile_from_cms.py::TestTileFromCMS::test_deleted_tile_not_on_launcher",
    "status": "FAIL",
    "duration_sec": 22.104,
    "timestamp": "2025-01-15T09:12:53.117+00:00",
    "device": "STB_DEVICE_001",
    "screenshot": "reports/screenshots/test_deleted_tile__20250115_091253.png",
    "error_msg": "AssertionError: Tile still visible after CMS deletion.",
    "tags": ["hybrid", "regression"]
  }
]
```

---

## ⚙️ Configuration Reference

### config.json key sections

| Section | Key | Description |
|---------|-----|-------------|
| `appium` | `server_url` | Appium server endpoint |
| `device` | `device_ip` | STB IP address |
| `device` | `app_package` | Android package name |
| `device` | `uiautomator2_server_install_timeout` | STB cold-boot tolerance (ms) |
| `api` | `base_url` | CMS REST API base URL |
| `api` | `retry_attempts` | HTTP retry count |
| `execution` | `screenshot_on_failure` | Auto-screenshot on FAIL |
| `reporting` | `results_file` | Path to results.json |

### Environment variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `CMS_API_KEY` | ✅ | CMS Bearer token |
| `CMS_USERNAME` | Optional | CMS username |
| `CMS_PASSWORD` | Optional | CMS password |
| `APPIUM_SERVER_URL` | Optional | Override Appium URL |
| `STB_DEVICE_IP` | Optional | Override device IP |

---

## 🔧 Extending the Framework

### Add a new page object
```python
# pages/settings_page.py
from pages.base_page import BasePage

class SettingsPage(BasePage):
    _LOC_SETTINGS_ROOT = (AppiumBy.ID, "com.stb.launcher:id/settings_root")

    def open_network_settings(self):
        self.navigate("right", "right", "enter")
```

### Add a new API service
```python
# api/epg_service.py
from api.api_client import APIClient

class EPGService:
    def get_schedule(self, channel_id: str) -> dict:
        return self._client.get(f"/epg/{channel_id}").json()
```

### Add a new test
```python
# tests/test_settings.py
@pytest.mark.ui
def test_network_settings_accessible(launcher, stb_driver):
    from pages.settings_page import SettingsPage
    settings = SettingsPage(stb_driver, test_name="test_network_settings")
    # ... navigate and assert
```

---

## 🏭 CI/CD Integration

### GitHub Actions example

```yaml
name: STB Automation
on: [push, schedule]

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      CMS_API_KEY: ${{ secrets.CMS_API_KEY }}
      STB_DEVICE_IP: ${{ vars.STB_DEVICE_IP }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest -m api -v          # API tests (no device)
      - uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: reports/
```

---

## 📐 Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Thread-local Appium driver** | Safe for pytest-xdist parallel workers without connection sharing |
| **Append-safe JSON reporter** | No database dependency; dashboard reads the same file |
| **Retry decorator (tenacity)** | Centralised retry logic reusable across API + UI layers |
| **ADB TCP/IP connect helper** | Most STBs are headless — USB isn't practical in CI/CD |
| **Page Object + DPAD keycodes** | Decouples test logic from Android KeyEvent details |
| **conftest auto-use fixture** | Zero-boilerplate result recording — tests don't need to import reporter |

---

## 📜 License

Internal use — STB Platform QA Team.
