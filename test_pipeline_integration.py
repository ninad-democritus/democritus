#!/usr/bin/env python3
"""
Comprehensive integration test for the data pipeline service.
Tests the complete flow: file upload -> schema processing -> Iceberg ingestion.
"""

import os
import sys
import json
import time
import uuid
import requests
import pandas as pd
from minio import Minio
from minio.error import S3Error
import websocket
import threading
from datetime import datetime
from typing import Dict, List, Any

class DataPipelineIntegrationTest:
    def __init__(self):
        self.base_url = "http://localhost"
        self.minio_endpoint = "localhost:9000"
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        self.test_job_id = f"test-job-{str(uuid.uuid4())[:8]}"
        self.websocket_messages = []
        self.ws = None
        
    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def upload_test_files_to_minio(self) -> List[str]:
        """Upload test CSV files to MinIO test buckets"""
        self.log("Step 1: Uploading test files to MinIO test buckets...")
        
        test_files = [
            "test_data/athlete_events.csv",
            "test_data/noc_regions.csv"
        ]
        
        uploaded_files = []
        
        try:
            # Ensure test uploads bucket exists
            if not self.minio_client.bucket_exists("testupload"):
                self.minio_client.make_bucket("testupload")
                self.log("Created 'testupload' bucket")
            
            # Ensure test data warehouse bucket exists
            if not self.minio_client.bucket_exists("testdata"):
                self.minio_client.make_bucket("testdata")
                self.log("Created 'testdata' bucket")
            
            for file_path in test_files:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Test file not found: {file_path}")
                
                filename = os.path.basename(file_path)
                file_id = str(uuid.uuid4())
                object_name = f"jobs/{self.test_job_id}/{file_id}/{filename}"
                
                self.log(f"Uploading {filename} to testupload/{object_name}")
                self.minio_client.fput_object("testupload", object_name, file_path)
                
                uploaded_files.append({
                    "file_id": file_id,
                    "filename": filename,
                    "object_name": object_name
                })
                
            self.log(f"Successfully uploaded {len(uploaded_files)} files to testupload bucket")
            return uploaded_files
            
        except Exception as e:
            self.log(f"Error uploading files: {str(e)}")
            raise
    
    def create_test_schema(self) -> Dict[str, Any]:
        """Create realistic schema for the test entities"""
        self.log("Step 2: Creating test schema...")
        
        schema = {
            "entities": [
                {
                    "name": "athlete_events",
                    "column_details": [
                        {"name": "ID", "data_type": "INTEGER", "primary_key": True, "nullable": False},
                        {"name": "Name", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Sex", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Age", "data_type": "INTEGER", "primary_key": False, "nullable": True},
                        {"name": "Height", "data_type": "DOUBLE", "primary_key": False, "nullable": True},
                        {"name": "Weight", "data_type": "DOUBLE", "primary_key": False, "nullable": True},
                        {"name": "Team", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "NOC", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Games", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Year", "data_type": "INTEGER", "primary_key": False, "nullable": False},
                        {"name": "Season", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "City", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Sport", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Event", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "Medal", "data_type": "STRING", "primary_key": False, "nullable": True}
                    ]
                },
                {
                    "name": "noc_regions",
                    "column_details": [
                        {"name": "NOC", "data_type": "STRING", "primary_key": True, "nullable": False},
                        {"name": "region", "data_type": "STRING", "primary_key": False, "nullable": False},
                        {"name": "notes", "data_type": "STRING", "primary_key": False, "nullable": True}
                    ]
                }
            ],
            "relationships": [
                {
                    "from": "athlete_events",
                    "to": "noc_regions",
                    "from_column": "NOC",
                    "to_column": "NOC",
                    "relationship_type": "many_to_one"
                }
            ]
        }
        
        self.log("Created schema with 2 entities and 1 relationship")
        return schema
    
    def setup_websocket_listener(self, run_id: str):
        """Setup WebSocket listener for real-time updates"""
        self.log("Step 3: Setting up WebSocket listener...")
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.websocket_messages.append(data)
                self.log(f"WebSocket: {data.get('step', 'unknown')} - {data.get('message', 'No message')}")
            except Exception as e:
                self.log(f"WebSocket error parsing message: {e}")
        
        def on_error(ws, error):
            self.log(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            self.log("WebSocket connection closed")
        
        def on_open(ws):
            self.log("WebSocket connection established")
        
        ws_url = f"ws://localhost/ws/v1/pipelines/status/{run_id}"
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Start WebSocket in a separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        time.sleep(2)  # Give WebSocket time to connect
    
    def trigger_pipeline(self, schema: Dict[str, Any]) -> str:
        """Trigger the data pipeline"""
        self.log("Step 4: Triggering data pipeline...")
        
        payload = {
            "job_id": self.test_job_id,
            "schema_data": schema
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/pipelines/trigger",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 202:
                result = response.json()
                run_id = result["pipelineRunId"]
                self.log(f"Pipeline triggered successfully. Run ID: {run_id}")
                return run_id
            else:
                raise Exception(f"Pipeline trigger failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log(f"Error triggering pipeline: {str(e)}")
            raise
    
    def wait_for_pipeline_completion(self, timeout: int = 300) -> bool:
        """Wait for pipeline to complete (success or failure)"""
        self.log("Step 5: Waiting for pipeline completion...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check latest WebSocket messages
            if self.websocket_messages:
                latest_message = self.websocket_messages[-1]
                status = latest_message.get('step', '')
                
                if status in ['completed', 'failed', 'pipeline_failed']:
                    self.log(f"Pipeline finished with status: {status}")
                    return status == 'completed'
            
            time.sleep(5)
        
        self.log("Pipeline completion timeout reached")
        return False
    
    def validate_results(self) -> bool:
        """Validate that the pipeline produced expected results"""
        self.log("Step 6: Validating results...")
        
        try:
            # Check if we have expected WebSocket messages
            if not self.websocket_messages:
                self.log("ERROR: No WebSocket messages received")
                return False
            
            # Print summary of messages
            self.log("\nWebSocket Message Summary:")
            for i, msg in enumerate(self.websocket_messages):
                step = msg.get('step', 'unknown')
                message = msg.get('message', 'No message')
                timestamp = msg.get('timestamp', 'No timestamp')
                self.log(f"  {i+1}. [{step}] {message} ({timestamp})")
            
            # Check for specific pipeline steps
            steps_received = [msg.get('step', '') for msg in self.websocket_messages]
            expected_steps = ['initializing', 'iceberg_ingestion']
            
            for expected_step in expected_steps:
                if expected_step not in steps_received:
                    self.log(f"WARNING: Expected step '{expected_step}' not found in messages")
            
            # Analyze final status
            final_message = self.websocket_messages[-1]
            final_status = final_message.get('step', '')
            
            if final_status == 'completed':
                self.log("Pipeline completed successfully!")
                
                # Check for summary data
                data = final_message.get('data', {})
                if data:
                    self.log(f"   Files processed: {data.get('total_files', 'N/A')}")
                    self.log(f"   Records processed: {data.get('total_records', 'N/A')}")
                
                # Validate data warehouse bucket has data
                self.validate_data_warehouse()
                    
                return True
            elif final_status == 'failed' or final_status == 'pipeline_failed':
                self.log("Pipeline failed")
                error = final_message.get('message', 'Unknown error')
                self.log(f"   Error: {error}")
                return False
            else:
                self.log(f"Pipeline status unclear: {final_status}")
                return False
                
        except Exception as e:
            self.log(f"Error validating results: {str(e)}")
            return False
    
    def validate_data_warehouse(self) -> bool:
        """Validate that data was written to the test data warehouse bucket"""
        self.log("   Validating test data warehouse bucket...")
        
        try:
            # Check if test data warehouse bucket has any objects
            warehouse_objects = list(self.minio_client.list_objects(
                "testdata", 
                prefix="warehouse/",
                recursive=True
            ))
            
            if warehouse_objects:
                self.log(f"   Found {len(warehouse_objects)} objects in test data warehouse")
                for obj in warehouse_objects[:5]:  # Show first 5 objects
                    self.log(f"     - {obj.object_name}")
                if len(warehouse_objects) > 5:
                    self.log(f"     ... and {len(warehouse_objects) - 5} more")
                return True
            else:
                self.log("   WARNING: No objects found in test data warehouse bucket")
                return False
                
        except Exception as e:
            self.log(f"   ERROR: Failed to validate test data warehouse: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up test resources"""
        self.log("Step 7: Cleaning up test resources...")
        
        try:
            # Close WebSocket
            if self.ws:
                self.ws.close()
            
            # Clean up MinIO objects from test uploads bucket
            try:
                objects_to_delete = self.minio_client.list_objects(
                    "testupload", 
                    prefix=f"jobs/{self.test_job_id}/",
                    recursive=True
                )
                
                for obj in objects_to_delete:
                    self.minio_client.remove_object("testupload", obj.object_name)
                    self.log(f"Deleted from testupload: {obj.object_name}")
            except Exception as e:
                self.log(f"Error cleaning testupload bucket: {e}")
            
            # Clean up MinIO objects from test data warehouse bucket
            try:
                warehouse_objects = self.minio_client.list_objects(
                    "testdata", 
                    prefix=f"warehouse/",
                    recursive=True
                )
                
                for obj in warehouse_objects:
                    self.minio_client.remove_object("testdata", obj.object_name)
                    self.log(f"Deleted from testdata warehouse: {obj.object_name}")
            except Exception as e:
                self.log(f"Error cleaning testdata warehouse bucket: {e}")
                
        except Exception as e:
            self.log(f"Error during cleanup: {str(e)}")
    
    def run_test(self) -> bool:
        """Run the complete integration test"""
        self.log("Starting Data Pipeline Integration Test")
        self.log(f"Test Job ID: {self.test_job_id}")
        
        try:
            # Step 1: Upload files
            uploaded_files = self.upload_test_files_to_minio()
            
            # Step 2: Create schema
            schema = self.create_test_schema()
            
            # Step 3: Trigger pipeline
            run_id = self.trigger_pipeline(schema)
            
            # Step 4: Setup WebSocket
            self.setup_websocket_listener(run_id)
            
            # Step 5: Wait for completion
            success = self.wait_for_pipeline_completion()
            
            # Step 6: Validate results
            validation_passed = self.validate_results()
            
            # Step 7: Cleanup
            self.cleanup()
            
            # Final result
            overall_success = success and validation_passed
            
            self.log("\n" + "="*60)
            if overall_success:
                self.log("INTEGRATION TEST PASSED! Data pipeline is working correctly.")
            else:
                self.log("INTEGRATION TEST FAILED! Issues found in data pipeline.")
            self.log("="*60)
            
            return overall_success
            
        except Exception as e:
            self.log(f"Test failed with exception: {str(e)}")
            self.cleanup()
            return False

def main():
    """Main test runner"""
    test = DataPipelineIntegrationTest()
    success = test.run_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
