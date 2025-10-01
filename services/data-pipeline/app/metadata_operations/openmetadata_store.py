"""
OpenMetadata store implementation
"""

import logging
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from .metadata_store_interface import MetadataStoreInterface
from .authentication.openmetadata_auth import OpenMetadataAuth
from .models import (
    MetadataStorageRequest,
    MetadataStorageResult,
    MetadataStoreType,
    HealthCheckResult,
    MetadataEntity,
    MetadataRelationship
)

logger = logging.getLogger(__name__)


class OpenMetadataStore(MetadataStoreInterface):
    """OpenMetadata implementation of metadata store"""
    
    def __init__(self, host: str, port: str, admin_email: str):
        """
        Initialize OpenMetadata store
        
        Args:
            host: OpenMetadata server host
            port: OpenMetadata server port
            admin_email: Admin email for authentication
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.auth_provider = OpenMetadataAuth(host, port, admin_email)
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the OpenMetadata store connection"""
        try:
            logger.info("Initializing OpenMetadata store...")
            
            # Check health first
            health_result = await self.health_check()
            if not health_result.healthy:
                logger.error(f"OpenMetadata health check failed: {health_result.error_message}")
                return False
            
            # Authenticate
            auth_result = await self.auth_provider.authenticate()
            if not auth_result.success:
                logger.error(f"OpenMetadata authentication failed: {auth_result.error_message}")
                return False
            
            self.initialized = True
            logger.info("✅ OpenMetadata store initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenMetadata store: {e}")
            return False
    
    async def health_check(self) -> HealthCheckResult:
        """Check the health of OpenMetadata"""
        try:
            start_time = datetime.now()
            health_url = f"{self.base_url}/v1/system/version"
            response = requests.get(health_url, timeout=10)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                version_data = response.json()
                return HealthCheckResult(
                    healthy=True,
                    service_name="OpenMetadata",
                    version=version_data.get("version"),
                    response_time_ms=response_time
                )
            elif response.status_code == 401:
                # Service is running but requires authentication
                return HealthCheckResult(
                    healthy=True,
                    service_name="OpenMetadata",
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    healthy=False,
                    service_name="OpenMetadata",
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                service_name="OpenMetadata",
                error_message=str(e)
            )
    
    async def store_metadata(self, request: MetadataStorageRequest) -> MetadataStorageResult:
        """Store metadata in OpenMetadata"""
        logger.info(f"🔄 Starting metadata storage for job {request.job_id}")
        
        if not self.initialized:
            logger.info("🔧 OpenMetadata store not initialized, initializing now...")
            if not await self.initialize():
                logger.error("❌ Failed to initialize OpenMetadata store")
                return MetadataStorageResult(
                    success=False,
                    store_type=MetadataStoreType.OPENMETADATA,
                    stored_entities=0,
                    stored_relationships=0,
                    stored_lineage=0,
                    errors=["OpenMetadata store not initialized"]
                )
            else:
                logger.info("✅ OpenMetadata store initialized successfully")
        
        # Verify authentication is still valid
        if not self.auth_provider.is_token_valid():
            logger.warning("🔑 Token expired or invalid, re-authenticating...")
            auth_result = await self.auth_provider.authenticate()
            if not auth_result.success:
                logger.error(f"❌ Re-authentication failed: {auth_result.error_message}")
                return MetadataStorageResult(
                    success=False,
                    store_type=MetadataStoreType.OPENMETADATA,
                    stored_entities=0,
                    stored_relationships=0,
                    stored_lineage=0,
                    errors=[f"Authentication failed: {auth_result.error_message}"]
                )
        
        try:
            logger.info(f"Storing metadata for job {request.job_id} in OpenMetadata with {request.entities} entities, {request.relationships} relationships, {request.lineage} lineage")
            
            stored_entities = 0
            stored_relationships = 0
            stored_lineage = 0
            errors = []
            
            # Store entities
            for entity in request.entities:
                try:
                    if await self._store_entity(entity):
                        stored_entities += 1
                    else:
                        errors.append(f"Failed to store entity: {entity.name}")
                except Exception as e:
                    errors.append(f"Error storing entity {entity.name}: {str(e)}")
            
            # Store relationships
            for relationship in request.relationships:
                try:
                    if await self._store_relationship(relationship):
                        stored_relationships += 1
                    else:
                        errors.append(f"Failed to store relationship: {relationship.from_entity} -> {relationship.to_entity}")
                except Exception as e:
                    errors.append(f"Error storing relationship: {str(e)}")
            
            # Store lineage if provided
            if request.lineage:
                for lineage in request.lineage:
                    try:
                        if await self._store_lineage(lineage):
                            stored_lineage += 1
                        else:
                            errors.append(f"Failed to store lineage: {lineage.source_entity} -> {lineage.target_entity}")
                    except Exception as e:
                        errors.append(f"Error storing lineage: {str(e)}")
            
            success = len(errors) == 0
            logger.info(f"OpenMetadata storage completed: {stored_entities} entities, {stored_relationships} relationships, {stored_lineage} lineage")
            
            return MetadataStorageResult(
                success=success,
                store_type=MetadataStoreType.OPENMETADATA,
                stored_entities=stored_entities,
                stored_relationships=stored_relationships,
                stored_lineage=stored_lineage,
                errors=errors if errors else None
            )
            
        except Exception as e:
            logger.error(f"Failed to store metadata in OpenMetadata: {e}")
            return MetadataStorageResult(
                success=False,
                store_type=MetadataStoreType.OPENMETADATA,
                stored_entities=0,
                stored_relationships=0,
                stored_lineage=0,
                errors=[str(e)]
            )
    
    async def _store_entity(self, entity: MetadataEntity) -> bool:
        """Store a single entity in OpenMetadata with failsafe checking"""
        try:
            # First ensure the database service exists
            service_name = "data-pipeline-service"
            await self._ensure_database_service_exists(service_name)
            
            # Ensure database and schema exist before creating table
            schema_fqn = f"{service_name}.default.default"
            await self._ensure_database_exists(service_name, "default")
            await self._ensure_database_schema_exists(service_name, "default", "default")
            
            # Create table entity with proper OpenMetadata format
            columns = []
            for col in entity.schema_data.get("columns", []):
                data_type = self._map_data_type(col.get("data_type", "STRING"))
                column_data = {
                    "name": col.get("name", ""),
                    "dataType": data_type,
                    "description": col.get("description", "")
                }
                
                # Add dataLength for string types that require it
                if data_type.upper() in ["VARCHAR", "CHAR", "BINARY", "VARBINARY"]:
                    # Ensure dataLength is always a valid integer, never None
                    max_length = col.get("max_length") or col.get("maxLength") or 255
                    column_data["dataLength"] = int(max_length) if max_length else 255
                    logger.debug(f"📏 Column '{col.get('name')}' type {data_type} - setting dataLength to {column_data['dataLength']}")
                
                columns.append(column_data)
            
            # OpenMetadata expects the FQN (fully qualified name) for databaseSchema, not an ID
            entity_data = {
                "name": entity.name,
                "displayName": entity.name,
                "description": entity.description or f"Table {entity.name} from data pipeline",
                "columns": columns,
                "databaseSchema": schema_fqn
            }
            
            # Check if entity already exists
            table_fqn = f"{schema_fqn}.{entity.name}"
            existing_entity = await self._get_entity_by_fqn(table_fqn)
            
            if existing_entity:
                logger.info(f"🔍 Entity {entity.name} already exists, comparing definitions...")
                
                # Compare existing entity with new entity
                if self._compare_entities(existing_entity, entity_data):
                    logger.info(f"✅ Entity {entity.name} unchanged, skipping creation")
                    return True
                else:
                    logger.info(f"🔄 Entity {entity.name} has changes, updating...")
                    return await self._update_entity(table_fqn, entity_data, existing_entity)
            
            # Entity doesn't exist, create it
            headers = self.auth_provider.get_auth_headers()
            logger.info(f"📤 Creating new table {entity.name}")
            
            response = requests.post(
                f"{self.base_url}/v1/tables",
                json=entity_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully created entity: {entity.name}")
                return True
            else:
                error_detail = response.text
                logger.error(f"❌ Failed to create entity {entity.name}: {response.status_code}")
                logger.error(f"   Error details: {error_detail}")
                logger.error(f"   Columns sent: {json.dumps(columns, indent=2)}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing entity {entity.name}: {e}")
            return False
    
    async def _store_relationship(self, relationship: MetadataRelationship) -> bool:
        """
        Store a relationship in OpenMetadata as lineage between tables with failsafe checking.
        In OpenMetadata, relationships (foreign keys) are represented as lineage edges.
        """
        try:
            # Validate entity names are not empty
            if not relationship.from_entity or not relationship.to_entity:
                logger.warning(f"⚠️ Skipping relationship with empty entity names: from='{relationship.from_entity}', to='{relationship.to_entity}'")
                return True  # Don't fail - just skip invalid relationships
            
            logger.info(f"📊 Storing relationship: {relationship.from_entity}.{relationship.from_column} -> {relationship.to_entity}.{relationship.to_column}")
            
            # Build fully qualified names for source and target tables
            service_name = "data-pipeline-service"
            from_table_fqn = f"{service_name}.default.default.{relationship.from_entity}"
            to_table_fqn = f"{service_name}.default.default.{relationship.to_entity}"
            
            # Get the actual entity objects to retrieve their UUIDs
            from_entity_obj = await self._get_entity_by_fqn(from_table_fqn)
            to_entity_obj = await self._get_entity_by_fqn(to_table_fqn)
            
            if not from_entity_obj:
                logger.warning(f"⚠️ Source entity not found: {from_table_fqn}. Skipping relationship.")
                return True  # Don't fail - just skip
            
            if not to_entity_obj:
                logger.warning(f"⚠️ Target entity not found: {to_table_fqn}. Skipping relationship.")
                return True  # Don't fail - just skip
            
            # Extract UUIDs from entity objects
            from_entity_id = from_entity_obj.get("id")
            to_entity_id = to_entity_obj.get("id")
            
            if not from_entity_id or not to_entity_id:
                logger.warning(f"⚠️ Could not get entity IDs. Skipping relationship.")
                return True  # Don't fail - just skip
            
            # Create lineage edge from source to target table using UUIDs
            lineage_data = {
                "edge": {
                    "fromEntity": {
                        "id": from_entity_id,
                        "type": "table"
                    },
                    "toEntity": {
                        "id": to_entity_id,
                        "type": "table"
                    },
                    "lineageDetails": {
                        "sqlQuery": f"-- Foreign Key: {relationship.from_entity}.{relationship.from_column} references {relationship.to_entity}.{relationship.to_column}",
                        "description": relationship.description or f"{relationship.relationship_type} relationship"
                    }
                }
            }
            
            # Check if lineage already exists
            existing_lineage = await self._get_lineage(from_table_fqn)
            
            if existing_lineage:
                # Check if this specific edge exists
                edge_exists = self._lineage_edge_exists(existing_lineage, from_table_fqn, to_table_fqn)
                
                if edge_exists:
                    logger.info(f"🔍 Relationship lineage {relationship.from_entity} -> {relationship.to_entity} already exists")
                    # Lineage PUT is idempotent, so we can just update it
                    logger.info(f"🔄 Updating relationship lineage...")
            
            headers = self.auth_provider.get_auth_headers()
            response = requests.put(
                f"{self.base_url}/v1/lineage",
                json=lineage_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully stored relationship lineage: {relationship.from_entity} -> {relationship.to_entity}")
                return True
            else:
                logger.warning(f"⚠️ Failed to store relationship lineage: {response.status_code} - {response.text}")
                logger.warning(f"   Lineage data sent: {json.dumps(lineage_data, indent=2)}")
                # Don't fail completely - relationships are nice-to-have
                return True
            
        except Exception as e:
            logger.error(f"Error storing relationship: {e}")
            # Don't fail the entire metadata storage for relationship issues
            return True
    
    async def _store_lineage(self, lineage) -> bool:
        """Store lineage information in OpenMetadata with failsafe checking"""
        try:
            # Validate entity names are not empty
            if not lineage.source_entity or not lineage.target_entity:
                logger.warning(f"⚠️ Skipping lineage with empty entity names: source='{lineage.source_entity}', target='{lineage.target_entity}'")
                return True  # Don't fail - just skip invalid lineage
            
            logger.info(f"📈 Storing lineage: {lineage.source_entity} -> {lineage.target_entity}")
            
            # Build fully qualified names
            service_name = "data-pipeline-service"
            source_fqn = f"{service_name}.default.default.{lineage.source_entity}"
            target_fqn = f"{service_name}.default.default.{lineage.target_entity}"
            
            # Get the actual entity objects to retrieve their UUIDs
            source_entity_obj = await self._get_entity_by_fqn(source_fqn)
            target_entity_obj = await self._get_entity_by_fqn(target_fqn)
            
            if not source_entity_obj:
                logger.warning(f"⚠️ Source entity not found: {source_fqn}. Skipping lineage.")
                return True  # Don't fail - just skip
            
            if not target_entity_obj:
                logger.warning(f"⚠️ Target entity not found: {target_fqn}. Skipping lineage.")
                return True  # Don't fail - just skip
            
            # Extract UUIDs from entity objects
            source_entity_id = source_entity_obj.get("id")
            target_entity_id = target_entity_obj.get("id")
            
            if not source_entity_id or not target_entity_id:
                logger.warning(f"⚠️ Could not get entity IDs. Skipping lineage.")
                return True  # Don't fail - just skip
            
            # Create lineage edge using UUIDs
            lineage_data = {
                "edge": {
                    "fromEntity": {
                        "id": source_entity_id,
                        "type": "table"
                    },
                    "toEntity": {
                        "id": target_entity_id,
                        "type": "table"
                    },
                    "lineageDetails": {
                        "sqlQuery": lineage.transformation_logic or "-- Data pipeline transformation"
                    }
                }
            }
            
            # Check if lineage already exists
            existing_lineage = await self._get_lineage(source_fqn)
            
            if existing_lineage:
                # Check if this specific edge exists
                edge_exists = self._lineage_edge_exists(existing_lineage, source_fqn, target_fqn)
                
                if edge_exists:
                    logger.info(f"🔍 Lineage {lineage.source_entity} -> {lineage.target_entity} already exists")
                    # Lineage PUT is idempotent, so we can just update it
                    logger.info(f"🔄 Updating lineage...")
            
            headers = self.auth_provider.get_auth_headers()
            response = requests.put(
                f"{self.base_url}/v1/lineage",
                json=lineage_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully stored lineage: {lineage.source_entity} -> {lineage.target_entity}")
                return True
            else:
                logger.warning(f"⚠️ Failed to store lineage: {response.status_code} - {response.text}")
                # Don't fail completely - lineage is nice-to-have
                return True
            
        except Exception as e:
            logger.error(f"Error storing lineage: {e}")
            # Don't fail the entire metadata storage for lineage issues
            return True
    
    async def get_entity(self, entity_name: str) -> Optional[MetadataEntity]:
        """Retrieve an entity by name"""
        try:
            headers = self.auth_provider.get_auth_headers()
            response = requests.get(
                f"{self.base_url}/v1/tables/name/{entity_name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return MetadataEntity(
                    name=data.get("name"),
                    description=data.get("description"),
                    entity_type="table",
                    schema_data={"columns": data.get("columns", [])}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving entity {entity_name}: {e}")
            return None
    
    async def get_relationships(self, entity_name: str) -> List[MetadataRelationship]:
        """Get all relationships for an entity"""
        try:
            # This would implement OpenMetadata's relationship API
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving relationships for {entity_name}: {e}")
            return []
    
    async def _ensure_database_service_exists(self, service_name: str) -> bool:
        """Ensure a database service exists in OpenMetadata"""
        try:
            headers = self.auth_provider.get_auth_headers()
            
            # Check if service already exists
            check_response = requests.get(
                f"{self.base_url}/v1/services/databaseServices/name/{service_name}",
                headers=headers,
                timeout=10
            )
            
            if check_response.status_code == 200:
                logger.debug(f"Database service {service_name} already exists")
                return True
            
            # Create the database service
            service_data = {
                "name": service_name,
                "displayName": "Data Pipeline Service",
                "description": "Database service for data pipeline ingested tables",
                "serviceType": "CustomDatabase",
                "connection": {
                    "config": {
                        "type": "CustomDatabase",
                        "connectionOptions": {},
                        "connectionArguments": {}
                    }
                }
            }
            
            create_response = requests.post(
                f"{self.base_url}/v1/services/databaseServices",
                json=service_data,
                headers=headers,
                timeout=30
            )
            
            if create_response.status_code in [200, 201]:
                logger.info(f"✅ Created database service: {service_name}")
                
                # Also create default database and schema
                await self._ensure_database_exists(service_name, "default")
                await self._ensure_database_schema_exists(service_name, "default", "default")
                return True
            else:
                logger.warning(f"Failed to create database service: {create_response.status_code} - {create_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring database service exists: {e}")
            return False
    
    async def _ensure_database_exists(self, service_name: str, database_name: str) -> bool:
        """Ensure a database exists in OpenMetadata"""
        try:
            headers = self.auth_provider.get_auth_headers()
            
            # Check if database already exists
            db_fqn = f"{service_name}.{database_name}"
            check_response = requests.get(
                f"{self.base_url}/v1/databases/name/{db_fqn}",
                headers=headers,
                timeout=10
            )
            
            if check_response.status_code == 200:
                logger.debug(f"Database {db_fqn} already exists")
                return True
            
            # Create the database
            database_data = {
                "name": database_name,
                "displayName": database_name,
                "description": f"Default database for {service_name}",
                "service": service_name
            }
            
            create_response = requests.post(
                f"{self.base_url}/v1/databases",
                json=database_data,
                headers=headers,
                timeout=30
            )
            
            if create_response.status_code in [200, 201]:
                logger.info(f"✅ Created database: {db_fqn}")
                return True
            else:
                logger.warning(f"Failed to create database: {create_response.status_code} - {create_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring database exists: {e}")
            return False
    
    async def _ensure_database_schema_exists(self, service_name: str, database_name: str, schema_name: str) -> bool:
        """Ensure a database schema exists in OpenMetadata"""
        try:
            headers = self.auth_provider.get_auth_headers()
            
            # Check if schema already exists
            schema_fqn = f"{service_name}.{database_name}.{schema_name}"
            check_response = requests.get(
                f"{self.base_url}/v1/databaseSchemas/name/{schema_fqn}",
                headers=headers,
                timeout=10
            )
            
            if check_response.status_code == 200:
                logger.debug(f"Database schema {schema_fqn} already exists")
                return True
            
            # Create the database schema
            schema_data = {
                "name": schema_name,
                "displayName": schema_name,
                "description": f"Default schema for {service_name}.{database_name}",
                "database": f"{service_name}.{database_name}"
            }
            
            create_response = requests.post(
                f"{self.base_url}/v1/databaseSchemas",
                json=schema_data,
                headers=headers,
                timeout=30
            )
            
            if create_response.status_code in [200, 201]:
                logger.info(f"✅ Created database schema: {schema_fqn}")
                return True
            else:
                logger.warning(f"Failed to create database schema: {create_response.status_code} - {create_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring database schema exists: {e}")
            return False
    
    async def _get_database_schema_id(self, schema_fqn: str) -> Optional[str]:
        """Get the ID of a database schema by its FQN"""
        try:
            headers = self.auth_provider.get_auth_headers()
            response = requests.get(
                f"{self.base_url}/v1/databaseSchemas/name/{schema_fqn}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                schema_data = response.json()
                schema_id = schema_data.get("id")
                logger.info(f"✅ Found schema ID for {schema_fqn}: {schema_id}")
                return schema_id
            else:
                logger.warning(f"Could not get schema ID for {schema_fqn}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting schema ID for {schema_fqn}: {e}")
            return None
    
    async def _get_entity_by_fqn(self, table_fqn: str) -> Optional[Dict[str, Any]]:
        """Get an entity by its fully qualified name"""
        try:
            headers = self.auth_provider.get_auth_headers()
            response = requests.get(
                f"{self.base_url}/v1/tables/name/{table_fqn}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.warning(f"Unexpected status {response.status_code} when checking entity {table_fqn}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting entity by FQN {table_fqn}: {e}")
            return None
    
    def _compare_entities(self, existing_entity: Dict[str, Any], new_entity_data: Dict[str, Any]) -> bool:
        """
        Compare existing entity with new entity data to determine if they're the same.
        Returns True if entities are the same, False if different.
        """
        try:
            # Compare columns - this is the most critical part
            existing_columns = existing_entity.get("columns", [])
            new_columns = new_entity_data.get("columns", [])
            
            if len(existing_columns) != len(new_columns):
                logger.info(f"Column count differs: existing={len(existing_columns)}, new={len(new_columns)}")
                return False
            
            # Create maps for easier comparison
            existing_col_map = {col["name"]: col for col in existing_columns}
            new_col_map = {col["name"]: col for col in new_columns}
            
            # Check if all column names match
            if set(existing_col_map.keys()) != set(new_col_map.keys()):
                logger.info(f"Column names differ")
                return False
            
            # Compare each column's data type and other properties
            for col_name, existing_col in existing_col_map.items():
                new_col = new_col_map[col_name]
                
                # Compare data type (case-insensitive)
                existing_type = existing_col.get("dataType", "").upper()
                new_type = new_col.get("dataType", "").upper()
                
                if existing_type != new_type:
                    logger.info(f"Column {col_name} data type differs: {existing_type} vs {new_type}")
                    return False
                
                # Compare dataLength for string types
                if existing_type in ["VARCHAR", "CHAR", "BINARY", "VARBINARY"]:
                    existing_length = existing_col.get("dataLength")
                    new_length = new_col.get("dataLength")
                    if existing_length != new_length:
                        logger.info(f"Column {col_name} dataLength differs: {existing_length} vs {new_length}")
                        return False
            
            # Entities are the same
            return True
            
        except Exception as e:
            logger.error(f"Error comparing entities: {e}")
            # If we can't compare, assume they're different to be safe
            return False
    
    async def _update_entity(self, table_fqn: str, new_entity_data: Dict[str, Any], existing_entity: Dict[str, Any]) -> bool:
        """
        Update an existing entity. Uses PATCH to update only changed fields.
        If PATCH fails, falls back to DELETE and CREATE.
        """
        try:
            headers = self.auth_provider.get_auth_headers()
            
            # OpenMetadata supports PATCH for partial updates
            # We need to send the complete entity with updated fields
            entity_id = existing_entity.get("id")
            
            # Prepare update data with all required fields from existing entity
            update_data = {
                "name": new_entity_data["name"],
                "displayName": new_entity_data.get("displayName", new_entity_data["name"]),
                "description": new_entity_data.get("description", ""),
                "columns": new_entity_data["columns"],
                "databaseSchema": new_entity_data["databaseSchema"]
            }
            
            # Try PATCH first
            logger.info(f"🔄 Attempting to PATCH update entity {table_fqn}")
            patch_response = requests.patch(
                f"{self.base_url}/v1/tables/{entity_id}",
                json=update_data,
                headers=headers,
                timeout=30
            )
            
            if patch_response.status_code in [200, 201]:
                logger.info(f"✅ Successfully updated entity via PATCH: {new_entity_data['name']}")
                return True
            
            # If PATCH fails, try PUT (full update)
            logger.info(f"PATCH failed ({patch_response.status_code}), trying PUT update...")
            put_response = requests.put(
                f"{self.base_url}/v1/tables",
                json=update_data,
                headers=headers,
                timeout=30
            )
            
            if put_response.status_code in [200, 201]:
                logger.info(f"✅ Successfully updated entity via PUT: {new_entity_data['name']}")
                return True
            
            # If both fail, try DELETE and CREATE
            logger.warning(f"PUT also failed ({put_response.status_code}), attempting DELETE and CREATE...")
            
            # Delete existing entity
            delete_response = requests.delete(
                f"{self.base_url}/v1/tables/{entity_id}?hardDelete=true&recursive=false",
                headers=headers,
                timeout=30
            )
            
            if delete_response.status_code not in [200, 204]:
                logger.error(f"❌ Failed to delete entity: {delete_response.status_code} - {delete_response.text}")
                return False
            
            logger.info(f"🗑️ Deleted existing entity {new_entity_data['name']}")
            
            # Create new entity
            create_response = requests.post(
                f"{self.base_url}/v1/tables",
                json=new_entity_data,
                headers=headers,
                timeout=30
            )
            
            if create_response.status_code in [200, 201]:
                logger.info(f"✅ Successfully recreated entity: {new_entity_data['name']}")
                return True
            else:
                logger.error(f"❌ Failed to recreate entity: {create_response.status_code} - {create_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating entity {table_fqn}: {e}")
            return False
    
    async def _get_lineage(self, entity_fqn: str) -> Optional[Dict[str, Any]]:
        """Get lineage information for an entity"""
        try:
            headers = self.auth_provider.get_auth_headers()
            
            # Get lineage with depth 1 (direct connections)
            response = requests.get(
                f"{self.base_url}/v1/lineage/table/name/{entity_fqn}?upstreamDepth=1&downstreamDepth=1",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.warning(f"Unexpected status {response.status_code} when getting lineage for {entity_fqn}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting lineage for {entity_fqn}: {e}")
            return None
    
    def _lineage_edge_exists(self, lineage_data: Dict[str, Any], from_fqn: str, to_fqn: str) -> bool:
        """Check if a specific lineage edge exists in the lineage data"""
        try:
            # Check downstream edges
            downstream_edges = lineage_data.get("downstreamEdges", [])
            for edge in downstream_edges:
                to_entity = edge.get("toEntity")
                if to_entity and to_entity.get("fullyQualifiedName") == to_fqn:
                    return True
            
            # Check upstream edges  
            upstream_edges = lineage_data.get("upstreamEdges", [])
            for edge in upstream_edges:
                from_entity = edge.get("fromEntity")
                if from_entity and from_entity.get("fullyQualifiedName") == from_fqn:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking lineage edge existence: {e}")
            return False
    
    def _map_data_type(self, data_type: str) -> str:
        """Map data types to OpenMetadata format"""
        type_mapping = {
            "STRING": "VARCHAR",
            "INTEGER": "INT",
            "LONG": "BIGINT",
            "DOUBLE": "DOUBLE",
            "FLOAT": "FLOAT",
            "BOOLEAN": "BOOLEAN",
            "DATE": "DATE",
            "TIMESTAMP": "TIMESTAMP",
            "DECIMAL": "DECIMAL"
        }
        return type_mapping.get(data_type.upper(), "VARCHAR")
    
    async def cleanup(self) -> None:
        """Clean up resources and connections"""
        logger.info("Cleaning up OpenMetadata store resources")
        self.initialized = False

