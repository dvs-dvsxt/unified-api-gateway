# 🌐 Unified API Gateway

> A unified API gateway providing **time, weather, phone number lookup, and IP geolocation** services via a consistent `/api/v3/` interface.

The **Unified API Gateway** wraps multiple external APIs behind a clean, unified `/api/v3/` REST interface. It provides current time, weather (by city / adcode / auto-IP), phone number location, and IP geolocation — all with consistent response formatting and graceful fallbacks.

---

## ✨ Features

| Endpoint | Description |
|----------|-------------|
| 🕐 **Time** | Get current time with timestamp / datetime / Chinese & English weekday |
| 🌤️ **Weather** | Weather by city name / adcode / auto-IP (sojson + uapis.cn dual source) |
| 📱 **Phone Lookup** | Query Chinese mainland phone number location & carrier |
| 🌍 **IP Geolocation** | Query IP info / your public IP / advanced commercial data |
| 🎯 **Precise City Matching** | Smart city name → adcode matching (from `adcode.txt`) |
| ⚡ **Graceful Fallback** | Automatic fallback when external APIs fail |
| 📦 **Unified Format** | Consistent `{code, message, data}` response structure |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- `flask`, `requests`

### Install & Run

```bash
# Install dependencies
pip install flask requests

# Run the gateway (loads adcode.txt, listens on port 880)
python API.py
```

### Verify

```bash
# API directory / index
curl http://api.dvssvc.site/api/v3

# Current time
curl http://api.dvssvc.site/api/v3/time

# Weather by city
curl "http://api.dvssvc.site/api/v3/weather?city=Beijing"

# Weather by adcode
curl "http://api.dvssvc.site/api/v3/weather?adcode=110000"

# Phone number lookup
curl "http://api.dvssvc.site/api/v3/phone?phone=13800138000"

# Your public IP
curl "http://api.dvssvc.site/api/v3/ip/me"

# IP geolocation
curl "http://api.dvssvc.site/api/v3/ip?ip=8.8.8.8"
```

---

## 🔌 API Endpoints

### GET `/api/v3`
API directory / index — lists all available endpoints.

### GET `/api/v3/time`
Get current time.
- **Params**: none
- **Response**: timestamp, datetime, date (CN), time, week (CN/EN)

### GET `/api/v3/weather/sojson`
Get weather (sojson API, uses citykey).
- **Params**: `city` (city name, e.g. `Linyi`)

### GET `/api/v3/weather`
Get weather (uapis.cn general weather API).
- **Params**:
  - `city` — city name
  - `adcode` — administrative region code
  - `forecast` / `extended` / `hourly` / `minutely` / `indices` — booleans
  - `lang` — language
- **Note**: with no params, auto-detects by IP

### GET `/api/v3/phone`
Query phone number location.
- **Params**: `phone` — 11-digit Chinese mainland mobile number (validated `^1[3-9]\d{9}$`)

### GET `/api/v3/ip/me`
Get your public IP address.
- **Params**: `source=commercial` (optional, returns more detail)

### GET `/api/v3/ip`
Query IP information.
- **Params**: `ip` (IP address, optional — auto-detects if omitted), `source=commercial` (optional)

### GET `/api/v3/ip/advanced`
Advanced IP query with commercial data source.
- **Params**: `ip` (required), `source` (default `commercial`)

---

## 📦 Response Format

**Success:**
```json
{
  "code": 200,
  "message": "Success",
  "data": { }
}
```

**Error:**
```json
{
  "code": 404,
  "message": "Error description"
}
```

---

## 🗂️ Project Structure

```
Unified-API-Gateway/
├── API.py        # Flask API gateway (main program)
├── adcode.txt    # City name → adcode mapping data
└── README.md     # This document
```

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- Time API: [api.zxki.cn](https://api.zxki.cn)
- Weather APIs: [sojson](http://t.weather.sojson.com), [uapis.cn](https://uapis.cn)
- Phone / IP APIs: [uapis.cn](https://uapis.cn), [ip.sb](https://ip.sb)
