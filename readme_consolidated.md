# Consolidated README - Python Player Service

This document consolidates all README files from the Python Player Service repository. 
Refer to individual README files for original formatting and details.

---

## Table of Contents
1. [Main README (Root)](#main-readme)
2. [Player Service Model README](#player-service-model-readme)
3. [Model Training Documentation](#model-training-documentation)
4. [Player Service Model Server README](#player-service-model-server-readme)

---

## Main README

### Overview
This repository contains the **Backend Python Player Service**, a microservices-based application designed to manage player data and provide AI-driven team generation features. The architecture is split into two main sub-projects:
1. **`player-service-app`**: The core API Gateway and data service layer.
2. **`player-service-model`**: An AI/ML model wrapper service for generating player recommendations based on K-Nearest Neighbors (KNN).

---

### 🏗️ Architecture and Design Flow

The application follows a **microservices architecture**, decoupling the core data access from the machine learning inference logic.

#### 1. Player Service App (`player-service-app`)
* **Framework:** Flask (Python)
* **Port:** `8000`
* **Flow:** On startup, the application reads a `Player.csv` file into a Pandas DataFrame and loads it into a local SQLite database (`player.db`) via SQLAlchemy. This enables fast, dynamic SQL querying directly in-memory.
* **Responsibilities:**
  * Serving REST endpoints for querying all players (`GET /v1/players`) or fetching a specific player by ID (`GET /v1/players/<player_id>`).
  * Proxying/integrating chat features via Ollama models (`/v1/chat`, `/v1/chat/list-models`).

#### 2. Player Service Model (`player-service-model`)
* **Framework:** Flask (Python) with `flask_pydantic` for request validation.
* **Port:** `8657` (Typically containerized via Docker/Podman)
* **ML Model:** Uses `scikit-learn`'s `NearestNeighbors` algorithm (`n_neighbors=25` by default) serialized as `team_model.joblib`. The model is trained inside `a4a_model/train.ipynb` by compiling Z-scores for physical characteristics.
* **Flow:** On startup, it loads the player features database (`features_db.csv`), extracts dataset-wide mean/std stats for dynamic Z-score calculation on incoming API requests, and loads the pre-trained `team_model.joblib`.
* **Responsibilities:**
  * Generating teams of similar players based on either a "seed" player ID (fetching nearest neighbors) or a set of manually provided physical features (height, weight, handedness, etc., which are then manually z-scored).
  * Handling feedback for generated teams to exclude certain recommendations in future requests (maintains an in-memory `exclude_db` feedback loop to filter output).
  * Providing mock endpoints for LLM interaction (`/llm/generate`, `/llm/feedback`).

---

### 🗄️ Schema & Data Models

#### 1. Database Schema (Core Data Payload)
The core application relies on a dynamically generated SQLite `players` table based on the CSV dataset. The schema supports generic querying for player properties such as `playerId`, `birthCountry`, etc., which are translated into standard JSON payloads via the `/v1/players` API.

#### 2. AI / ML Features Schema
The recommendation engine (`player-service-model`) relies on a specific set of physical features to calculate Z-scores and predict nearest neighbors using Euclidean distance (`scikit-learn`).

##### What is a Z-Score?
A **Z-Score** is a statistical measure that standardizes data by centering it around 0 and scaling it to have a standard deviation of 1. It indicates how many standard deviations a data point is from the mean.

**Formula:** Z = (X - μ) / σ

Where:
- **X** = the data point
- **μ** = the mean (average) of the dataset
- **σ** = the standard deviation of the dataset

**Why Z-Scores are used:**
- **Fair Comparison:** Different attributes have different scales (age in years, height in inches, weight in pounds). Z-Scores normalize them to the same scale.
- **Algorithm Fairness:** KNN uses Euclidean distance, which would be biased toward attributes with larger ranges without normalization.
- **Statistical Standard:** Most values fall between -3 and +3 in a normal distribution, making the data predictable and comparable.

**Example:** If average height is 70 inches with a standard deviation of 3 inches, a player who is 76 inches tall has a Z-Score of (76-70)/3 = 2.0 (2 standard deviations above average).

**Data Preprocessing (`train.ipynb` & `server.py`):**
During training (`train.ipynb`) and inference (`server.py`), raw data is transformed into a standard scale (Z-scores) to normalize heavily varying metrics.
* `birthZ`: Z-score of age (computed down to fractions of a year including month/day).
* `heightZ`, `weightZ`: Z-scores for physical tracking, missing values default to `0.0` (Dataset Mean).
* `batsN`, `throwsN`: Numerically encoded (`1.0` for Right-handed, `-1.0` for Left-handed, `0.0` for Neither/Switch).

**Model Input Features (Pydantic `Features` Schema):**
- `birth_year` (float)
- `height` (float - inches)
- `weight` (float - lbs)
- `bats` (Literals: `"L"`, `"R"`, `"N"`)
- `throws` (Literals: `"L"`, `"R"`, `"N"`)

*Internally, these inputs are dynamically vectorized into the standard scales mentioned above using the dataset's historical mean and standard deviation statistics.*

#### 3. API Payload Schemas (`player-service-model`)

##### Team Generation (`POST /team/generate`)
Used to generate similar players based on an ID or exact feature parameters.
**Request (`TeamGenerateInput`):**
```json
{
  "seed_id": "optional_string_player_id",
  "features": {
    "birth_year": 1970, "height": 70, "weight": 120, "bats": "R", "throws": "L"
  },
  "team_size": 10
}
```
*Note: You must provide **either** a `seed_id` or a `features` object.*

**Response (`TeamGenerateOutput`):**
```json
{
  "seed_id": "abbotji01",
  "prediction_id": "UUID-string",
  "team_size": 10,
  "member_ids": ["player1", "player2", "..."]
}
```

##### Team Feedback (`POST /team/feedback`)
Used to exclude specific players from future generated lists for a given seed player.
**Request (`TeamFeedbackInput`):**
```json
{
  "seed_id": "abbotji01",
  "member_id": "bad_recommendation_01",
  "feedback": -1,
  "prediction_id": "UUID-string"
}
```

**Response (`TeamFeedbackOutput`):**
```json
{
  "seed_id": "abbotji01",
  "member_id": "bad_recommendation_01",
  "accepted": true,
  "prediction_id": "UUID-string"
}
```

---

### 📋 API Endpoints Reference

#### 1. POST `/team/generate` - Generate Similar Players

**Purpose:** Generate a list of similar players based on physical and playing characteristics.

**Use Cases:**
- **Scout comparable players:** Find players with similar physical profiles to an existing player
- **Build a team with specific attributes:** Provide physical characteristics (height, weight, age, batting/throwing hand) to find matching players
- **Talent discovery:** Identify underrated players who match a specific player's profile

**How it works:**
- **Input:** Either provide a `seed_id` (existing player ID) OR custom `features` (physical attributes)
- **Output:** Returns a list of `member_ids` (similar player IDs) with a unique `prediction_id` for tracking

**Example:** "Find 10 players similar to player 'abbotji01'" or "Find 10 players who are 70 inches tall, 180 lbs, right-handed batter"

---

#### 2. POST `/team/feedback` - Refine Recommendations with Feedback

**Purpose:** Provide feedback on generated team recommendations to improve future suggestions.

**Use Cases:**
- **Exclude bad recommendations:** Mark a player as a poor recommendation for a specific seed player
- **Personalize results:** Teach the system which recommendations are relevant and which are not
- **Refine future generations:** Build a feedback loop that learns user preferences

**How it works:**
- **Input:** Provide the `prediction_id` from a previous generation, the `seed_id`, the `member_id` to exclude, and `feedback` (-1 for bad, 1 for good)
- **Output:** Confirms acceptance of the feedback and stores it for future filtering

**Example:** "Player 'maurero01' was a bad recommendation for seed 'abbotji01', so exclude them next time"

---

#### 3. POST `/llm/generate` - Generate AI Text Responses

**Purpose:** Generate AI-powered text responses using an LLM (Large Language Model).

**Use Cases:**
- **Generate descriptions:** Create player profiles or team summaries
- **Ask questions:** Query the model with custom prompts
- **Custom responses:** Get intelligent, contextual text based on system and user prompts

**How it works:**
- **Input:** Provide an optional `system_prompt` (instructions for the LLM) and a required `user_prompt` (the actual question/request)
- **Output:** Returns a text `response` from the LLM

**Example:** `system_prompt`: "You are a baseball analyst", `user_prompt`: "Describe the strengths of a left-handed pitcher" → Response: "Left-handed pitchers have a natural advantage..."

---

#### 4. POST `/llm/feedback` - Improve LLM Responses

**Purpose:** Provide feedback on LLM-generated responses to refine future outputs.

**Use Cases:**
- **Quality improvement:** Mark good or bad LLM responses for model fine-tuning
- **Preference learning:** Teach the system about desired response styles
- **Context refinement:** Help the system understand what prompts work best

**How it works:**
- **Input:** Provide `feedback` (a string describing what was good/bad about the response)
- **Output:** Returns `system_prompt` and `user_prompt` with optional adjustments based on feedback

**Example:** `feedback`: "Response was too technical, please simplify for general audience" → System learns to adjust future responses

---

### 🎯 Quick Endpoint Comparison

| Endpoint | Primary Function | Input Type | Output Type |
| :--- | :--- | :--- | :--- |
| `/team/generate` | Find similar players | Player ID or physical attributes | List of player IDs |
| `/team/feedback` | Refine player recommendations | Feedback on a recommendation | Confirmation & storage |
| `/llm/generate` | Generate AI text responses | System & user prompts | Text response |
| `/llm/feedback` | Improve LLM responses | Feedback on quality | Updated prompts & guidance |

---

### 🚀 Running the Services

#### App Service
```bash
cd player-service-app
pip install -r requirements.txt
python app.py
```

#### Model Service (Docker)
```bash
cd player-service-model
docker build -t a4a_model .
docker run -d -p 8657:8657 a4a_model
```

---

### ⚾ Player Service

Player Service is a backend application that serves baseball player data. In addition, Player service integrates with [Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md), which allows us to run the [tinyllama LLM](https://ollama.com/library/tinyllama) locally.

#### Dependencies

- Python3.9+
- sqllite3
- Docker
- [Ollama Python SDK](https://github.com/ollama/ollama-python)

#### 🛠️ Setup Instructions

1. Verify system dependencies
   1. Python
      - Verify installation: `python3 --version`
   3. Container Manager
      - Download and install from [docker.com](https://www.docker.com/)(recommended) or [podman](https://podman.io/) (alternative)
      - Verify installation, run: `docker --version` for docker

2. Clone this repository or Download the code as zip
   - run `git clone https://github.com/Intuit-A4A/backend-python-player-service.git`

#### Run the application

##### Part 1: Application Dependencies

*OPTIONAL* Create & activate virtual env
```shell
   $ python3 -m venv env # use `python -m venv env` on Windows
   $ source env/bin/activate  # use `env\Scripts\activate` on Windows
```

1. Install application dependencies
    - Move into the project's root directory, run: `cd player-service-app`.
    - From the project's root directory, run: `pip install -r requirements.txt`

##### Part 2: Run Player Service (without LLM)

1. Start the Player service

   ```shell
    python3 app.py
   ```

2. Verify the Player service is running
      1. Open your browser and visit `http://localhost:8000/v1/players`
      2. If the application is running successfully, you will see player data appear in the browser

##### Part 3: Start LLM Docker Container

Player service integrates with Ollama 🦙, which allows us to run LLMs locally. This app runs [tinyllama](https://ollama.com/library/tinyllama) model.

- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Python SDK](https://github.com/ollama/ollama-python)

1. Pull and run Ollama docker image and download `tinyllama` model
   - Pull Ollama docker image

    ```shell
    docker pull ollama/ollama
    ```

2. Run Ollama docker image on port 11434 as a background process

    ```shell
    docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
    ```

3. Download and run `tinyllama` model

    ```shell
    docker exec -it ollama ollama run tinyllama
    ```

4. Test Ollama API server

    ```curl
    curl -v --location 'http://localhost:11434/api/generate' --header 'Content-Type: application/json' --data '{"model": "tinyllama","prompt": "why is the sky blue?", "stream": false}'
    ```

Having trouble with docker? Try using podman as an alternative. Instructions [here](https://github.com/Intuit-A4A/backend-python-player-service/wiki/Supplemental-Materials:-Set-up-help)

##### Part 4: Verify Player Service and LLM Integration

1. Ensure Player Service is running

    ```shell
   python3 app.py
    ```

2. Open your browser and visit `http://localhost:8000/v1/chat/list-models`
   - If the application is running successfully, you will see a json response that include information about tinyllama

---

## Player Service Model README

This is a thin model wrapper container based on `Player.csv` data.

### Building and Running with Docker/Podman

To build and run using docker:
```shell
docker build -t a4a_model .
docker run -d -p 8657:8657 a4a_model
```

OR, alternatively, using podman:
```shell
podman build -t a4a_model .
podman run --rm -p 8657:8657  -it localhost/a4a_model:latest
```

This will expose the model on port 8657.

### Example API Requests

#### Team Generation with Player ID
To send an inference request to the AI model using player names:
```shell
$ curl -H "Content-type: application/json" -d '{"seed_id":"abbotji01","team_size":10}' http://127.0.0.1:8657/team/generate
```

Response:
```json
{
  "seed_id":"abbotji01",
  "prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a",
  "team_size":10,
  "member_ids":["abbotji01","combspa01","maurero01","cummijo01","flemida01","macdobo01","eddych01","morriha02","mcgrifr01","blossgr01"]
}
```

#### Team Generation with Features
To send an inference request to the AI model using a set of features:
```shell
$ curl -H "Content-type: application/json" -d '{"features":{"birth_year":1970, "height":70, "weight":120, "bats":"R", "throws":"L"},"team_size":10}' http://127.0.0.1:8657/team/generate
```

Response:
```json
{
  "seed_id":null,
  "prediction_id":"ddedf511-2e68-4ab5-87c5-c77b8d15eb23",
  "team_size":10,
  "member_ids":["roblevi01","deverra01","goharlu01","albieoz01","barrefr02","urenari01","uriasju01","verdual01","mejiafr01","sierrma01"]
}
```

#### Team Feedback
To send feedback about the recommendation of a prior seed:
```shell
$ curl -H "Content-type: application/json"  -d '{"seed_id":"abbotji01","member_id":"maurero01","feedback":-1,"prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"}' http://127.0.0.1:8657/team/feedback
```

Response:
```json
{
  "seed_id":"abbotji01",
  "member_id":"maurero01",
  "accepted":true,
  "prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"
}
```

---

## Model Training Documentation

### Overview

This machine learning project implements a **k-nearest neighbors (KNN) based 
player similarity model** designed to find baseball players with comparable 
physical attributes and playing characteristics.

The trained model can identify the 25 most similar players for any given 
player based on normalized features.

### Project Purpose

The model serves to:

- **Identify player similarities** based on:
  - Physical attributes (height, weight, age)
  - Playing characteristics (batting hand, throwing hand)

- **Data analysis** for identifying comparable players in baseball 
  statistics

- **Machine learning pipeline** for:
  - Feature engineering
  - Model deployment

- **Quick player lookup** using:
  - Pre-trained model
  - Feature database

### Data Source

- **Input file**: `player.csv`

- **Data contains**: Player statistics including:
  - `playerID`: Unique player identifier
  - `birth year, month, day`: Birth date information
  - `height`, `weight`: Physical measurements
  - `bats`: Batting hand (R=Right, L=Left, B=Both)
  - `throws`: Throwing hand (R=Right, L=Left)
  - Additional player statistics and career information

### Model Architecture

#### Algorithm: k-Nearest Neighbors (KNN)

A non-parametric, instance-based learning algorithm that:

- Stores all training instances
- Classifies new instances based on the k nearest neighbors in the training set
- Uses Euclidean distance to measure similarity
- Configuration: `n_neighbors=25` (retrieves 25 most similar players)

#### Features Used for Similarity

The model uses **5 normalized features** for comparison:

##### 1. **birthZ**: Z-score normalized birth date
- Combines year, month, and day into a decimal value
- Standardized to have mean=0, std=1
- Captures player age/generation

##### 2. **heightZ**: Z-score normalized height
- Standardized height measurements
- Enables fair comparison across all players

##### 3. **weightZ**: Z-score normalized weight
- Standardized weight measurements
- Captures body mass differences

##### 4. **batsN**: Numeric encoding of batting hand
- Right-handed: `1.0`
- Left-handed: `-1.0`
- Both/Other: `0.0`

##### 5. **throwsN**: Numeric encoding of throwing hand
- Right-handed: `1.0`
- Left-handed: `-1.0`
- Both/Other: `0.0`

### Processing Pipeline

#### Step 1: Data Loading and Exploration
```python
# Load player data
df = pd.read_csv("player.csv")

# Preview first few rows
df.head()
```

#### Step 2: Feature Engineering - Birth Date Normalization
```python
# Convert birth date components into normalized z-score
df["birthZ"] = stats.zscore(
    df["birthYear"] + 
    (df["birthMonth"] - 1.0)/12.0 + 
    (df["birthDay"] - 1.0)/30.0,
    nan_policy="omit"
)
```

#### Step 3: Feature Engineering - Physical and Playing Characteristics
```python
# Normalize physical measurements
df["weightZ"] = stats.zscore(
    df["weight"], 
    nan_policy="omit"
)
df["heightZ"] = stats.zscore(
    df["height"], 
    nan_policy="omit"
)

# Encode batting and throwing hands
df["batsN"] = df["bats"].apply(
    lambda b: 1.0 if b == 'R' 
              else -1.0 if b == 'L' 
              else 0.0
)
df["throwsN"] = df["throws"].apply(
    lambda b: 1.0 if b == 'R' 
              else -1.0 if b == 'L' 
              else 0.0
)
```

#### Step 4: Handle Missing Values
```python
# Replace NaN values with 0.0
# (neutral value for normalized features)
df[["birthZ", "weightZ", "heightZ"]] = \
    df[["birthZ", "weightZ", "heightZ"]].fillna(0.0)
```

#### Step 5: Train KNN Model
```python
features = ["birthZ", "heightZ", "weightZ", "batsN", "throwsN"]
nn_model = NearestNeighbors(n_neighbors=25)
nn_model.fit(df[features])
```

#### Step 6: Define Query Function
```python
def get_nearest_neighbors(id: str, n=25):
    """
    Retrieve similar players for a given player ID.
    
    Args:
        id: Player ID
           (e.g., "aaronha01" for Hank Aaron)
        n: Number of similar players to return
           (default: 25)
    
    Returns:
        pandas Series of player IDs similar to 
        the query player
    """
    # Extract features for query player
    seed = df[df["playerID"] == id][features]
    
    # Find nearest neighbors
    neighbor_indices = nn_model.kneighbors(
        seed, n, return_distance=False
    )
    
    # Return player IDs
    return df.take(neighbor_indices[0])["id"]
```

#### Step 7: Model Deployment and Data Export
```python
# Save trained model for future use
import joblib

joblib.dump(
    nn_model, 
    "team_model.joblib"
)

# Export feature database for quick lookups
df.to_csv(
    "features_db.csv", 
    index=False
)
```

### Usage Example

```python
# Find 25 most similar players to Hank Aaron
hank_aaron_id = "aaronha01"

similar_players = get_nearest_neighbors(
    hank_aaron_id, 
    n=25
)

print(similar_players)
```

### Output Files

#### 1. `team_model.joblib`
- **Type**: Serialized scikit-learn KNN model
- **Size**: Varies (depends on dataset size)
- **Purpose**: Can be loaded and used for prediction without retraining
- **Usage**: 
  ```python
  import joblib
  
  loaded_model = joblib.load("team_model.joblib")
  ```

#### 2. `features_db.csv`
- **Type**: CSV file with processed player data
- **Columns**: All original columns + engineered features
  - birthZ
  - weightZ
  - heightZ
  - batsN
  - throwsN
- **Purpose**: Feature database for reference and analysis
- **Rows**: One row per player

### Dependencies

#### Required Packages

- **pandas** (==2.2.3)
  - Data manipulation and analysis

- **numpy** (>=2.0.0)
  - Numerical computations

- **scipy** (latest)
  - Statistical functions (z-score normalization)

- **scikit-learn** (>=1.0.0)
  - Machine learning algorithms (KNN)

- **joblib** (latest)
  - Model serialization and persistence

#### Installation

```bash
pip install pandas==2.2.3 numpy scipy scikit-learn joblib
```

Or use requirements.txt:

```bash
pip install -r requirements.txt
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13+ |
| Data Processing | Pandas, NumPy |
| Statistical Analysis | SciPy |
| Machine Learning | Scikit-learn |
| Model Serialization | Joblib |
| Notebook Environment | Jupyter |

### Model Performance Considerations

#### Strengths

- ✅ Simple and interpretable
- ✅ No training time (lazy learner)
- ✅ Effective for similarity-based tasks
- ✅ Scales well with dataset size
- ✅ Easy to understand results

#### Limitations

- ❌ Computationally expensive at prediction time
- ❌ Sensitive to feature scaling (mitigated by z-score normalization)
- ❌ Curse of dimensionality with high-dimensional data
- ❌ Requires storing entire dataset in memory

### Validation Steps

The notebook includes data validation:

```python
# Check if a specific player exists in the dataset
"aardsda01" in list(df["playerID"])  

# Returns: True/False
```

### Future Enhancements

1. **Feature scaling improvements**
   - Implement StandardScaler or MinMaxScaler

2. **Dimensionality reduction**
   - Add PCA to reduce feature space

3. **Model comparison**
   - Test other algorithms
   - Random forest, neural networks

4. **Hyperparameter tuning**
   - Optimize n_neighbors value

5. **Distance metrics**
   - Experiment with different distance metrics
   - Manhattan, Minkowski

6. **Feature importance**
   - Analyze which features contribute most to similarity

7. **Cross-validation**
   - Implement k-fold cross-validation
   - Model evaluation

8. **APIs deployment**
   - Create REST API endpoints
   - Model queries

### Troubleshooting

#### Issue: `ModuleNotFoundError: No module named 'scipy'`
**Solution**: Install scipy using
```bash
pip install scipy
```

#### Issue: `ModuleNotFoundError: No module named 'sklearn'`
**Solution**: Install scikit-learn using
```bash
pip install scikit-learn
```

#### Issue: File not found errors
**Ensure** that `player.csv` is in the same directory as the notebook

#### Issue: Model gives different results on different runs
This is **expected**
- KNN results depend on the training data
- Both results are valid
- Distance metrics are consistent

### File Structure

```
a4a_model/
├── train.ipynb
│   └── Main training notebook
│
├── README.md
│   └── This documentation file
│
├── player.csv
│   └── Input data file
│
├── team_model.joblib
│   └── Trained KNN model (generated)
│
├── features_db.csv
│   └── Processed features database (generated)
│
├── model.py
│   └── Model deployment script (optional)
│
├── server.py
│   └── API server (optional)
│
└── __init__.py
```

### Author Notes

This model is designed for:
- **Exploratory analysis** in baseball statistics
- **Similarity matching** and player comparison

It demonstrates classic machine learning concepts:
- Feature engineering and normalization
- Distance-based classification
- Model persistence and deployment
- Data transformation pipelines

### License

See LICENSE file in the project root.

### Contact & Support

For issues or questions:
- Refer to the project documentation
- Contact the development team

---

## Player Service Model Server README

This is a thin model wrapper container based on `Player.csv` data.

### Building and Running with Docker/Podman

To build and run using docker:
```shell
docker build -t a4a_model .
docker run -d -p 8657:8657 a4a_model
```

OR, alternatively, using podman:
```shell
podman build -t a4a_model .
podman run --rm -p 8657:8657  -it localhost/a4a_model:latest
```

This will expose the model on port 8657.

### Example API Requests

#### Team Generation with Player ID
To send an inference request to the AI model using player names:
```shell
$ curl -H "Content-type: application/json" -d '{"seed_id":"abbotji01","team_size":10}' http://127.0.0.1:8657/team/generate
```

Response:
```json
{
  "seed_id":"abbotji01",
  "prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a",
  "team_size":10,
  "member_ids":["abbotji01","combspa01","maurero01","cummijo01","flemida01","macdobo01","eddych01","morriha02","mcgrifr01","blossgr01"]
}
```

#### Team Generation with Features
To send an inference request to the AI model using a set of features:
```shell
$ curl -H "Content-type: application/json" -d '{"features":{"birth_year":1970, "height":70, "weight":120, "bats":"R", "throws":"L"},"team_size":10}' http://127.0.0.1:8657/team/generate
```

Response:
```json
{
  "seed_id":null,
  "prediction_id":"ddedf511-2e68-4ab5-87c5-c77b8d15eb23",
  "team_size":10,
  "member_ids":["roblevi01","deverra01","goharlu01","albieoz01","barrefr02","urenari01","uriasju01","verdual01","mejiafr01","sierrma01"]
}
```

#### Team Feedback
To send feedback about the recommendation of a prior seed:
```shell
$ curl -H "Content-type: application/json"  -d '{"seed_id":"abbotji01","member_id":"maurero01","feedback":-1,"prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"}' http://127.0.0.1:8657/team/feedback
```

Response:
```json
{
  "seed_id":"abbotji01",
  "member_id":"maurero01",
  "accepted":true,
  "prediction_id":"38f5f02f-b1be-4282-8d0e-865b3995d50a"
}
```

---

## Summary

This consolidated README brings together documentation from:
- **README.md** - Main architecture and setup overview
- **README_player_service_model.md** - Model service quick reference
- **README_a4a_model_training.md** - Detailed ML model training documentation
- **player-service-model/README.md** - Model server deployment guide

For the most up-to-date and detailed information, refer to the individual README files in their respective directories.
