import os
import json
import re
from datetime import datetime
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('gemini_food_analyzer')

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY not set in environment")

genai.configure(api_key=GEMINI_API_KEY)

# Available models to try
AVAILABLE_MODELS = ["gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro"]

# Find a working model
def get_working_model():
    for model_name in AVAILABLE_MODELS:
        try:
            logger.info(f"Trying to use model: {model_name}")
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple query
            response = model.generate_content("Hello")
            if response:
                logger.info(f"Successfully using model: {model_name}")
                return model
        except Exception as e:
            logger.warning(f"Error with model {model_name}: {str(e)}")
    
    logger.error("No working Gemini models found")
    return None

# Get the model
gemini_model = get_working_model()

# Storage type definitions
STORAGE_TYPES = {
    "Room Temp": "room temperature (around 70°F/21°C)",
    "Refrigerated": "refrigerated (around 40°F/4°C)",
    "Frozen": "frozen (around 0°F/-18°C)"
}

# Default expiry times for different food categories (in hours)
DEFAULT_EXPIRY = {
    "Meat": {
        "Room Temp": 2,
        "Refrigerated": 48,
        "Frozen": 2160  # 90 days
    },
    "Seafood": {
        "Room Temp": 1,
        "Refrigerated": 24,
        "Frozen": 1440  # 60 days
    },
    "Dairy": {
        "Room Temp": 2,
        "Refrigerated": 72,
        "Frozen": 720  # 30 days
    },
    "Vegetables": {
        "Room Temp": 24,
        "Refrigerated": 168,  # 7 days
        "Frozen": 2160  # 90 days
    },
    "Fruits": {
        "Room Temp": 72,
        "Refrigerated": 240,  # 10 days
        "Frozen": 1440  # 60 days
    },
    "Grains": {
        "Room Temp": 72,
        "Refrigerated": 168,  # 7 days
        "Frozen": 2160  # 90 days
    },
    "Baked Goods": {
        "Room Temp": 48,
        "Refrigerated": 168,  # 7 days
        "Frozen": 720  # 30 days
    },
    "Mixed": {
        "Room Temp": 2,
        "Refrigerated": 72,
        "Frozen": 1440  # 60 days
    }
}

# Danger zone temperatures for food safety
DANGER_ZONE = {
    "min": 40,  # 40°F (4°C)
    "max": 140  # 140°F (60°C)
}

# Food is in danger zone if kept at room temperature beyond these hours
DANGER_ZONE_HOURS = {
    "Meat": 2,
    "Seafood": 1,
    "Dairy": 2,
    "Vegetables": 4,
    "Fruits": 6,
    "Grains": 4,
    "Baked Goods": 12,
    "Mixed": 2
}

def analyze_food_with_gemini(food_name, storage_type, hours_since_prepared):
    """Analyze food safety using Gemini API"""
    if not gemini_model:
        logger.error("No working Gemini model available")
        return fallback_food_analysis(food_name, storage_type, hours_since_prepared)
    
    try:
        prompt = f"""
        You are a food safety expert. Analyze the safety of the following food item:
        
        Food: {food_name}
        Current storage: {STORAGE_TYPES.get(storage_type, storage_type)}
        Hours since prepared/cooked: {hours_since_prepared}
        
        Respond with a JSON object only (no other text) in this exact format:
        {{
            "food_name": "{food_name}",
            "food_category": "One of: Meat, Seafood, Dairy, Vegetables, Fruits, Grains, Baked Goods, Mixed",
            "ingredients": ["ingredient1", "ingredient2", ...],
            "high_risk": true/false,
            "safety_status": "One of: fresh, safe_today, consume_soon, consume_immediately, change_storage, unsafe, expired",
            "safety_message": "Clear message about the food safety status",
            "danger_zone_hours": number of hours this food can safely be at room temperature,
            "shelf_life": {{
                "Room Temp": hours at room temperature,
                "Refrigerated": hours when refrigerated,
                "Frozen": hours when frozen
            }},
            "recommended_storage": "Most appropriate storage type",
            "safety_guidelines": [
                "Guideline 1",
                "Guideline 2",
                ...
            ]
        }}
        
        Ensure all times are in hours, all values are in the specified format, and provide accurate shelf life estimates based on food safety standards.
        """

        logger.info(f"Sending prompt to Gemini for food: {food_name}")
        response = gemini_model.generate_content(prompt)
        
        if not response or not response.text:
            logger.warning("Empty response from Gemini")
            return fallback_food_analysis(food_name, storage_type, hours_since_prepared)
            
        # Try to extract valid JSON
        try:
            # Find JSON in the response
            json_pattern = r'({[\s\S]*})'
            json_match = re.search(json_pattern, response.text)
            
            if json_match:
                json_text = json_match.group(1)
                analysis = json.loads(json_text)
                logger.info(f"Successfully analyzed {food_name} with Gemini")
                
                # Validate response format
                required_fields = ["food_name", "food_category", "ingredients", "high_risk", 
                                   "safety_status", "safety_message", "danger_zone_hours", 
                                   "shelf_life", "recommended_storage", "safety_guidelines"]
                
                for field in required_fields:
                    if field not in analysis:
                        logger.warning(f"Missing field in Gemini response: {field}")
                        analysis[field] = None
                
                # Ensure all storage types are present
                if "shelf_life" in analysis:
                    for storage in STORAGE_TYPES.keys():
                        if storage not in analysis["shelf_life"]:
                            if analysis["food_category"] in DEFAULT_EXPIRY:
                                analysis["shelf_life"][storage] = DEFAULT_EXPIRY[analysis["food_category"]][storage]
                            else:
                                analysis["shelf_life"][storage] = DEFAULT_EXPIRY["Mixed"][storage]
                
                return analysis
            else:
                logger.warning("No JSON found in Gemini response")
                return fallback_food_analysis(food_name, storage_type, hours_since_prepared)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return fallback_food_analysis(food_name, storage_type, hours_since_prepared)
            
    except Exception as e:
        logger.error(f"Error in Gemini analysis: {str(e)}")
        return fallback_food_analysis(food_name, storage_type, hours_since_prepared)

def fallback_food_analysis(food_name, storage_type, hours_since_prepared):
    """Fallback analysis when Gemini API fails"""
    logger.info(f"Using fallback analysis for {food_name}")
    
    # Try to categorize the food based on common keywords
    category = "Mixed"  # Default category
    
    food_lower = food_name.lower()
    
    # Simple keyword-based categorization
    if any(word in food_lower for word in ["chicken", "beef", "pork", "steak", "burger", "ham", "sausage", "turkey"]):
        category = "Meat"
    elif any(word in food_lower for word in ["fish", "shrimp", "salmon", "tuna", "prawn", "lobster", "crab", "seafood"]):
        category = "Seafood"
    elif any(word in food_lower for word in ["milk", "cheese", "yogurt", "butter", "cream", "dairy", "paneer"]):
        category = "Dairy"
    elif any(word in food_lower for word in ["spinach", "carrot", "broccoli", "potato", "onion", "tomato", "vegetable", "salad"]):
        category = "Vegetables"
    elif any(word in food_lower for word in ["apple", "banana", "orange", "grape", "fruit", "berry"]):
        category = "Fruits"
    elif any(word in food_lower for word in ["rice", "pasta", "wheat", "bread", "cereal", "grain", "oat"]):
        category = "Grains"
    elif any(word in food_lower for word in ["cake", "cookie", "muffin", "pastry", "bread", "baked"]):
        category = "Baked Goods"
    
    # Get default expiry times
    shelf_life = DEFAULT_EXPIRY.get(category, DEFAULT_EXPIRY["Mixed"])
    
    # Determine safety status
    danger_zone_hour = DANGER_ZONE_HOURS.get(category, 2)
    high_risk = category in ["Meat", "Seafood", "Dairy", "Mixed"]
    
    # Check storage conditions
    in_danger_zone = storage_type == "Room Temp" and hours_since_prepared > danger_zone_hour
    
    if hours_since_prepared >= shelf_life[storage_type]:
        safety_status = "expired"
        message = f"This {category.lower()} item has expired and should be discarded."
    elif in_danger_zone:
        safety_status = "unsafe"
        message = f"This {category.lower()} has been in the danger zone for too long and may be unsafe."
    elif hours_since_prepared >= (shelf_life[storage_type] * 0.8):
        safety_status = "consume_immediately"
        message = f"This {category.lower()} should be consumed immediately."
    elif hours_since_prepared >= (shelf_life[storage_type] * 0.6):
        safety_status = "consume_soon"
        message = f"This {category.lower()} should be consumed soon."
    else:
        safety_status = "safe_today"
        message = f"This {category.lower()} is safe to consume."
    
    # Determine recommended storage
    if category in ["Meat", "Seafood", "Dairy"]:
        recommended = "Refrigerated" if hours_since_prepared < 2 else "Frozen"
    elif hours_since_prepared > (shelf_life["Room Temp"] * 0.5):
        recommended = "Refrigerated"
    else:
        recommended = storage_type
    
    # Generate safety guidelines
    guidelines = [
        f"Keep {category.lower()} items at safe temperatures.",
        "Wash hands before and after handling food.",
        "Use separate cutting boards for raw meats and vegetables."
    ]
    
    if high_risk:
        guidelines.append("High-risk foods should not be left at room temperature for more than 2 hours.")
    
    if category == "Meat":
        guidelines.append("Cook meat to appropriate internal temperatures to ensure safety.")
    
    if category == "Seafood":
        guidelines.append("Seafood spoils quickly and should be consumed within 1-2 days of refrigeration.")
    
    # Create ingredients based on food name
    ingredients = [part.strip() for part in food_lower.split() if len(part.strip()) > 2]
    if not ingredients:
        ingredients = [food_name]
    
    # Construct the response
    analysis = {
        "food_name": food_name,
        "food_category": category,
        "ingredients": ingredients,
        "high_risk": high_risk,
        "safety_status": safety_status,
        "safety_message": message,
        "danger_zone_hours": danger_zone_hour,
        "shelf_life": shelf_life,
        "recommended_storage": recommended,
        "safety_guidelines": guidelines
    }
    
    return analysis

# Serve static files
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Add a specific route for the test interface
@app.route('/test')
def test_interface():
    return send_from_directory('static', 'gemini_food_tester.html')

@app.route('/api/food-safety', methods=['POST'])
def food_safety_endpoint():
    """Endpoint to analyze food safety"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Extract parameters
        food_name = data.get('foodName', '')
        storage_type = data.get('storageType', 'Room Temp')
        hours_since_prepared = data.get('hoursSincePrepared', 0)
        
        logger.info(f"Analyzing food: {food_name}, Storage: {storage_type}, Hours: {hours_since_prepared}")
        
        # Validate
        if not food_name:
            return jsonify({"error": "Food name is required"}), 400
        
        if storage_type not in STORAGE_TYPES:
            return jsonify({"error": f"Invalid storage type. Must be one of: {', '.join(STORAGE_TYPES.keys())}"}), 400
        
        try:
            hours_since_prepared = float(hours_since_prepared)
        except ValueError:
            return jsonify({"error": "Hours since prepared must be a number"}), 400
        
        # Analyze food safety
        analysis = analyze_food_with_gemini(food_name, storage_type, hours_since_prepared)
        
        # Add remaining shelf life information
        analysis["remaining_hours"] = max(0, analysis["shelf_life"][storage_type] - hours_since_prepared)
        
        # Add hours before unsafe
        analysis["hours_before_unsafe"] = max(0, analysis["danger_zone_hours"] - hours_since_prepared) if storage_type == "Room Temp" else None
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error in food safety endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/storage-types', methods=['GET'])
def get_storage_types():
    """Return available storage types"""
    return jsonify(list(STORAGE_TYPES.keys()))

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "gemini_model": gemini_model is not None,
        "gemini_model_name": next((model for model in AVAILABLE_MODELS if gemini_model and model in str(gemini_model)), None) if gemini_model else None,
        "version": "1.0.0"
    }
    return jsonify(status)

# For documentation and testing
@app.route('/api/docs', methods=['GET'])
def get_api_docs():
    """Return API documentation"""
    docs = {
        "api_version": "1.0.0",
        "endpoints": [
            {
                "path": "/api/food-safety",
                "method": "POST",
                "description": "Analyze food safety based on food name, storage type, and time since preparation",
                "parameters": {
                    "foodName": "Name of the food item (required)",
                    "storageType": "Storage type (Room Temp, Refrigerated, Frozen)",
                    "hoursSincePrepared": "Hours since the food was prepared (number)"
                },
                "example_request": {
                    "foodName": "chicken curry",
                    "storageType": "Room Temp",
                    "hoursSincePrepared": 2
                }
            },
            {
                "path": "/api/storage-types",
                "method": "GET",
                "description": "Get available storage types"
            },
            {
                "path": "/api/health",
                "method": "GET",
                "description": "Check API health status"
            }
        ]
    }
    return jsonify(docs)

if __name__ == '__main__':
    logger.info("Starting Gemini Food Analyzer API server")
    # Use PORT environment variable if available (for deployment platforms)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 