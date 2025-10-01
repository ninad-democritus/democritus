"""
Refactored Pipeline Orchestrator using the new modular service architecture
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

# Infrastructure services
from ..infrastructure.spark_session_manager import SparkSessionManager
from ..infrastructure.minio_client_manager import MinioClientManager

# File operations services
from ..file_operations.file_discovery_service import FileDiscoveryService
from ..file_operations.file_reader_service import FileReaderService
from ..file_operations.file_processor_service import FileProcessorService
from ..file_operations.models import FileInfo, EntityFileMatch

# Data processing services
from ..data_processing.schema_validator_service import SchemaValidatorService
from ..data_processing.data_transformer_service import DataTransformerService
from ..data_processing.data_mapper_service import DataMapperService

# Catalog operations services
from ..catalog_operations.iceberg_catalog_service import IcebergCatalogService
from ..catalog_operations.iceberg_writer_service import IcebergWriterService
from ..catalog_operations.nessie_transaction_service import NessieTransactionService

# New refactored services
from ..metadata_operations.metadata_service import MetadataService
from ..file_operations.unified_file_service import UnifiedFileService

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Pipeline orchestrator using modular service architecture"""
    
    # Define granular pipeline stages
    PIPELINE_STAGES = [
        {"id": "file_discovery", "name": "File Discovery", "description": "Discovering and validating uploaded files"},
        {"id": "file_validation", "name": "File Validation", "description": "Validating file formats and accessibility"},
        {"id": "schema_validation", "name": "Schema Validation", "description": "Validating and creating data schemas"},
        {"id": "entity_mapping", "name": "Entity Mapping", "description": "Mapping files to entities"},
        {"id": "data_transformation", "name": "Data Transformation", "description": "Transforming and cleaning data"},
        {"id": "table_setup", "name": "Table Setup", "description": "Creating Iceberg tables and schemas"},
        {"id": "data_ingestion", "name": "Data Ingestion", "description": "Writing data to Iceberg tables"},
        {"id": "metadata_storage", "name": "Metadata Storage", "description": "Storing schema metadata"},
        {"id": "file_cleanup", "name": "File Cleanup", "description": "Cleaning up temporary files"}
    ]
    
    def __init__(self):
        """Initialize the pipeline orchestrator with all services"""
        
        # Infrastructure services
        self.spark_manager = SparkSessionManager()
        self.minio_manager = MinioClientManager()
        
        # File operations services
        self.file_discovery = FileDiscoveryService()
        self.file_reader = FileReaderService()
        self.file_processor = FileProcessorService()
        
        # Data processing services
        self.schema_validator = SchemaValidatorService()
        self.data_transformer = DataTransformerService()
        self.data_mapper = DataMapperService()
        
        # Catalog operations services
        self.iceberg_catalog = IcebergCatalogService()
        self.iceberg_writer = IcebergWriterService()
        self.nessie_transaction = NessieTransactionService()  # Not integrated in pipeline
        
        # Refactored services
        self.metadata_service = MetadataService()
        self.file_service = UnifiedFileService()
        
        # Set orchestrator references for services that need it
        self.file_service.set_orchestrator(self)
        
        # Initialize metadata service asynchronously when first used
        self._metadata_initialized = False
        
        # Pipeline run tracking
        self.pipeline_runs: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def get_pipeline_stages(cls):
        """Get list of all pipeline stages"""
        return cls.PIPELINE_STAGES
    
    async def execute_pipeline(self, run_id: str, job_id: str, schema_data: Dict[str, Any], websocket_manager=None) -> None:
        """
        Execute the complete data ingestion pipeline using the new modular architecture
        
        Args:
            run_id: Unique pipeline run identifier
            job_id: Job identifier from the workflow system
            schema_data: Complete schema data with entities, relationships, and metadata
            websocket_manager: WebSocket connection manager for real-time updates
        """
        logger.info(f"Starting refactored pipeline execution for run {run_id} (job: {job_id})")
        
        try:
            # Normalize schema data format
            normalized_schema = self._normalize_schema_data(schema_data)
            entities = normalized_schema.get('entities', [])
            
            if not entities:
                raise Exception("No entities found in schema data")
            
            # Initialize pipeline run tracking
            self.pipeline_runs[run_id] = {
                "status": "running",
                "job_id": job_id,
                "started_at": datetime.now().isoformat(),
                "step": "initializing",
                "steps_completed": [],
                "steps_failed": [],
                "file_summary": [],
                "total_records": 0,
                "total_files": 0,
                "entities_processed": 0
            }
            
            # Send initial status update
            await self._send_status_update(websocket_manager, run_id, "Starting modular data ingestion pipeline", "data_processing")
            
            # Add small delay to ensure WebSocket connection is established
            await asyncio.sleep(0.5)
            
            # Step 1: File Discovery
            await self._send_status_update(websocket_manager, run_id, "Discovering files for processing", "file_discovery")
            discovered_files = await self.file_discovery.discover_job_files(job_id)
            
            if not discovered_files:
                raise Exception(f"No files found for job {job_id}")
            
            logger.info(f"Discovered {len(discovered_files)} files")
            await self._send_status_update(websocket_manager, run_id, f"Discovered {len(discovered_files)} files", "file_discovery_complete")
            
            # Small delay to ensure status update is processed
            await asyncio.sleep(0.2)
            
            # Step 2: File Validation
            await self._send_status_update(websocket_manager, run_id, "Validating file formats and accessibility", "file_validation")
            validated_files = await self.file_discovery.validate_file_accessibility(discovered_files)
            
            if not validated_files:
                raise Exception("No valid files found after validation")
            
            logger.info(f"Validated {len(validated_files)} files")
            await self._send_status_update(websocket_manager, run_id, f"Validated {len(validated_files)} files", "file_validation_complete")
            
            # Small delay to ensure status update is processed
            await asyncio.sleep(0.2)
            
            # Step 3: Schema Validation
            await self._send_status_update(websocket_manager, run_id, "Creating and validating schemas", "schema_validation")
            entity_schemas = {}
            
            for entity in entities:
                entity_id = entity.get('id', entity.get('name', ''))
                spark_schema = self.schema_validator.create_spark_schema(entity)
                iceberg_schema = self.schema_validator.create_iceberg_schema(entity)
                
                entity_schemas[entity_id] = {
                    'entity': entity,
                    'spark_schema': spark_schema,
                    'iceberg_schema': iceberg_schema
                }
            
            logger.info(f"Created schemas for {len(entity_schemas)} entities")
            await self._send_status_update(websocket_manager, run_id, f"Created schemas for {len(entity_schemas)} entities", "schema_validation_complete")
            
            # Small delay to ensure status update is processed
            await asyncio.sleep(0.2)
            
            # Step 4: Entity Mapping
            await self._send_status_update(websocket_manager, run_id, "Mapping files to entities", "entity_mapping")
            entity_file_mappings = await self.data_mapper.map_entities_to_files(entities, validated_files)
            
            if not entity_file_mappings:
                raise Exception("No entity-file mappings could be created")
            
            logger.info(f"Created mappings for {len(entity_file_mappings)} entities")
            await self._send_status_update(websocket_manager, run_id, f"Mapped files to {len(entity_file_mappings)} entities", "entity_mapping_complete")
            
            # Small delay to ensure status update is processed
            await asyncio.sleep(0.2)
            
            # Step 5: Data Transformation
            await self._send_status_update(websocket_manager, run_id, "Transforming and cleaning data", "data_transformation")
            processed_data = {}
            
            for entity_id, file_mapping in entity_file_mappings.items():
                if entity_id not in entity_schemas:
                    logger.warning(f"No schema found for entity {entity_id}")
                    continue
                
                entity_info = entity_schemas[entity_id]
                entity = entity_info['entity']
                spark_schema = entity_info['spark_schema']
                
                # Process each file for this entity
                entity_dataframes = []
                
                for file_info in file_mapping.matched_files:
                    # Load file with expected schema
                    df = await self.file_processor.load_file_with_schema(file_info, spark_schema)
                    if df is None:
                        logger.error(f"Failed to load file {file_info.file_name}")
                        continue
                    
                    # Transform and clean data
                    transformed_df = await self.data_transformer.transform_data_for_entity(df, entity)
                    if transformed_df is None:
                        logger.error(f"Failed to transform data for entity {entity_id}")
                        continue
                    
                    cleaned_df = await self.data_transformer.clean_data(transformed_df, entity)
                    if cleaned_df is None:
                        logger.error(f"Failed to clean data for entity {entity_id}")
                        continue
                    
                    entity_dataframes.append(cleaned_df)
                
                if entity_dataframes:
                    # Union all DataFrames for this entity
                    if len(entity_dataframes) == 1:
                        final_df = entity_dataframes[0]
                    else:
                        final_df = entity_dataframes[0]
                        for df in entity_dataframes[1:]:
                            final_df = final_df.union(df)
                    
                    processed_data[entity_id] = {
                        'dataframe': final_df,
                        'entity': entity,
                        'iceberg_schema': entity_info['iceberg_schema']
                    }
            
            if not processed_data:
                raise Exception("No data could be processed")
            
            logger.info(f"Processed data for {len(processed_data)} entities")
            await self._send_status_update(websocket_manager, run_id, f"Processed data for {len(processed_data)} entities", "data_transformation_complete")
            
            # Mark data processing phase as complete
            await self._send_status_update(websocket_manager, run_id, "Data processing phase completed", "data_processing_complete")
            
            # Step 6: Table Setup
            await self._send_status_update(websocket_manager, run_id, "Setting up Iceberg tables", "table_setup")
            
            # Perform Iceberg catalog health check before proceeding
            try:
                catalog_health = await self.iceberg_catalog.health_check()
                if catalog_health["status"] != "healthy":
                    error_msg = f"Iceberg catalog not healthy: {', '.join(catalog_health.get('errors', []))}"
                    logger.error(error_msg)
                    await self._send_status_update(websocket_manager, run_id, error_msg, "table_setup_failed")
                    raise Exception(error_msg)
                else:
                    logger.info("Iceberg catalog health check passed")
            except Exception as e:
                logger.error(f"Iceberg catalog health check failed: {str(e)}")
                await self._send_status_update(websocket_manager, run_id, f"Catalog health check failed: {str(e)}", "table_setup_failed")
                raise
            
            for entity_id, data_info in processed_data.items():
                entity = data_info['entity']
                iceberg_schema = data_info['iceberg_schema']
                table_name = entity.get('name', entity_id).lower()
                
                # Ensure table exists
                success = await self.iceberg_catalog.ensure_table_exists(table_name, iceberg_schema)
                if not success:
                    logger.error(f"Failed to ensure table exists: {table_name}")
                    # Send explicit failure status for table setup
                    await self._send_status_update(websocket_manager, run_id, f"Failed to create table location", "table_setup_failed")
                    raise Exception(f"Failed to create table {table_name}")
            
            logger.info(f"Set up tables for {len(processed_data)} entities")
            await self._send_status_update(websocket_manager, run_id, f"Set up {len(processed_data)} Iceberg tables", "table_setup_complete")
            
            # Step 7: Data Ingestion
            await self._send_status_update(websocket_manager, run_id, "Writing data to Iceberg tables", "data_ingestion")
            
            total_records_written = 0
            successful_writes = 0
            
            for entity_id, data_info in processed_data.items():
                entity = data_info['entity']
                df = data_info['dataframe']
                table_name = entity.get('name', entity_id).lower()
                
                # Write data to table
                write_result = await self.iceberg_writer.write_data_to_table(df, table_name)
                
                if write_result.success:
                    successful_writes += 1
                    total_records_written += write_result.records_written
                    logger.info(f"Successfully wrote {write_result.records_written} records to {table_name}")
                else:
                    logger.error(f"Failed to write data to {table_name}: {write_result.error_message}")
                    raise Exception(f"Failed to write data to table {table_name}")
            
            logger.info(f"Successfully wrote {total_records_written} records to {successful_writes} tables")
            await self._send_status_update(websocket_manager, run_id, f"Wrote {total_records_written} records to {successful_writes} tables", "data_ingestion_complete")
            
            # Step 8: Metadata Storage
            await self._send_status_update(websocket_manager, run_id, "Storing schema metadata", "metadata_storage")
            
            try:
                # Ensure metadata service is initialized
                if not self._metadata_initialized:
                    logger.info("🔧 Initializing metadata service...")
                    metadata_init_result = await self.metadata_service.initialize()
                    if metadata_init_result:
                        logger.info("✅ Metadata service initialized successfully")
                        self._metadata_initialized = True
                    else:
                        logger.warning("⚠️ Metadata service initialization failed, will try fallback")
                
                result = await self.metadata_service.store_schema_metadata(run_id, job_id, normalized_schema, websocket_manager)
                if result.success:
                    logger.info("Successfully stored schema metadata")
                    await self._send_status_update(websocket_manager, run_id, "Stored schema metadata successfully", "metadata_storage_complete")
                else:
                    logger.warning(f"Metadata storage had issues: {result.errors}")
                    await self._send_status_update(websocket_manager, run_id, f"Metadata storage completed with warnings", "metadata_storage_complete")
            except Exception as e:
                logger.warning(f"Failed to store metadata: {str(e)}")
                await self._send_status_update(websocket_manager, run_id, f"Metadata storage failed: {str(e)}", "metadata_storage_failed")
                # Don't fail the entire pipeline for metadata issues
            
            # Step 9: File Cleanup
            await self._send_status_update(websocket_manager, run_id, "Cleaning up temporary files", "file_cleanup")
            
            try:
                await self.file_service.cleanup_source_files(run_id, job_id, websocket_manager)
                logger.info("Successfully cleaned up temporary files")
                await self._send_status_update(websocket_manager, run_id, "Cleaned up temporary files", "file_cleanup_complete")
            except Exception as e:
                logger.warning(f"File cleanup failed: {str(e)}")
                await self._send_status_update(websocket_manager, run_id, f"File cleanup failed: {str(e)}", "file_cleanup_failed")
                # Don't fail the entire pipeline for cleanup issues
            
            # Update pipeline run status
            self.pipeline_runs[run_id].update({
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "total_records": total_records_written,
                "total_files": len(validated_files),
                "entities_processed": len(processed_data)
            })
            
            # Send final success status
            await self._send_status_update(websocket_manager, run_id, "Pipeline completed successfully", "pipeline_complete", {
                "total_records": total_records_written,
                "total_files": len(validated_files),
                "entities_processed": len(processed_data),
                "duration": self._calculate_duration(run_id)
            })
            
            logger.info(f"Refactored pipeline execution completed successfully for run {run_id}")
            
        except Exception as e:
            logger.error(f"Refactored pipeline execution failed for run {run_id}: {str(e)}")
            
            # Update pipeline run status
            if run_id in self.pipeline_runs:
                self.pipeline_runs[run_id].update({
                    "status": "failed",
                    "failed_at": datetime.now().isoformat(),
                    "error_message": str(e)
                })
            
            # Send failure status
            await self._send_status_update(websocket_manager, run_id, f"Pipeline failed: {str(e)}", "pipeline_failed")
            raise
    
    def _normalize_schema_data(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize schema data to handle different relationship formats"""
        normalized_data = schema_data.copy()
        
        # Ensure entities exist
        if 'entities' not in normalized_data:
            normalized_data['entities'] = []
        
        # Normalize relationships format
        if 'relationships' in normalized_data:
            relationships = normalized_data['relationships']
            normalized_relationships = []
            
            for rel in relationships:
                if isinstance(rel, dict):
                    # Handle different relationship formats
                    # Support: from_entity/fromEntity/from, to_entity/toEntity/to, etc.
                    normalized_rel = {
                        'from_entity': rel.get('from_entity') or rel.get('fromEntity') or rel.get('from', ''),
                        'from_column': rel.get('from_column') or rel.get('fromColumn') or rel.get('foreign_key', ''),
                        'to_entity': rel.get('to_entity') or rel.get('toEntity') or rel.get('to', ''),
                        'to_column': rel.get('to_column') or rel.get('toColumn') or rel.get('references', ''),
                        'relationship_type': rel.get('relationship_type') or rel.get('relationshipType') or rel.get('type', 'one-to-many'),
                        'description': rel.get('description', '')
                    }
                    normalized_relationships.append(normalized_rel)
            
            normalized_data['relationships'] = normalized_relationships
        
        return normalized_data
    
    async def _send_status_update(self, websocket_manager, run_id: str, message: str, stage: str, data: Dict[str, Any] = None) -> None:
        """Send status update via WebSocket"""
        if websocket_manager is None:
            logger.warning(f"No websocket_manager provided for status update: {stage} - {message}")
            return
        
        # Determine status based on stage name
        def determine_status(stage: str, message: str) -> str:
            if any(word in stage.lower() for word in ["failed", "error", "exception"]):
                return "FAILED"
            elif any(word in message.lower() for word in ["failed", "error", "exception", "unsuccessful"]):
                return "FAILED"
            elif any(word in stage.lower() for word in ["completed", "complete", "finished", "success"]):
                if any(word in message.lower() for word in ["failed", "error", "unsuccessful"]):
                    return "FAILED"
                return "COMPLETED"
            elif any(word in stage.lower() for word in ["starting", "start", "preparing", "begin"]):
                return "STARTED"
            elif stage in ["completed", "pipeline_complete"]:
                return "COMPLETED"
            elif stage in ["failed", "pipeline_failed", "table_setup_failed", "metadata_storage_failed", "file_cleanup_failed"]:
                return "FAILED"
            else:
                return "STARTED"
        
        status = determine_status(stage, message)
        
        update_data = {
            "type": "status_update",
            "run_id": run_id,
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            update_data["data"] = data
        
        # Log the status update for debugging
        logger.info(f"📤 Sending status update: {stage} -> {status} | {message}")
        
        try:
            await websocket_manager.broadcast(json.dumps(update_data))
            logger.debug(f"✅ Status update sent successfully for stage: {stage}")
        except Exception as e:
            logger.error(f"❌ Failed to send status update for stage {stage}: {str(e)}")
    
    def _calculate_duration(self, run_id: str) -> Optional[float]:
        """Calculate pipeline duration in seconds"""
        if run_id not in self.pipeline_runs:
            return None
        
        run_info = self.pipeline_runs[run_id]
        started_at = run_info.get('started_at')
        
        if not started_at:
            return None
        
        try:
            start_time = datetime.fromisoformat(started_at)
            duration = (datetime.now() - start_time).total_seconds()
            return round(duration, 2)
        except Exception:
            return None
    
    def get_pipeline_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a pipeline run"""
        return self.pipeline_runs.get(run_id)
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services"""
        health_status = {
            "spark_session": self.spark_manager.is_session_active(),
            "minio_client": self.minio_manager.get_client_info().get("connected", False),
            "iceberg_catalog": True,  # Would need to implement health check
            "nessie_service": self.nessie_transaction.test_connection(),
            "metadata_service": True,  # Would need to implement health check
            "overall_health": "healthy"
        }
        
        # Determine overall health
        critical_services = ["spark_session", "minio_client", "iceberg_catalog"]
        if not all(health_status[service] for service in critical_services):
            health_status["overall_health"] = "unhealthy"
        
        return health_status
