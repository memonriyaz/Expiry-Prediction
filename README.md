# 🍲 Food Safety Analyzer API

A food safety analysis API powered by Google's Gemini AI that helps determine if food is safe to eat based on storage conditions and time since preparation.

## Features

- 🧠 Utilizes Google's Gemini AI to analyze food safety
- 🔍 Categorizes foods and provides safety recommendations
- ⏱️ Calculates expiry times based on storage conditions
- 🌡️ Identifies when food is in the "danger zone"
- 📊 Provides detailed safety information via API
- 🌐 Can be deployed as a standalone service or API
- 📱 Includes web interface for testing

## Requirements

- Python 3.7+
- Google Gemini API key ([Get one here](https://ai.google.dev/))
- Web browser for testing interface

## Local Installation

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/food-safety-api.git
   cd food-safety-api
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root containing your Gemini API key:

   ```
   GEMINI_API_KEY=your_api_key_here
   ```

4. Run the API locally:
   ```
   python start.py
   ```

## API Usage

### Analyze Food Safety

**Endpoint:** `POST /api/food-safety`

**Request Body:**

```json
{
  "foodName": "chicken curry",
  "storageType": "Room Temp",
  "hoursSincePrepared": 2
}
```

**Response:**

```json
{
  "food_name": "chicken curry",
  "food_category": "Meat",
  "ingredients": ["chicken", "curry"],
  "high_risk": true,
  "safety_status": "consume_soon",
  "safety_message": "This meat should be consumed soon.",
  "danger_zone_hours": 2,
  "shelf_life": {
    "Room Temp": 2,
    "Refrigerated": 48,
    "Frozen": 2160
  },
  "recommended_storage": "Refrigerated",
  "safety_guidelines": [
    "Keep meat items at safe temperatures.",
    "Wash hands before and after handling food.",
    "Use separate cutting boards for raw meats and vegetables.",
    "High-risk foods should not be left at room temperature for more than 2 hours.",
    "Cook meat to appropriate internal temperatures to ensure safety."
  ],
  "remaining_hours": 0,
  "hours_before_unsafe": 0
}
```

### Get Storage Types

**Endpoint:** `GET /api/storage-types`

**Response:**

```json
["Room Temp", "Refrigerated", "Frozen"]
```

### Health Check

**Endpoint:** `GET /api/health`

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2023-06-15T12:34:56.789Z",
  "gemini_model": true,
  "gemini_model_name": "gemini-pro",
  "version": "1.0.0"
}
```

## Deployment Options

This API can be deployed to various cloud platforms for remote access:

- [Heroku Deployment Guide](deployment-guides/heroku.md)
- [Render Deployment Guide](deployment-guides/render.md)

## Integrating with Your Main Project

After deployment, you can integrate this API with your main project:

```javascript
async function analyzeFoodSafety(foodName, storageType, hoursSincePrepared) {
  const response = await fetch(
    "https://your-deployed-url.com/api/food-safety",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        foodName,
        storageType,
        hoursSincePrepared,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return await response.json();
}
```

## Project Structure

- `gemini_food_analyzer.py` - The main API server that communicates with Gemini
- `gemini_food_tester.html` - The web interface for testing
- `start.py` - Helper script to set up and start the application
- `.env` - Configuration file for your API key
- `requirements.txt` - Dependencies for deployment
- `Procfile` - For Heroku deployment

## Limitations

- Food safety analysis is provided as guidance only and not a substitute for professional advice
- The accuracy depends on the quality of information provided
- For complex or unusual foods, the analysis may be more general

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Powered by [Google Gemini AI](https://ai.google.dev/)
- Built with Flask, HTML, CSS, and JavaScript
