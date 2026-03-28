# Server.py - Player Service Model API

## Overview

`server.py` is a Flask-based REST API server that provides AI-driven player recommendation and team generation features using a K-Nearest Neighbors (KNN) machine learning model. It serves as the core inference engine for the Player Service Model microservice.

**Port:** `8657`  
**Framework:** Flask with Pydantic validation  
**ML Algorithm:** K-Nearest Neighbors (KNN) using scikit-learn

---

## 🏗️ Architecture

### Key Components

1. **ML Model:** Pre-trained `team_model.joblib` 
   - Algorithm: NearestNeighbors (n_neighbors=25)
   - Features: 5 normalized attributes (birthZ, heightZ, weightZ, batsN, throwsN)

2. **Player Database:** `features_db.csv`
   - Contains 25+ player attributes including Z-score normalized fields
   - Loaded into memory as Pandas DataFrame on startup

3. **Feature Normalization:** Stats calculator for Z-score computation
   - Dynamically computes Z-scores for incoming requests
   - Uses dataset-wide mean/std statistics

4. **Feedback System:** In-memory exclusion database
   - Tracks negative feedback for generated recommendations
   - Filters future results to exclude poorly-rated players

---

## 📥 Data Files

### Required Files (must be in same directory as server.py)

| File | Description | Used For |
| :--- | :--- | :--- |
| `team_model.joblib` | Pre-trained KNN model | Finding nearest neighbor players |
| `features_db.csv` | Player features database | Loading player data and stats |

### CSV Columns

**Key Fields:**
- `playerID` - Unique player identifier
- `birthYear`, `birthMonth`, `birthDay` - Birth date components
- `height`, `weight` - Physical attributes (inches, lbs)
- `bats`, `throws` - Batting/throwing hand (L, R, B, S, N)
- `birthZ`, `heightZ`, `weightZ` - Z-score normalized values
- `batsN`, `throwsN` - Numerically encoded hand preference (1.0, -1.0, 0.0)

**Computed on Startup:**
- `birthFraction` - Calculated as `year + (month/12) + (day/365)`

---

## 🔌 API Endpoints

### 1. POST `/team/generate`

**Purpose:** Generate a list of similar players using KNN algorithm.

**Request (TeamGenerateInput):**
```json
{
  "seed_id": "abbotji01",
  "features": null,
  "team_size": 10
}
```

OR with custom features:
```json
{
  "seed_id": null,
  "features": {
    "birth_year": 1970,
    "height": 70,
    "weight": 180,
    "bats": "R",
    "throws": "L"
  },
  "team_size": 10
}
```

**Response (TeamGenerateOutput):**
```json
{
  "seed_id": "abbotji01",
  "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
  "team_size": 10,
  "member_ids": ["combspa01", "maurero01", "cummijo01", "...]
}
```

**Parameters:**
- `seed_id` (optional): Existing player ID to find similar players
- `features` (optional): Custom physical attributes for matching
- `team_size` (required): Number of players to return (integer)

**Notes:**
- Must provide **either** `seed_id` **or** `features`, not both
- Automatically excludes players marked in feedback database
- 1% random timeout failure for testing resilience
- 1% random 6-second delay for latency testing

---

### 2. POST `/team/feedback`

**Purpose:** Store feedback about team recommendations to improve future results.

**Request (TeamFeedbackInput):**
```json
{
  "seed_id": "abbotji01",
  "member_id": "maurero01",
  "feedback": -1,
  "prediction_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (TeamFeedbackOutput):**
```json
{
  "seed_id": "abbotji01",
  "member_id": "maurero01",
  "accepted": true,
  "prediction_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Parameters:**
- `seed_id` (required): The original seed player
- `member_id` (required): Recommended player to exclude/include
- `feedback` (required): -1 for negative, 1 for positive feedback
- `prediction_id` (required): ID from the original generation call

**Behavior:**
- Negative feedback (-1) adds player to exclusion database
- Excluded players won't appear in future generations for the same seed
- Positive feedback (1) is acknowledged but doesn't override exclusions

---

### 3. POST `/llm/generate`

**Purpose:** Generate AI-powered text responses (placeholder implementation).

**Request (LLMInput):**
```json
{
  "system_prompt": "You are a baseball analyst.",
  "user_prompt": "Describe the strengths of left-handed pitchers."
}
```

**Response (LLMOutput):**
```json
{
  "response": "Generated Description"
}
```

**Status:** Currently returns mock response (placeholder)

---

### 4. POST `/llm/feedback`

**Purpose:** Provide feedback on LLM-generated responses (placeholder implementation).

**Request (LLMFeedbackInput):**
```json
{
  "feedback": "Response was too technical, please simplify."
}
```

**Response (LLMFeedbackOutput):**
```json
{
  "system_prompt": null,
  "user_prompt": "Feedback acknowledgment"
}
```

**Status:** Currently returns mock response (placeholder)

---

## 🔧 Running the Server

### Prerequisites

Install all dependencies:
```bash
pip install -r requirements.txt
```

**Required packages:**
- pandas >= 2.2.3
- numpy >= 1.23.0
- scikit-learn >= 1.0.0
- Flask >= 3.0.0
- flask-pydantic >= 0.12.0
- pydantic >= 2.0.0
- joblib >= 1.3.0

### Start the Server

From the `a4a_model` directory:

```bash
python server.py
```

Or from the parent directory:

```bash
cd player-service-model
python a4a_model/server.py
```

The server will start on `http://0.0.0.0:8657` with debug mode enabled.

### Verify Server is Running

```bash
curl http://localhost:8657/team/generate \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"seed_id":"abbotji01","team_size":5}'
```

Expected response:
```json
{
  "seed_id": "abbotji01",
  "prediction_id": "uuid-here",
  "team_size": 5,
  "member_ids": ["player1", "player2", "player3", "player4", "player5"]
}
```

---

## 📊 How Team Generation Works

### Process Flow

1. **Input Processing**
   - Accept either `seed_id` or `features` parameter
   - Validate that at least one is provided

2. **Feature Extraction**
   - **If using seed_id:** Extract normalized features from dataset
   - **If using features:** Dynamically compute Z-scores using dataset statistics

3. **Normalization** (for custom features)
   ```
   heightZ = (height - dataset_mean) / dataset_std
   weightZ = (weight - dataset_mean) / dataset_std
   birthZ = (birth_year - dataset_mean) / dataset_std
   batsN = 1.0 (R) | -1.0 (L) | 0.0 (N)
   throwsN = 1.0 (R) | -1.0 (L) | 0.0 (N)
   ```

4. **KNN Search**
   - Find nearest neighbors using Euclidean distance
   - K = team_size + number of excluded players (to account for filtering)

5. **Feedback Filtering**
   - Remove any players marked as negative feedback
   - Return up to `team_size` remaining players

6. **Response Generation**
   - Return player IDs with unique prediction ID for tracking
   - Actual team size may be less than requested if many exclusions exist

---

## 📈 Features & Attributes

### Physical Attributes (Z-Scored)

| Attribute | Description | Range | Unit |
| :--- | :--- | :--- | :--- |
| `birthZ` | Age/generation normalized | -3 to +3 | Z-score |
| `heightZ` | Height normalized | -3 to +3 | Z-score (inches) |
| `weightZ` | Weight normalized | -3 to +3 | Z-score (lbs) |

### Categorical Attributes (Encoded)

| Attribute | L (Left) | R (Right) | N (Neither/Both) |
| :--- | :--- | :--- | :--- |
| `batsN` | -1.0 | 1.0 | 0.0 |
| `throwsN` | -1.0 | 1.0 | 0.0 |

---

## 🎯 Use Cases

### 1. Scout Similar Players
```bash
curl -X POST http://localhost:8657/team/generate \
  -H "Content-Type: application/json" \
  -d '{
    "seed_id": "abbotji01",
    "team_size": 10
  }'
```
Find 10 players with similar characteristics to Jim Abbott.

### 2. Find Players with Specific Attributes
```bash
curl -X POST http://localhost:8657/team/generate \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "birth_year": 1970,
      "height": 70,
      "weight": 180,
      "bats": "R",
      "throws": "L"
    },
    "team_size": 15
  }'
```
Find 15 players matching specific physical profile.

### 3. Exclude Poor Recommendations
```bash
curl -X POST http://localhost:8657/team/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "seed_id": "abbotji01",
    "member_id": "undesired_player_id",
    "feedback": -1,
    "prediction_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```
Mark a recommendation as poor; it won't appear in future results for this seed player.

---

## ⚠️ Error Handling

### Common Errors

| Error | Cause | Solution |
| :--- | :--- | :--- |
| `FileNotFoundError: team_model.joblib` | Model file missing or not in script directory | Ensure model file exists in same directory |
| `FileNotFoundError: features_db.csv` | CSV file missing | Ensure CSV exists in same directory |
| `KeyError: birthFraction` | CSV columns incorrect | Ensure CSV has required columns |
| `TeamException: seed_id not found` | Provided seed_id doesn't exist in database | Use valid player ID |
| `TeamException: payload missing seed_id or features` | Both parameters are None | Provide either seed_id or features |
| `TimeoutError: Unable to generate result` | Random 1% failure simulator triggered | Retry the request |

### Exception Handling

The server includes:
- Custom `TeamException` for team generation errors
- Pydantic validation for request/response schemas
- Flask error handling for HTTP responses

---

## 🔄 Feedback Loop

### How Exclusions Work

1. **Negative Feedback (-1)**
   - Stores player ID in in-memory `exclude_db` dictionary
   - Key: `seed_id`, Value: set of `member_id` to exclude

2. **Future Generations**
   - When generating teams for same seed, KNN finds extra players
   - Filters out excluded members before returning results

3. **Limitations**
   - Exclusions are in-memory (lost on server restart)
   - Only applies to specific seed player
   - No persistence to database

---

## 📝 Logging & Debugging

The server prints debug information:
```
seed='abbotji01' seed_features=[[...]] has exclude_db.get(seed)={'player_id_1', 'player_id_2'}
member_ids=['player3', 'player4', 'player5']
```

Enable by running with:
```bash
python server.py  # debug=True by default
```

---

## 🚀 Performance Notes

- **Startup time:** ~2-5 seconds (loads model + CSV)
- **Request latency:** ~10-50ms (depends on team_size)
- **Memory footprint:** ~200-300 MB (model + dataframe in RAM)
- **Concurrent requests:** Flask default (~1 worker, non-production)

---

## 📚 Related Files

- **Parent directory:** `player-service-model/`
- **Training notebook:** `train.ipynb` (generates team_model.joblib)
- **Model file:** `team_model.joblib` (KNN model)
- **Data file:** `features_db.csv` (player features)
- **README:** `../README.md`

