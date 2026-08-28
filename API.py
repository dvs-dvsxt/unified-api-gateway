"""
Unified API Gateway v3.0
Wraps all external APIs in /api/v3/ format
Supports precise city name matching (adcode.txt)
Server deployment version
"""

import json
import re
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ========== Configuration ==========
# Time API - using api.zxki.cn (simple and reliable)
TIME_API_URL = "https://api.zxki.cn/api/time"

# Weather API - sojson (uses citykey)
WEATHER_SOJSON_URL = "http://t.weather.sojson.com/api/weather/city/{}"

# Weather API - uapis.cn (general weather interface)
WEATHER_UAPIS_URL = "https://uapis.cn/api/v1/misc/weather"

# Phone number lookup API
PHONE_INFO_URL = "https://uapis.cn/api/v1/misc/phoneinfo"

# IP Geolocation APIs
IP_MYIP_URL = "https://uapis.cn/api/v1/network/myip"
IP_INFO_URL = "https://uapis.cn/api/v1/network/ipinfo"
IP_SB_URL = "https://api.ip.sb/geoip/{}"

# ========== City Code Mapping ==========
CITY_CODE_MAP = {}

def load_city_codes():
    """Load city code mapping from adcode.txt"""
    global CITY_CODE_MAP
    try:
        with open('adcode.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    code, city = line.split('=', 1)
                    city_name = city.strip()
                    code_value = code.strip()
                    CITY_CODE_MAP[city_name] = code_value
        print(f"Loaded {len(CITY_CODE_MAP)} city codes")
    except FileNotFoundError:
        print("Error: adcode.txt not found, city lookup unavailable")
        raise SystemExit("Missing adcode.txt file")
    except Exception as e:
        print(f"Error loading adcode.txt: {e}")
        raise

def search_city_code(query):
    """
    Search for city code
    1. Remove city/county/district suffixes and search
    2. If multiple matches found, search again with suffix
    3. If still multiple matches, return error
    4. Single-character search not supported
    """
    if not query or len(query.strip()) == 0:
        return None, "City name cannot be empty"
    
    query = query.strip()
    
    # Single-character search not supported
    if len(query) <= 1:
        return None, "Single-character search not supported, please enter full city name"
    
    # Remove suffix
    clean_query = re.sub(r'[市县区州]$', '', query)
    
    # First search: exact match on name without suffix
    if clean_query in CITY_CODE_MAP:
        return CITY_CODE_MAP[clean_query], None
    
    # If suffix was removed and original query exists, try original
    if clean_query != query and query in CITY_CODE_MAP:
        return CITY_CODE_MAP[query], None
    
    # Search for partial matches
    matches = {}
    for city, code in CITY_CODE_MAP.items():
        # City name equals query without suffix
        if city == clean_query:
            matches[city] = code
        # Query without suffix is a prefix of city name
        elif city.startswith(clean_query):
            # Require city to be at least 1 char longer than query to avoid vague matches
            if len(city) - len(clean_query) >= 1:
                matches[city] = code
    
    # If first search found results
    if matches:
        if len(matches) == 1:
            city, code = list(matches.items())[0]
            return code, None
        else:
            # Multiple results, try adding original suffix back
            if clean_query != query:
                # Search for city names containing original query
                refined_matches = {}
                for city, code in CITY_CODE_MAP.items():
                    if query in city:
                        refined_matches[city] = code
                
                if len(refined_matches) == 1:
                    city, code = list(refined_matches.items())[0]
                    return code, None
                elif len(refined_matches) > 1:
                    cities = list(refined_matches.keys())
                    return None, f"Multiple cities found: {', '.join(cities)}, please provide a more specific city name"
                else:
                    cities = list(matches.keys())
                    return None, f"Multiple cities found: {', '.join(cities)}, please provide a more specific city name"
            else:
                cities = list(matches.keys())
                return None, f"Multiple cities found: {', '.join(cities)}, please provide a more specific city name"
    
    # No match found
    return None, f"City '{query}' not found"

# ========== Generic Request Function ==========
def safe_request(url, method='GET', params=None, timeout=10):
    """Safe HTTP request handler"""
    try:
        if method == 'GET':
            resp = requests.get(url, params=params, timeout=timeout)
        elif method == 'POST':
            resp = requests.post(url, json=params, timeout=timeout)
        else:
            return None
        
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return {"error": "not_found", "message": "Resource not found"}
        else:
            return {"error": f"HTTP {resp.status_code}", "message": resp.text}
    except requests.exceptions.Timeout:
        return {"error": "timeout", "message": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "connection_error", "message": "Connection failed"}
    except requests.RequestException as e:
        return {"error": "request_failed", "message": str(e)}
    except json.JSONDecodeError:
        return {"error": "json_decode_failed", "message": "Response parsing failed"}

# ========== Response Formatting ==========
def success_response(data, message="Success"):
    """Unified success response format"""
    return jsonify({
        "code": 200,
        "message": message,
        "data": data
    })

def error_response(code, message, http_status=400):
    """Unified error response format"""
    return jsonify({
        "code": code,
        "message": message
    }), http_status

# ========== Helper: Get Local Time ==========
def get_local_time():
    """Get local time as fallback when external API fails"""
    now = datetime.now()
    weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekdays_short = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return {
        "timestamp": str(int(now.timestamp())),
        "timestamp_ms": str(int(now.timestamp() * 1000)),
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date_cn": now.strftime("%Y年%m月%d日"),
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M:%S"),
        "week_num": str(now.isocalendar()[1]),
        "week_cn": weekdays_cn[now.weekday()],
        "week_short_cn": weekdays_short[now.weekday()],
        "week_en": weekdays_en[now.weekday()]
    }

# ========== API Routes ==========

@app.route('/api/v3/time', methods=['GET'])
def get_time():
    """
    Get current time
    GET /api/v3/time
    """
    result = safe_request(TIME_API_URL)
    
    if result and "date" in result and "time" in result:
        try:
            date_str = result.get("date", "")
            time_str = result.get("time", "")
            week_str = result.get("week", "")
            
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y年%m月%d日 %H:%M:%S")
                timestamp = int(dt.timestamp())
                timestamp_ms = int(dt.timestamp() * 1000)
                datetime_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                now = datetime.now()
                try:
                    year = int(re.search(r'(\d{4})年', date_str).group(1))
                    month = int(re.search(r'年(\d{2})月', date_str).group(1))
                    day = int(re.search(r'月(\d{2})日', date_str).group(1))
                    hour, minute, second = map(int, time_str.split(':'))
                    dt = datetime(year, month, day, hour, minute, second)
                    timestamp = int(dt.timestamp())
                    timestamp_ms = int(dt.timestamp() * 1000)
                    datetime_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    now = datetime.now()
                    timestamp = int(now.timestamp())
                    timestamp_ms = int(now.timestamp() * 1000)
                    datetime_iso = now.strftime("%Y-%m-%d %H:%M:%S")
            
            weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekdays_short = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            weekday_index = 0
            if week_str in weekdays_cn:
                weekday_index = weekdays_cn.index(week_str)
            else:
                try:
                    weekday_index = dt.weekday()
                except:
                    weekday_index = datetime.now().weekday()
            
            formatted_data = {
                "timestamp": str(timestamp),
                "timestamp_ms": str(timestamp_ms),
                "datetime": datetime_iso,
                "date_cn": date_str,
                "date": date_str,
                "time": time_str,
                "week_num": str(weekday_index + 1),
                "week_cn": weekdays_cn[weekday_index],
                "week_short_cn": weekdays_short[weekday_index],
                "week_en": weekdays_en[weekday_index]
            }
            
            return success_response(formatted_data, "Time retrieved successfully")
            
        except Exception as e:
            print(f"Error parsing time response: {e}")
            return success_response(get_local_time(), "Time retrieved from local system (fallback)")
    
    print("Warning: Time API unavailable, using local time")
    return success_response(get_local_time(), "Time retrieved from local system")

@app.route('/api/v3/weather/sojson', methods=['GET'])
def get_weather_sojson():
    """
    Get weather (sojson API, uses citykey)
    GET /api/v3/weather/sojson?city=Linyi
    """
    city_name = request.args.get('city', '').strip()
    
    if not city_name:
        return error_response(400, "Please provide city name parameter ?city=city_name")
    
    city_code, error_msg = search_city_code(city_name)
    
    if error_msg:
        return error_response(404, error_msg)
    
    url = WEATHER_SOJSON_URL.format(city_code)
    result = safe_request(url)
    
    if result and result.get("status") == 200:
        return success_response(result, "Weather retrieved successfully")
    elif result and "error" in result:
        return error_response(500, result.get("message", "Weather service error"), 500)
    else:
        return error_response(500, "Weather service temporarily unavailable", 500)

@app.route('/api/v3/weather', methods=['GET'])
def get_weather_uapis():
    """
    Get weather (uapis.cn general weather API)
    GET /api/v3/weather?city=Beijing
    GET /api/v3/weather?adcode=110000
    GET /api/v3/weather  (auto IP geolocation)
    """
    params = {}
    
    for key in ['city', 'adcode', 'extended', 'forecast', 'hourly', 'minutely', 'indices', 'lang']:
        value = request.args.get(key)
        if value is not None:
            if key in ['extended', 'forecast', 'hourly', 'minutely', 'indices']:
                params[key] = value.lower() == 'true'
            else:
                params[key] = value
    
    result = safe_request(WEATHER_UAPIS_URL, params=params)
    
    if result:
        if "error" in result:
            return error_response(500, result.get("message", "Weather service error"), 500)
        return success_response(result, "Weather retrieved successfully")
    else:
        return error_response(500, "Weather service temporarily unavailable", 500)

@app.route('/api/v3/phone', methods=['GET'])
def get_phone_info():
    """
    Query phone number location
    GET /api/v3/phone?phone=13800138000
    """
    phone = request.args.get('phone', '').strip()
    
    if not phone:
        return error_response(400, "Please provide phone number parameter ?phone=phone_number")
    
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return error_response(400, "Invalid phone number format, please enter an 11-digit Chinese mainland phone number")
    
    result = safe_request(PHONE_INFO_URL, params={"phone": phone})
    
    if result:
        if "error" in result:
            return error_response(400, result.get("message", "Query failed"), 400)
        return success_response(result, "Phone number lookup successful")
    else:
        return error_response(500, "Phone number lookup service temporarily unavailable", 500)

# ========== IP Geolocation Routes ==========

@app.route('/api/v3/ip/me', methods=['GET'])
def get_my_ip():
    """
    Get current client's public IP address
    GET /api/v3/ip/me
    GET /api/v3/ip/me?source=commercial (returns more detailed info)
    """
    source = request.args.get('source', '')
    params = {}
    if source:
        params['source'] = source
    
    result = safe_request(IP_MYIP_URL, params=params if params else None)
    
    if result and "ip" in result:
        # Format the response
        formatted_data = {
            "ip": result.get("ip", ""),
            "region": result.get("region", ""),
            "isp": result.get("isp", ""),
            "llc": result.get("llc", ""),
            "asn": result.get("asn", ""),
            "latitude": result.get("latitude", ""),
            "longitude": result.get("longitude", ""),
            "beginip": result.get("beginip", ""),
            "endip": result.get("endip", "")
        }
        # Add commercial fields if available
        if "district" in result:
            formatted_data["district"] = result.get("district", "")
        if "time_zone" in result:
            formatted_data["time_zone"] = result.get("time_zone", "")
        
        return success_response(formatted_data, "IP geolocation successful")
    elif result and "error" in result:
        return error_response(500, result.get("message", "IP service error"), 500)
    else:
        return error_response(500, "IP geolocation service temporarily unavailable", 500)

@app.route('/api/v3/ip', methods=['GET'])
def get_ip_info():
    """
    Query IP information
    GET /api/v3/ip?ip=8.8.8.8
    GET /api/v3/ip?ip=8.8.8.8&source=commercial
    GET /api/v3/ip  (auto-detect current IP)
    """
    ip = request.args.get('ip', '').strip()
    source = request.args.get('source', '')
    
    # If no IP provided, use myip endpoint
    if not ip:
        # Use IP_SB as fallback for auto-detection
        try:
            resp = requests.get("https://api.ip.sb/geoip", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                formatted_data = {
                    "ip": data.get("ip", ""),
                    "region": f"{data.get('country', '')} {data.get('region', '')} {data.get('city', '')}".strip(),
                    "isp": data.get("isp", ""),
                    "organization": data.get("organization", ""),
                    "asn": data.get("asn", ""),
                    "latitude": data.get("latitude", ""),
                    "longitude": data.get("longitude", ""),
                    "country": data.get("country", ""),
                    "country_code": data.get("country_code", ""),
                    "region_code": data.get("region_code", ""),
                    "city": data.get("city", "")
                }
                return success_response(formatted_data, "IP geolocation successful")
        except:
            pass
        
        # Fallback to uapis myip
        result = safe_request(IP_MYIP_URL)
        if result and "ip" in result:
            formatted_data = {
                "ip": result.get("ip", ""),
                "region": result.get("region", ""),
                "isp": result.get("isp", ""),
                "llc": result.get("llc", ""),
                "asn": result.get("asn", ""),
                "latitude": result.get("latitude", ""),
                "longitude": result.get("longitude", ""),
                "beginip": result.get("beginip", ""),
                "endip": result.get("endip", "")
            }
            return success_response(formatted_data, "IP geolocation successful")
        return error_response(500, "Unable to determine IP address", 500)
    
    # Query specific IP
    # Try uapis first
    params = {"ip": ip}
    if source:
        params["source"] = source
    
    result = safe_request(IP_INFO_URL, params=params)
    
    if result and "ip" in result:
        formatted_data = {
            "ip": result.get("ip", ""),
            "region": result.get("region", ""),
            "isp": result.get("isp", ""),
            "llc": result.get("llc", ""),
            "asn": result.get("asn", ""),
            "latitude": result.get("latitude", ""),
            "longitude": result.get("longitude", ""),
            "beginip": result.get("beginip", ""),
            "endip": result.get("endip", "")
        }
        return success_response(formatted_data, "IP geolocation successful")
    
    # Fallback to ip.sb
    try:
        url = IP_SB_URL.format(ip)
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            formatted_data = {
                "ip": data.get("ip", ip),
                "region": f"{data.get('country', '')} {data.get('region', '')} {data.get('city', '')}".strip(),
                "isp": data.get("isp", ""),
                "organization": data.get("organization", ""),
                "asn": data.get("asn", ""),
                "latitude": data.get("latitude", ""),
                "longitude": data.get("longitude", ""),
                "country": data.get("country", ""),
                "country_code": data.get("country_code", ""),
                "region_code": data.get("region_code", ""),
                "city": data.get("city", "")
            }
            return success_response(formatted_data, "IP geolocation successful")
    except:
        pass
    
    return error_response(500, "IP geolocation service temporarily unavailable", 500)

@app.route('/api/v3/ip/advanced', methods=['GET'])
def get_ip_advanced():
    """
    Advanced IP query with commercial data source
    GET /api/v3/ip/advanced?ip=8.8.8.8
    """
    ip = request.args.get('ip', '').strip()
    source = request.args.get('source', 'commercial')
    
    if not ip:
        return error_response(400, "Please provide IP address parameter ?ip=8.8.8.8")
    
    params = {"ip": ip, "source": source}
    result = safe_request(IP_INFO_URL, params=params)
    
    if result and "ip" in result:
        return success_response(result, "IP geolocation successful")
    elif result and "error" in result:
        return error_response(500, result.get("message", "IP service error"), 500)
    else:
        return error_response(500, "IP geolocation service temporarily unavailable", 500)

@app.route('/api/v3', methods=['GET'])
def api_index():
    """API directory"""
    return jsonify({
        "code": 200,
        "message": "Unified API Gateway v3.0",
        "version": "3.0.0",
        "endpoints": {
            "time": {
                "path": "/api/v3/time",
                "method": "GET",
                "description": "Get current time",
                "example": "/api/v3/time"
            },
            "weather_sojson": {
                "path": "/api/v3/weather/sojson",
                "method": "GET",
                "description": "Get weather (sojson, uses citykey)",
                "params": {"city": "City name"},
                "example": "/api/v3/weather/sojson?city=Linyi"
            },
            "weather": {
                "path": "/api/v3/weather",
                "method": "GET",
                "description": "Get weather (uapis.cn general API)",
                "params": {"city": "City name", "forecast": "Enable forecast", "extended": "Enable extended fields"},
                "example": "/api/v3/weather?city=Beijing&forecast=true"
            },
            "phone": {
                "path": "/api/v3/phone",
                "method": "GET",
                "description": "Query phone number location",
                "params": {"phone": "Phone number"},
                "example": "/api/v3/phone?phone=13800138000"
            },
            "ip_me": {
                "path": "/api/v3/ip/me",
                "method": "GET",
                "description": "Get your public IP address",
                "params": {"source": "commercial (optional)"},
                "example": "/api/v3/ip/me"
            },
            "ip": {
                "path": "/api/v3/ip",
                "method": "GET",
                "description": "Query IP information",
                "params": {"ip": "IP address (optional)", "source": "commercial (optional)"},
                "example": "/api/v3/ip?ip=8.8.8.8"
            },
            "ip_advanced": {
                "path": "/api/v3/ip/advanced",
                "method": "GET",
                "description": "Advanced IP query with commercial data",
                "params": {"ip": "IP address", "source": "commercial (default)"},
                "example": "/api/v3/ip/advanced?ip=8.8.8.8"
            }
        }
    })

# ========== Error Handlers ==========
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "code": 404,
        "message": "Endpoint not found, visit /api/v3 to see available endpoints"
    }), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "code": 500,
        "message": "Internal server error"
    }), 500

# ========== Startup ==========
if __name__ == '__main__':
    load_city_codes()
    app.run(host='0.0.0.0', port=880, debug=False)
