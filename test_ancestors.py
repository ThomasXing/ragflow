#!/usr/bin/env python3
import requests
import time
import sys

def test_ancestors_timeout():
    url = "http://localhost:9380/api/v1/files/44b0cadc371611f1b1b31e71dcb42474/ancestors"
    headers = {"Authorization": "Bearer dummy"}  # 可能需要有效 token，但先测试超时
    timeout = 30  # 30 秒超时

    print(f"Testing {url} with timeout {timeout}s")
    start = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        elapsed = time.time() - start
        print(f"Success! Status: {response.status_code}, Time: {elapsed:.2f}s")
        if response.status_code == 200:
            print(f"Response length: {len(response.text)}")
        else:
            print(f"Response: {response.text[:200]}")
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
    return True

def test_health():
    url = "http://localhost:9380/api/v1/health"
    try:
        response = requests.get(url, timeout=5)
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.text[:100]}")
    except Exception as e:
        print(f"Health check failed: {e}")

if __name__ == "__main__":
    print("=== Health Check ===")
    test_health()
    print("\n=== Ancestors Endpoint Test ===")
    success = test_ancestors_timeout()
    sys.exit(0 if success else 1)