# 已知问题：空值温度数据导致的 500 错误

## 问题概述

**问题类型**: 未处理空值（Null Pointer Exception）

当第三方天气数据源返回 `temperature: null` 时，WeatherService 在进行温度单位转换时会抛出 `TypeError`，导致 API 返回 500 Internal Server Error。

## 触发条件

1. 用户查询城市 "Springfield" 的天气
2. 第三方数据源中 Springfield 的 `temperature` 字段为 `null`（模拟气象站故障）
3. `WeatherService.get_weather()` 方法尝试处理这个数据

## 预期 vs. 实际行为

### 预期行为 ✅

- API 返回 200 OK
- 响应中包含可用的天气信息（湿度、天气状况等）
- 温度字段标记为 "unavailable" 或 `null`，并有友好提示

示例响应：
```json
{
  "city": "Springfield",
  "temperature_c": null,
  "temperature_f": null,
  "humidity": 55,
  "condition": "Sunny",
  "wind_speed_kmh": 8.3,
  "notice": "Temperature data temporarily unavailable"
}
```

### Actual Behavior ❌

- API returns 500 Internal Server Error
- Error message: `"Internal server error: unsupported operand type(s) for *: 'NoneType' and 'float'"`
- User cannot retrieve any weather information, even though other data is available

## Root Cause Analysis

### Affected Files and Code Location

**File**: `src/weather_service.py`  
**Class**: `WeatherService`  
**Method**: `get_weather()`  
**Problem Line**: Line 45

```python
# Line 45 - 🐛 BUG HERE
temperature_fahrenheit = self._celsius_to_fahrenheit(raw_data['temperature'])
```

### Detailed Explanation

1. **Line 45**: Directly calls `_celsius_to_fahrenheit()` without checking if `temperature` is `None`
2. **Lines 61-63**: `_celsius_to_fahrenheit()` method attempts mathematical operations on `None`

```python
def _celsius_to_fahrenheit(self, celsius: float) -> float:
    """Convert Celsius to Fahrenheit"""
    # 🐛 This will raise TypeError when celsius is None
    return (celsius * 9/5) + 32  # None * 9/5 -> TypeError
```

3. **Exception Propagation**: `TypeError` is caught by exception handling in `src/api.py`, returning a 500 error

## Reproduction Tests

The project includes the following automated tests to reproduce the issue:

### 1. Unit Test (tests/test_weather_service.py)

```python
def test_get_weather_with_null_temperature(self):
    """Verify Springfield query throws TypeError"""
    with pytest.raises(TypeError):
        result = self.weather_service.get_weather("Springfield")
```

**Status**: ✅ Passes (proves bug exists)

### 2. Integration Test (tests/test_api.py)

```python
def test_get_weather_springfield_should_succeed(self, client):
    """Verify Springfield should return 200 instead of 500"""
    response = client.get('/api/weather?city=Springfield')
    assert response.status_code == 200  # ❌ This assertion will fail
```

**Status**: ❌ Fails (shows expected vs. actual behavior mismatch)

### Run Tests

```powershell
# Run all tests to see failures
pytest -v

# Run specific tests only
pytest tests/test_weather_service.py::TestWeatherService::test_get_weather_with_null_temperature -v
pytest tests/test_api.py::TestWeatherAPI::test_get_weather_springfield_should_succeed -v
```

## Impact Scope

- **Severity**: Medium
- **Affected Users**: All users querying Springfield or any city with unavailable temperature data
- **Frequency**: Triggers on every query
- **Data Loss**: None, but available data (humidity, conditions) also cannot be retrieved

## Fix Approaches

### Approach 1: Handle at WeatherService Layer (Recommended) ✅

Add null check in the `get_weather()` method:

```python
def get_weather(self, city: str) -> Dict:
    raw_data = self.data_provider.fetch_weather_data(city)
    
    # Check if temperature is available
    if raw_data['temperature'] is not None:
        temperature_fahrenheit = self._celsius_to_fahrenheit(raw_data['temperature'])
    else:
        temperature_fahrenheit = None
    
    formatted_data = {
        'city': raw_data['city'],
        'temperature_c': raw_data['temperature'],
        'temperature_f': temperature_fahrenheit,
        'humidity': raw_data['humidity'],
        'condition': raw_data['condition'],
        'wind_speed_kmh': raw_data['wind_speed']
    }
    
    return formatted_data
```

### Approach 2: Handle in Conversion Function

Modify `_celsius_to_fahrenheit()` to handle `None`:

```python
def _celsius_to_fahrenheit(self, celsius: Optional[float]) -> Optional[float]:
    """Convert Celsius to Fahrenheit"""
    if celsius is None:
        return None
    return (celsius * 9/5) + 32
```

### Approach 3: Validate Data Provider Data (Defensive)

Standardize data format in `WeatherDataProvider.fetch_weather_data()` to ensure required field consistency.

## Verify Fix

After fixing, the following test should pass:

```powershell
pytest tests/test_api.py::TestWeatherAPI::test_get_weather_springfield_should_succeed -v
```

Expected result:
- Test passes ✅
- Springfield query returns 200
- Response contains `temperature_c: null` and `temperature_f: null`

## Related Files

- 🐛 **Problem Code**: `src/weather_service.py` (Line 45)
- 🧪 **Test Files**: `tests/test_weather_service.py`, `tests/test_api.py`
- 📊 **Test Data**: `data/mock_weather_responses.json` (Springfield entry)

## Notes

This is a typical case of missing "defensive programming". When handling external data, you should:

1. ✅ Validate input data
2. ✅ Handle null values and edge cases
3. ✅ Provide meaningful error messages
4. ✅ Return partial available data on partial failure

Fixing this issue will improve system robustness and user experience.
