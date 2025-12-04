"""
Weather Service Module
Handles fetching and processing weather data from external API
"""
import json
import os
from typing import Dict, Optional


class WeatherDataProvider:
    """Simulates third-party weather API"""
    
    def __init__(self, mock_data_path: Optional[str] = None):
        self.mock_data_path = mock_data_path or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'mock_weather_responses.json'
        )
        
    def fetch_weather_data(self, city: str) -> Dict:
        """Fetch weather data for a given city"""
        with open(self.mock_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if city not in data:
            raise ValueError(f"City '{city}' not found")
        
        return data[city]


class WeatherService:
    """Main weather service that processes weather data"""
    
    def __init__(self, data_provider: WeatherDataProvider):
        self.data_provider = data_provider
    
    def get_weather(self, city: str) -> Dict:
        """
        Get weather information for a city
        
        Args:
            city: Name of the city
            
        Returns:
            Formatted weather information
            
        Raises:
            ValueError: If city not found
        """
        # Fetch raw data from external API
        raw_data = self.data_provider.fetch_weather_data(city)
        
        # Process and format the data
        # 🐛 BUG: Line 45 - No null check for temperature field
        # When temperature is null (e.g., sensor failure), this will cause issues
        temperature_fahrenheit = self._celsius_to_fahrenheit(raw_data['temperature'])
        
        formatted_data = {
            'city': raw_data['city'],
            'temperature_c': raw_data['temperature'],
            'temperature_f': temperature_fahrenheit,
            'humidity': raw_data['humidity'],
            'condition': raw_data['condition'],
            'wind_speed_kmh': raw_data['wind_speed']
        }
        
        return formatted_data
    
    def _celsius_to_fahrenheit(self, celsius: float) -> float:
        """Convert Celsius to Fahrenheit"""
        # 🐛 This will raise TypeError when celsius is None
        return (celsius * 9/5) + 32
