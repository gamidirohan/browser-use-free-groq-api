#!/usr/bin/env python3
"""
Test script for the updated backend.py with JavaScript support
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_javascript_generation():
    """Test generating a JavaScript replay script"""
    
    # Test request with JavaScript language
    task_request = {
        "task": "Go to google.com and search for 'playwright javascript'",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "script_language": "javascript"
    }
    
    print("🧪 Testing JavaScript script generation...")
    print(f"📋 Task: {task_request['task']}")
    print(f"🔧 Script Language: {task_request['script_language']}")
    
    try:
        # Send request to backend
        response = requests.post(f"{BASE_URL}/run-agent", json=task_request)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Agent completed successfully!")
            print(f"📄 Script file: {result.get('script_file', 'N/A')}")
            print(f"🔧 Script language: {result.get('script_language', 'N/A')}")
            print(f"📝 Final result: {result.get('final_result', 'N/A')}")
            
            # Check script info
            script_info_response = requests.get(f"{BASE_URL}/script-info")
            if script_info_response.status_code == 200:
                script_info = script_info_response.json()
                print(f"📊 Available scripts: {script_info.get('available_scripts', [])}")
                print(f"🔧 Current language: {script_info.get('current_language', 'N/A')}")
            
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

def test_python_generation():
    """Test generating a Python replay script"""
    
    # Test request with Python language
    task_request = {
        "task": "Go to wikipedia.org and search for 'Python programming'",
        "model": "gpt-4o-mini", 
        "temperature": 0.0,
        "script_language": "python"
    }
    
    print("\n🧪 Testing Python script generation...")
    print(f"📋 Task: {task_request['task']}")
    print(f"🔧 Script Language: {task_request['script_language']}")
    
    try:
        # Send request to backend
        response = requests.post(f"{BASE_URL}/run-agent", json=task_request)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Agent completed successfully!")
            print(f"📄 Script file: {result.get('script_file', 'N/A')}")
            print(f"🔧 Script language: {result.get('script_language', 'N/A')}")
            print(f"📝 Final result: {result.get('final_result', 'N/A')}")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

def check_backend_status():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"🟢 Backend is running - Status: {status.get('status', 'unknown')}")
            return True
        else:
            print(f"🔴 Backend responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"🔴 Cannot connect to backend: {e}")
        print("💡 Make sure to start the backend with: python backend.py")
        return False

if __name__ == "__main__":
    print("🚀 Testing Updated Backend with JavaScript Support")
    print("=" * 50)
    
    # Check if backend is running
    if not check_backend_status():
        exit(1)
    
    # Test JavaScript generation
    js_success = test_javascript_generation()
    
    # Wait a bit between tests
    if js_success:
        print("\n⏳ Waiting 5 seconds before next test...")
        time.sleep(5)
        
        # Test Python generation
        py_success = test_python_generation()
        
        if js_success and py_success:
            print("\n🎉 All tests passed! Both JavaScript and Python generation work correctly.")
        else:
            print("\n⚠️ Some tests failed.")
    else:
        print("\n❌ JavaScript test failed, skipping Python test.")
