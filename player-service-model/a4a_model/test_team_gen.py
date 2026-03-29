import requests
import json

print("Testing /team/generate endpoint on port 8657...\n")

# Test 1: With seed_id
print("Test 1: With seed_id (aaronha01)")
try:
    r = requests.post(
        'http://localhost:8657/team/generate',
        json={'seed_id': 'aaronha01', 'team_size': 9},
        timeout=10
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}\n")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {str(e)}\n")

# Test 2: With features
print("Test 2: With features")
try:
    r = requests.post(
        'http://localhost:8657/team/generate',
        json={
            'features': {'height': 72, 'weight': 180, 'bats': 'R'},
            'team_size': 9
        },
        timeout=10
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}\n")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {str(e)}\n")
