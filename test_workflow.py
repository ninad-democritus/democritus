#!/usr/bin/env python3
"""
Quick test script to verify the agent workflow is working properly.
Run this to test the workflow without going through the full UI.
"""

import requests
import json
import time

def test_agent_workflow():
    print("🔍 Testing Agent Workflow Integration...")
    
    # Test 1: Generate upload URLs for batch files
    print("\n1. Testing batch upload URL generation...")
    batch_request = {
        "files": [
            {"fileName": "test_customers.csv", "fileType": "text/csv"},
            {"fileName": "test_orders.xlsx", "fileType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        ]
    }
    
    try:
        response = requests.post('http://localhost/v1/files/batch-upload-urls', 
                               json=batch_request, timeout=10)
        if response.status_code == 200:
            batch_data = response.json()
            job_id = batch_data['jobId']
            print(f"✅ Batch upload URLs generated successfully")
            print(f"   Job ID: {job_id}")
            print(f"   Upload URLs count: {len(batch_data['uploads'])}")
        else:
            print(f"❌ Batch upload URL generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error generating batch upload URLs: {e}")
        return False
    
    # Test 2: Start agent workflow
    print(f"\n2. Testing agent workflow start with job ID: {job_id}...")
    workflow_request = {
        "jobId": job_id,
        "sourceType": "batch"
    }
    
    try:
        response = requests.post('http://localhost/v1/workflows/start-job',
                               json=workflow_request, timeout=10)
        if response.status_code == 202:
            workflow_data = response.json()
            workflow_id = workflow_data['workflowId']
            print(f"✅ Agent workflow started successfully")
            print(f"   Workflow ID: {workflow_id}")
            print(f"   WebSocket URL: {workflow_data['websocketUrl']}")
            
            # Wait a bit for workflow to process
            print("\n3. Waiting for workflow to process...")
            time.sleep(5)
            
            return True
        else:
            print(f"❌ Agent workflow start failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error starting agent workflow: {e}")
        return False

def test_service_health():
    print("🏥 Testing service health...")
    
    services = [
        ("Frontend", "http://localhost/"),
        ("File Upload", "http://localhost/v1/files/"),
        ("Agent Workflow", "http://localhost/v1/workflows/")
    ]
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 404, 405]:  # 404/405 are OK for API endpoints
                print(f"✅ {name} service is reachable")
            else:
                print(f"⚠️  {name} service returned {response.status_code}")
        except Exception as e:
            print(f"❌ {name} service is unreachable: {e}")

if __name__ == "__main__":
    print("🚀 Democritus Agent Workflow Test")
    print("="*50)
    
    test_service_health()
    print("\n" + "="*50)
    test_agent_workflow()
    
    print(f"\n🎯 Test completed! Check the results above.")
    print("If agent workflow started successfully, check LangSmith dashboard for traces:")
    print("https://smith.langchain.com/projects/democritus-agents")




