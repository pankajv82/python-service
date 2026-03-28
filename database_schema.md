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

---

## 3. API Endpoints with Schemas

### POST `/team/generate` - Generate Similar Players

**Purpose:** Generate a list of similar players based on physical and playing characteristics.

**Use Cases:**
- **Scout comparable players:** Find players with similar physical profiles to an existing player
- **Build a team with specific attributes:** Provide physical characteristics (height, weight, age, batting/throwing hand) to find matching players
- **Talent discovery:** Identify underrated players who match a specific player's profile

**How it works:**
- **Input:** Either provide a `seed_id` (existing player ID) OR custom `features` (physical attributes)
- **Output:** Returns a list of `member_ids` (similar player IDs) with a unique `prediction_id` for tracking

**Example:** "Find 10 players similar to player 'abbotji01'" or "Find 10 players who are 70 inches tall, 180 lbs, right-handed batter"

#### Schema (TeamGenerateInput & TeamGenerateOutput)
| **Request Field** | **Datatype** | **Req/Opt** | **Response Field** | **Datatype** | **Resp/Opt** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `seed_id` | STRING | Optional* | `seed_id` | STRING | Optional |
| `features` | Features (Object) | Optional* | `prediction_id` | STRING | Mandatory |
| `team_size` | INTEGER | Mandatory | `team_size` | INTEGER | Mandatory |
| | | | `member_ids` | List[STRING] | Mandatory |

*(Note: At least one of `seed_id` or `features` must be provided)*

---

### POST `/team/feedback` - Refine Recommendations with Feedback

**Purpose:** Provide feedback on generated team recommendations to improve future suggestions.

**Use Cases:**
- **Exclude bad recommendations:** Mark a player as a poor recommendation for a specific seed player
- **Personalize results:** Teach the system which recommendations are relevant and which are not
- **Refine future generations:** Build a feedback loop that learns user preferences

**How it works:**
- **Input:** Provide the `prediction_id` from a previous generation, the `seed_id`, the `member_id` to exclude, and `feedback` (-1 for bad, 1 for good)
- **Output:** Confirms acceptance of the feedback and stores it for future filtering

**Example:** "Player 'maurero01' was a bad recommendation for seed 'abbotji01', so exclude them next time"

#### Schema (TeamFeedbackInput & TeamFeedbackOutput)
| **Request Field** | **Datatype** | **Req/Opt** | **Response Field** | **Datatype** | **Resp/Opt** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `seed_id` | STRING | Mandatory | `seed_id` | STRING | Mandatory |
| `member_id` | STRING | Mandatory | `prediction_id` | STRING | Mandatory |
| `feedback` | Literal[-1, 1] | Mandatory | `member_id` | STRING | Mandatory |
| `prediction_id` | STRING | Mandatory | `accepted` | BOOLEAN | Mandatory |

---

### POST `/llm/generate` - Generate AI Text Responses

**Purpose:** Generate AI-powered text responses using an LLM (Large Language Model).

**Use Cases:**
- **Generate descriptions:** Create player profiles or team summaries
- **Ask questions:** Query the model with custom prompts
- **Custom responses:** Get intelligent, contextual text based on system and user prompts

**How it works:**
- **Input:** Provide an optional `system_prompt` (instructions for the LLM) and a required `user_prompt` (the actual question/request)
- **Output:** Returns a text `response` from the LLM

**Example:** `system_prompt`: "You are a baseball analyst", `user_prompt`: "Describe the strengths of a left-handed pitcher" → Response: "Left-handed pitchers have a natural advantage..."

#### Schema (LLMInput & LLMOutput)
| **Request Field** | **Datatype** | **Req/Opt** | **Response Field** | **Datatype** | **Resp/Opt** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `system_prompt` | STRING | Optional | `response` | STRING | Mandatory |
| `user_prompt` | STRING | Mandatory | | | |

---

### POST `/llm/feedback` - Improve LLM Responses

**Purpose:** Provide feedback on LLM-generated responses to refine future outputs.

**Use Cases:**
- **Quality improvement:** Mark good or bad LLM responses for model fine-tuning
- **Preference learning:** Teach the system about desired response styles
- **Context refinement:** Help the system understand what prompts work best

**How it works:**
- **Input:** Provide `feedback` (a string describing what was good/bad about the response)
- **Output:** Returns `system_prompt` and `user_prompt` with optional adjustments based on feedback

**Example:** `feedback`: "Response was too technical, please simplify for general audience" → System learns to adjust future responses

#### Schema (LLMFeedbackInput & LLMFeedbackOutput)
| **Request Field** | **Datatype** | **Req/Opt** | **Response Field** | **Datatype** | **Resp/Opt** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `feedback` | STRING | Mandatory | `system_prompt` | STRING | Optional |
| | | | `user_prompt` | STRING | Mandatory |
