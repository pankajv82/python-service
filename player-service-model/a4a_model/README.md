# Player Similarity Model - Training Notebook Documentation

## Overview

This machine learning project implements a **k-nearest neighbors (KNN) based 
player similarity model** designed to find baseball players with comparable 
physical attributes and playing characteristics.

The trained model can identify the 25 most similar players for any given 
player based on normalized features.

## Project Purpose

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

## Data Source

- **Input file**: `player.csv`

- **Data contains**: Player statistics including:

  - `playerID`: Unique player identifier
  
  - `birth year, month, day`: Birth date information
  
  - `height`, `weight`: Physical measurements
  
  - `bats`: Batting hand (R=Right, L=Left, B=Both)
  
  - `throws`: Throwing hand (R=Right, L=Left)
  
  - Additional player statistics and career information

## Model Architecture

### Algorithm: k-Nearest Neighbors (KNN)

A non-parametric, instance-based learning algorithm that:

- Stores all training instances

- Classifies new instances based on the k nearest neighbors 
  in the training set

- Uses Euclidean distance to measure similarity

- Configuration: `n_neighbors=25`
  (retrieves 25 most similar players)

### Features Used for Similarity

The model uses **5 normalized features** for comparison:

#### 1. **birthZ**: Z-score normalized birth date

- Combines year, month, and day into a decimal value
- Standardized to have mean=0, std=1
- Captures player age/generation

#### 2. **heightZ**: Z-score normalized height

- Standardized height measurements
- Enables fair comparison across all players

#### 3. **weightZ**: Z-score normalized weight

- Standardized weight measurements
- Captures body mass differences

#### 4. **batsN**: Numeric encoding of batting hand

- Right-handed: `1.0`
- Left-handed: `-1.0`
- Both/Other: `0.0`

#### 5. **throwsN**: Numeric encoding of throwing hand

- Right-handed: `1.0`
- Left-handed: `-1.0`
- Both/Other: `0.0`

## Processing Pipeline

### Step 1: Data Loading and Exploration

```python
# Load player data
df = pd.read_csv("player.csv")

# Preview first few rows
df.head()
```

### Step 2: Feature Engineering - Birth Date Normalization

```python
# Convert birth date components into normalized z-score
df["birthZ"] = stats.zscore(
    df["birthYear"] + 
    (df["birthMonth"] - 1.0)/12.0 + 
    (df["birthDay"] - 1.0)/30.0,
    nan_policy="omit"
)
```

### Step 3: Feature Engineering - Physical and Playing Characteristics

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

### Step 4: Handle Missing Values

```python
# Replace NaN values with 0.0
# (neutral value for normalized features)
df[["birthZ", "weightZ", "heightZ"]] = \
    df[["birthZ", "weightZ", "heightZ"]].fillna(0.0)
```

### Step 5: Train KNN Model

```python
features = ["birthZ", "heightZ", "weightZ", "batsN", "throwsN"]
nn_model = NearestNeighbors(n_neighbors=25)
nn_model.fit(df[features])
```

### Step 6: Define Query Function

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

### Step 7: Model Deployment and Data Export

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

## Usage Example

```python
# Find 25 most similar players to Hank Aaron
hank_aaron_id = "aaronha01"

similar_players = get_nearest_neighbors(
    hank_aaron_id, 
    n=25
)

print(similar_players)
```

## Output Files

### 1. `team_model.joblib`

- **Type**: Serialized scikit-learn KNN model

- **Size**: Varies (depends on dataset size)

- **Purpose**: Can be loaded and used for prediction 
  without retraining

- **Usage**: 
  ```python
  import joblib
  
  loaded_model = joblib.load("team_model.joblib")
  ```

### 2. `features_db.csv`

- **Type**: CSV file with processed player data

- **Columns**: All original columns + engineered features
  - birthZ
  - weightZ
  - heightZ
  - batsN
  - throwsN

- **Purpose**: Feature database for reference and analysis

- **Rows**: One row per player

## Dependencies

### Required Packages

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

### Installation

```bash
pip install pandas==2.2.3 numpy scipy scikit-learn joblib
```

Or use requirements.txt:

```bash
pip install -r requirements.txt
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13+ |
| Data Processing | Pandas, NumPy |
| Statistical Analysis | SciPy |
| Machine Learning | Scikit-learn |
| Model Serialization | Joblib |
| Notebook Environment | Jupyter |

## Model Performance Considerations

### Strengths

- ✅ Simple and interpretable

- ✅ No training time (lazy learner)

- ✅ Effective for similarity-based tasks

- ✅ Scales well with dataset size

- ✅ Easy to understand results

### Limitations

- ❌ Computationally expensive at prediction time

- ❌ Sensitive to feature scaling
  (mitigated by z-score normalization)

- ❌ Curse of dimensionality with high-dimensional data

- ❌ Requires storing entire dataset in memory

## Validation Steps

The notebook includes data validation:

```python
# Check if a specific player exists in the dataset
"aardsda01" in list(df["playerID"])  

# Returns: True/False
```

## Future Enhancements

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

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'scipy'`

**Solution**: Install scipy using
```bash
pip install scipy
```

### Issue: `ModuleNotFoundError: No module named 'sklearn'`

**Solution**: Install scikit-learn using
```bash
pip install scikit-learn
```

### Issue: File not found errors

**Ensure** that `player.csv` is in the same directory 
as the notebook

### Issue: Model gives different results on different runs

This is **expected**

- KNN results depend on the training data
- Both results are valid
- Distance metrics are consistent

## File Structure

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

## Author Notes

This model is designed for:
- **Exploratory analysis** in baseball statistics
- **Similarity matching** and player comparison

It demonstrates classic machine learning concepts:
- Feature engineering and normalization
- Distance-based classification
- Model persistence and deployment
- Data transformation pipelines

## License

See LICENSE file in the project root.

## Contact & Support

For issues or questions:
- Refer to the project documentation
- Contact the development team
