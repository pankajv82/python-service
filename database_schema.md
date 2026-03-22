# Database & API Schemas Coverage

## 1. `player-service-app` Schemas

### SQLite Database (`players` table)
This database is dynamically generated on startup from `Player.csv` using Pandas and SQLAlchemy.
All inferred types are corresponding SQLite types (`TEXT`, `FLOAT`, `INTEGER`).

| Column Name | Datatype | Optional/Mandatory | Description / Notes |
| :--- | :--- | :--- | :--- |
| `playerId` | TEXT | Mandatory | Unique Identifier for the player |
| `birthYear` | FLOAT | Optional | Year of birth |
| `birthMonth` | FLOAT | Optional | Month of birth |
| `birthDay` | FLOAT | Optional | Day of birth |
| `birthCountry` | TEXT | Optional | Country of birth |
| `birthState` | TEXT | Optional | State of birth |
| `birthCity` | TEXT | Optional | City of birth |
| `deathYear` | FLOAT | Optional | Year of death |
| `deathMonth` | FLOAT | Optional | Month of death |
| `deathDay` | FLOAT | Optional | Day of death |
| `deathCountry` | TEXT | Optional | Country of death |
| `deathState` | TEXT | Optional | State of death |
| `deathCity` | TEXT | Optional | City of death |
| `nameFirst` | TEXT | Optional | First Name |
| `nameLast` | TEXT | Optional | Last Name |
| `nameGiven` | TEXT | Optional | Given Name |
| `weight` | FLOAT | Optional | Weight in lbs |
| `height` | FLOAT | Optional | Height in inches |
| `bats` | TEXT | Optional | Batting hand (L, R, B) |
| `throws` | TEXT | Optional | Throwing hand (L, R, S) |
| `debut` | TEXT | Optional | Date of first game (YYYY-MM-DD) |
| `finalGame` | TEXT | Optional | Date of final game (YYYY-MM-DD) |
| `retroID` | TEXT | Optional | Retrosheet ID |
| `bbrefID` | TEXT | Optional | Baseball Reference ID |

---

## 2. `player-service-model` Schemas

### Features Database (`features_db.csv` / Pandas DataFrame)
Contains the same properties as `Player.csv` but with additional calculated normalized features mapped as `FLOAT` which are used directly by the ML team generation models.

| Column Name | Datatype | Optional/Mandatory | Description / Notes |
| :--- | :--- | :--- | :--- |
| *(All fields from `players` table)* | *Various* | Optional | Inherited properties (see above) |
| `birthFraction` | FLOAT | Optional | Calculated decimal from birth date |
| `birthZ` | FLOAT | Mandatory* | Z-score for age |
| `weightZ` | FLOAT | Mandatory* | Z-score for weight |
| `heightZ` | FLOAT | Mandatory* | Z-score for height |
| `batsN` | FLOAT | Mandatory* | Normalized numeric value for batting hand (-1.0, 0.0, 1.0) |
| `throwsN` | FLOAT | Mandatory* | Normalized numeric value for throwing hand (-1.0, 0.0, 1.0) |
*(For players included in ML, these calculated columns are guaranteed to be populated)*

### API Pydantic Models

#### `Features` (Input properties block)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `birth_year` | FLOAT | Optional |
| `height` | FLOAT | Optional |
| `weight` | FLOAT | Optional |
| `bats` | Literal["L", "R", "N"] | Optional |
| `throws` | Literal["L", "R", "N"] | Optional |

#### `TeamGenerateInput` (POST `/team/generate` Request)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `seed_id` | STRING | Optional* |
| `features` | Features (Object) | Optional* |
| `team_size` | INTEGER | Mandatory |
*(Note: At least one of `seed_id` or `features` must be provided)*

#### `TeamGenerateOutput` (POST `/team/generate` Response)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `seed_id` | STRING | Optional |
| `prediction_id` | STRING | Mandatory |
| `team_size` | INTEGER | Mandatory |
| `member_ids` | List[STRING] | Mandatory |

#### `TeamFeedbackInput` (POST `/team/feedback` Request)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `seed_id` | STRING | Mandatory |
| `member_id` | STRING | Mandatory |
| `feedback` | Literal[-1, 1] | Mandatory |
| `prediction_id` | STRING | Mandatory |

#### `TeamFeedbackOutput` (POST `/team/feedback` Response)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `seed_id` | STRING | Mandatory |
| `prediction_id` | STRING | Mandatory |
| `member_id` | STRING | Mandatory |
| `accepted` | BOOLEAN | Mandatory |

#### `LLMInput` (POST `/llm/generate` Request)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `system_prompt` | STRING | Optional |
| `user_prompt` | STRING | Mandatory |

#### `LLMOutput` (POST `/llm/generate` Response)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `response` | STRING | Mandatory |

#### `LLMFeedbackInput` (POST `/llm/feedback` Request)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `feedback` | STRING | Mandatory |

#### `LLMFeedbackOutput` (POST `/llm/feedback` Response)
| Field | Datatype | Optional/Mandatory |
| :--- | :--- | :--- |
| `system_prompt` | STRING | Optional |
| `user_prompt` | STRING | Mandatory |
