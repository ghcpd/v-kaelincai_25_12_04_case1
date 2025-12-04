"""
Integration Tests for Weather API
Tests the Flask API endpoints
"""
import pytest
from src.api import app


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestWeatherAPI:
    """Test suite for Weather API endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json['status'] == 'healthy'
    
    def test_get_weather_success(self, client):
        """Test successful weather query"""
        response = client.get('/api/weather?city=London')
        
        assert response.status_code == 200
        data = response.json
        assert data['city'] == 'London'
        assert data['temperature_c'] == 18.0
        assert 'temperature_f' in data
        assert data['condition'] == 'Rainy'
    
    def test_get_weather_missing_city_parameter(self, client):
        """Test API without city parameter"""
        response = client.get('/api/weather')
        
        assert response.status_code == 400
        assert 'error' in response.json
        assert 'required' in response.json['error'].lower()
    
    def test_get_weather_city_not_found(self, client):
        """Test API with non-existent city"""
        response = client.get('/api/weather?city=Atlantis')
        
        assert response.status_code == 404
        assert 'error' in response.json
        assert 'not found' in response.json['error'].lower()
    
    def test_get_weather_springfield_returns_500(self, client):
        """
        🐛 BUG TEST: This test will PASS (demonstrates the bug)
        Springfield query should return 200 with temperature unavailable
        Current behavior: Returns 500 Internal Server Error
        Root cause: NullPointerException when temperature is null
        """
        response = client.get('/api/weather?city=Springfield')
        
        # BUG: This assertion passes because the API returns 500
        assert response.status_code == 500
        assert 'error' in response.json
        # The error message reveals the TypeError from null temperature
        assert 'Internal server error' in response.json['error']
    
    def test_get_weather_springfield_should_succeed(self, client):
        """
        🐛 BUG TEST: This test will FAIL (shows expected behavior)
        This is what SHOULD happen - Springfield should return valid data
        even when temperature sensor is down (null value)
        """
        response = client.get('/api/weather?city=Springfield')
        
        # This should pass but will FAIL due to the bug
        assert response.status_code == 200
        data = response.json
        assert data['city'] == 'Springfield'
        assert data['condition'] == 'Sunny'
        assert data['humidity'] == 55
        # Temperature should be None or marked as unavailable
        assert data['temperature_c'] is None or data['temperature_c'] == 'unavailable'
