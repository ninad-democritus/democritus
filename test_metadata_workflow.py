#!/usr/bin/env python3
"""
Test script to verify the metadata storage workflow with OpenMetadata
"""

import requests
import json
import time
import sys

def test_openmetadata_health():
    """Test if OpenMetadata is healthy"""
    print("🔍 Testing OpenMetadata health...")
    try:
        response = requests.get("http://localhost:8585/api/v1/system/status", timeout=10)
        if response.status_code == 200:
            print("✅ OpenMetadata is healthy!")
            return True
        else:
            print(f"❌ OpenMetadata health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ OpenMetadata connection failed: {str(e)}")
        return False

def test_airflow_connection():
    """Test if Airflow is accessible"""
    print("🔍 Testing Airflow connection...")
    try:
        response = requests.get("http://localhost:8081/health", timeout=10)
        if response.status_code == 200:
            print("✅ Airflow is accessible!")
            return True
        else:
            print(f"❌ Airflow connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Airflow connection failed: {str(e)}")
        return False

def test_data_pipeline_trigger():
    """Test triggering the data pipeline with sample schema"""
    print("🔍 Testing data pipeline trigger...")
    
    # Sample schema data for testing
    sample_schema = {
        "entities": [
            {
                "name": "TestCustomers",
                "table_name": "test_customers",
                "description": "Test customer data",
                "business_description": "Customer information for testing metadata workflow",
                "business_purpose": "Store customer demographic and contact information",
                "domain_classification": "Customer Data",
                "key_business_attributes": ["customer_id", "email", "registration_date"],
                "suggested_use_cases": ["Customer analytics", "Marketing campaigns"],
                "column_details": [
                    {
                        "name": "customer_id",
                        "data_type": "INTEGER",
                        "nullable": False,
                        "primary_key": True,
                        "unique": True,
                        "description": "Unique customer identifier",
                        "tags": ["Identifier", "PII"]
                    },
                    {
                        "name": "email",
                        "data_type": "VARCHAR(255)",
                        "nullable": False,
                        "primary_key": False,
                        "unique": True,
                        "description": "Customer email address",
                        "tags": ["Contact", "PII"]
                    },
                    {
                        "name": "first_name",
                        "data_type": "VARCHAR(100)",
                        "nullable": False,
                        "primary_key": False,
                        "unique": False,
                        "description": "Customer first name",
                        "tags": ["PII"]
                    },
                    {
                        "name": "registration_date",
                        "data_type": "TIMESTAMP",
                        "nullable": False,
                        "primary_key": False,
                        "unique": False,
                        "description": "Date when customer registered",
                        "tags": ["Temporal", "Audit"]
                    }
                ]
            },
            {
                "name": "TestOrders",
                "table_name": "test_orders",
                "description": "Test order data",
                "business_description": "Order transactions for testing metadata workflow",
                "business_purpose": "Track customer orders and purchase history",
                "domain_classification": "Transaction Data",
                "key_business_attributes": ["order_id", "customer_id", "order_total"],
                "suggested_use_cases": ["Sales analytics", "Revenue reporting"],
                "column_details": [
                    {
                        "name": "order_id",
                        "data_type": "INTEGER",
                        "nullable": False,
                        "primary_key": True,
                        "unique": True,
                        "description": "Unique order identifier",
                        "tags": ["Identifier"]
                    },
                    {
                        "name": "customer_id",
                        "data_type": "INTEGER",
                        "nullable": False,
                        "primary_key": False,
                        "unique": False,
                        "description": "Reference to customer",
                        "tags": ["Identifier", "Foreign Key"]
                    },
                    {
                        "name": "order_total",
                        "data_type": "DECIMAL",
                        "nullable": False,
                        "primary_key": False,
                        "unique": False,
                        "description": "Total order amount",
                        "tags": ["Financial", "Measurement"]
                    }
                ]
            }
        ],
        "relationships": [
            {
                "from": "TestOrders",
                "to": "TestCustomers", 
                "from_column": "customer_id",
                "to_column": "customer_id",
                "relationship_type": "many_to_one",
                "confidence": 0.95
            }
        ],
        "businessTags": {
            "PII": ["customer_id", "email", "first_name"],
            "Financial": ["order_total"],
            "Temporal": ["registration_date"]
        },
        "business_summary": "Test dataset for validating metadata workflow"
    }
    
    # Trigger pipeline
    try:
        payload = {
            "job_id": "test_metadata_workflow_001",
            "schema_data": sample_schema
        }
        
        response = requests.post(
            "http://localhost/v1/pipelines/trigger",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 202:
            result = response.json()
            print("✅ Pipeline triggered successfully!")
            print(f"   Pipeline Run ID: {result.get('pipelineRunId')}")
            print(f"   Airflow DAG Run: {result.get('airflow_dag_run_id')}")
            return result.get('airflow_dag_run_id')
        else:
            print(f"❌ Pipeline trigger failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Pipeline trigger failed: {str(e)}")
        return None

def check_airflow_dag_status(dag_run_id):
    """Check the status of the Airflow DAG run"""
    if not dag_run_id:
        return False
        
    print(f"🔍 Checking Airflow DAG status for: {dag_run_id}")
    
    try:
        # Check DAG run status
        response = requests.get(
            f"http://localhost/v1/pipelines/status/{dag_run_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            status = response.json()
            state = status.get('state', 'unknown')
            print(f"✅ DAG Run Status: {state}")
            
            if state == 'success':
                print("🎉 DAG completed successfully!")
                return True
            elif state == 'failed':
                print("❌ DAG execution failed!")
                return False
            else:
                print(f"⏳ DAG is still running (state: {state})")
                return None  # Still running
        else:
            print(f"❌ Failed to get DAG status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check DAG status: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Metadata Workflow Test")
    print("=" * 50)
    
    # Test 1: OpenMetadata Health
    if not test_openmetadata_health():
        print("❌ OpenMetadata is not ready. Please wait for it to start.")
        return False
    
    # Test 2: Airflow Connection
    if not test_airflow_connection():
        print("❌ Airflow is not ready. Please wait for it to start.")
        return False
    
    # Test 3: Trigger Pipeline
    dag_run_id = test_data_pipeline_trigger()
    if not dag_run_id:
        print("❌ Failed to trigger pipeline")
        return False
    
    # Test 4: Monitor DAG execution
    print("\n⏳ Monitoring DAG execution...")
    max_attempts = 12  # 2 minutes with 10-second intervals
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"   Attempt {attempt}/{max_attempts}")
        
        status = check_airflow_dag_status(dag_run_id)
        
        if status is True:
            print("\n🎉 Metadata workflow test completed successfully!")
            print("\n📋 Next Steps:")
            print("   1. Check OpenMetadata UI: http://localhost:8585")
            print("   2. Check Airflow UI: http://localhost:8081")
            print("   3. Verify tables are created in the metadata store")
            return True
        elif status is False:
            print("\n❌ Metadata workflow test failed!")
            return False
        else:
            # Still running, wait and retry
            time.sleep(10)
    
    print("\n⏰ DAG execution is taking longer than expected")
    print("   Check Airflow UI for detailed status: http://localhost:8081")
    return None

if __name__ == "__main__":
    success = main()
    if success is True:
        sys.exit(0)
    elif success is False:
        sys.exit(1)
    else:
        sys.exit(2)  # Timeout/unknown status
