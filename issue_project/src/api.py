"""
Flask API for Weather Service
"""
from flask import Flask, jsonify, request
from src.weather_service import WeatherService, WeatherDataProvider

app = Flask(__name__)

# Initialize service
data_provider = WeatherDataProvider()
weather_service = WeatherService(data_provider)


@app.route('/api/weather', methods=['GET'])
def get_weather():
    """
    Get weather for a city
    Query parameter: city
    """
    city = request.args.get('city')
    
    if not city:
        return jsonify({'error': 'City parameter is required'}), 400
    
    try:
        weather_data = weather_service.get_weather(city)
        return jsonify(weather_data), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except TypeError as e:
        # 🐛 This catches the null pointer issue but returns 500
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
