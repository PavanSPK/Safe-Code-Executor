import requests
import json

# API endpoint
API_URL = "http://localhost:5000/run"

def test_code(name, code):
    """Helper function to test code execution"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Code:\n{code}\n")
    
    try:
        response = requests.post(
            API_URL,
            json={"code": code},
            timeout=15
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

# Test 1: Normal execution
test_code(
    "Normal Execution",
    "print('Hello, World!')\nprint(2 + 2)"
)

# Test 2: Infinite loop (should timeout)
test_code(
    "Infinite Loop Attack",
    "while True:\n    pass"
)

# Test 3: Memory bomb (should fail)
test_code(
    "Memory Attack",
    "x = 'a' * 1000000000"
)

# Test 4: Network access (should fail)
test_code(
    "Network Attack",
    "import urllib.request\nurllib.request.urlopen('http://google.com')"
)

# Test 5: File write (should fail)
test_code(
    "File Write Attack",
    "with open('/tmp/hack.txt', 'w') as f:\n    f.write('hacked')"
)

# Test 6: File read from host (should fail or show container files only)
test_code(
    "File Read Attack",
    "with open('/etc/passwd', 'r') as f:\n    print(f.read())"
)

# Test 7: Long code (should fail)
test_code(
    "Code Length Attack",
    "print('x')" * 2000  # Creates very long code
)

print(f"\n{'='*60}")
print("TESTING COMPLETE")
print(f"{'='*60}")