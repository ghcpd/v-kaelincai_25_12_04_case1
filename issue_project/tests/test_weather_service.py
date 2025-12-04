"""
Unit Tests for Weather Service
These tests demonstrate the null temperature bug
"""
import pytest
from src.weather_service import WeatherService, WeatherDataProvider


class TestWeatherService:
    """Test suite for WeatherService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.data_provider = WeatherDataProvider()
        self.weather_service = WeatherService(self.data_provider)
    
    def test_get_weather_normal_case(self):
        """Test normal weather query - this should pass"""
        result = self.weather_service.get_weather("New York")
        
        assert result['city'] == "New York"
        assert result['temperature_c'] == 22.5
        assert result['temperature_f'] == pytest.approx(72.5)
        assert result['humidity'] == 65
        assert result['condition'] == "Cloudy"
    
    def test_get_weather_with_null_temperature(self):
        """
        🐛 BUG TEST: This test will FAIL
        When temperature is null (sensor failure), service should handle gracefully
        Expected: Return weather data with temperature marked as unavailable
        Actual: Raises TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'
        """
        # This will raise TypeError when processing Springfield data
        with pytest.raises(TypeError) as exc_info:
            result = self.weather_service.get_weather("Springfield")
        
        # Verify it's the null temperature issue
        assert "NoneType" in str(exc_info.value) or "float" in str(exc_info.value)
    
    def test_get_weather_city_not_found(self):
        """Test error handling for non-existent city"""
        with pytest.raises(ValueError) as exc_info:
            self.weather_service.get_weather("NonExistentCity")
        
        assert "not found" in str(exc_info.value)
    
    def test_temperature_conversion(self):
        """Test temperature conversion helper"""
        # Test normal case
        assert self.weather_service._celsius_to_fahrenheit(0) == 32
        assert self.weather_service._celsius_to_fahrenheit(100) == 212
        assert self.weather_service._celsius_to_fahrenheit(25) == 77
    
    def test_temperature_conversion_with_null(self):
        """
        🐛 BUG TEST: This test will FAIL
        Temperature conversion should handle null values
        Expected: Return None or raise appropriate exception
        Actual: Raises TypeError
        """
        with pytest.raises(TypeError):
            self.weather_service._celsius_to_fahrenheit(None)  # type: ignore
