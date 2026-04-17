#!/usr/bin/env python3
import requests
import time
import sys

def test_ancestors_with_token(token):
    url = "http://localhost:9380/api/v1/files/44b0cadc371611f1b1b31e71dcb42474/ancestors"
    headers = {"Authorization": f"Bearer {token}"}
    timeout = 30

    print(f"Testing {url} with token {token[:8]}...")
    start = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        elapsed = time.time() - start
        print(f"Response Status: {response.status_code}, Time: {elapsed:.2f}s")
        if response.status_code == 200:
            print(f"Success! Response length: {len(response.text)}")
            # print first 500 chars
            print(f"Preview: {response.text[:500]}")
            return True
        else:
            print(f"Error: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"Timeout after {elapsed:.2f}s - request took too long")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Use token from database
    token = "df5a47b43a0111f188cf291b2987bd47"
    success = test_ancestors_with_token(token)
    sys.exit(0 if success else 1)