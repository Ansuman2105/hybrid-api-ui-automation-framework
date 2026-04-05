# 📺 STB Hybrid API + UI Automation Framework

A production-grade **Hybrid Automation Framework** for Set-Top Box (STB) systems integrating:

* 🔗 API Testing (pytest + requests)
* 📱 UI Automation (Appium - Android TV / STB)
* ⚙️ n8n Workflow Automation
* 📊 Real-time Streamlit Dashboard
* 🔄 Dynamic Device Handling (ADB)

---

## 🚀 Project Overview

This framework validates **end-to-end STB workflows**:

👉 CMS/API → STB UI → Dashboard → Notification

It ensures data consistency between backend services and the UI layer.

---

## 🏗️ Architecture

```text
n8n (Trigger / Scheduler)
        ↓
Webhook Server (Flask)
        ↓
Pytest Engine
   ↓              ↓
API Tests     UI Tests (Appium)
        ↓
results.json (Report Layer)
        ↓
Streamlit Dashboard
```

---

## 📂 Project Structure

```text
hybrid-api-ui-automation-framework/

├── api/               # API test modules
├── config/            # Environment & config files
├── dashboard/         # Streamlit dashboard UI
├── driver/            # Appium driver setup & management
├── n8n/               # n8n workflow configs
├── pages/             # Page objects (UI layer)
├── reports/           # Results.json + screenshots
├── tests/             # Test cases (API + UI flows)
├── utils/             # Logger, reporter, helpers

├── conftest.py        # Pytest fixtures & setup
├── pytest.ini         # Pytest configuration
├── requirements.txt   # Dependencies
├── docker-compose.yml # Container setup (optional)
├── run.bat            # Windows execution script
├── setup_windows.bat  # Setup script
├── Makefile           # Commands automation
├── README.md
```

---

## 🔥 Key Features

### ✅ Hybrid Testing (API + UI)

* Validates CMS/API data against STB UI
* End-to-end test coverage

---

### ✅ Dynamic Device Handling

* No hardcoded IPs
* Supports multiple STBs
* ADB-based detection

---

### ✅ Appium Integration

* UiAutomator2 driver
* Android TV / STB automation
* Page Object Model (POM)

---

### ✅ n8n Automation

* Trigger tests via webhook
* Email notifications
* CI/CD ready workflows

---

### ✅ Real-time Dashboard

* Live test metrics
* Pass/Fail trends
* Failure drill-down with screenshots
* Run filtering

---

### ✅ Scalable Framework

* Modular design
* Parallel execution support (pytest-xdist)
* Logging & reporting system

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Ansuman2105/hybrid-api-ui-automation-framework.git
cd hybrid-api-ui-automation-framework
```

---

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3️⃣ Start Appium Server

```bash
appium
```

---

### 4️⃣ Connect STB Device

```bash
adb connect <DEVICE_IP>:5555
adb devices
```

---

### 5️⃣ Run Tests

```bash
pytest tests/ -v
```

---

## 🔁 Run via n8n

### Webhook Endpoint

```http
POST /webhook/run-tests
```

### Sample Payload

```json
{
  "device_ip": "192.168.31.248",
  "markers": "smoke",
  "workers": 2
}
```

---

## 📊 Run Dashboard

```bash
streamlit run dashboard/dashboard.py
```

👉 Open: http://localhost:8501

---

## 🧪 Sample Test Flow

1. Fetch data from API
2. Launch STB application
3. Validate UI elements
4. Compare API vs UI data
5. Log result + capture screenshot

---

## 📸 Dashboard Capabilities

* 📊 Summary metrics (Total / Pass / Fail)
* 📈 Trend charts
* 📋 Test results table
* 🔍 Failure debugging
* 🎛 Filters (device, module, status)

---

## 🔐 Environment Variables

```bash
DEVICE_IP=192.168.31.248
DEVICE_PORT=5555
WEBHOOK_SECRET=your_secret
```
## 🛠️ Tech Stack

* Python
* Pytest
* Appium (UiAutomator2)
* Streamlit
* Flask
* n8n
* ADB

---

## 👨‍💻 Author

**Ansuman Nayak**
---

## ⭐ Support

If you found this useful, consider giving a ⭐ on GitHub!
