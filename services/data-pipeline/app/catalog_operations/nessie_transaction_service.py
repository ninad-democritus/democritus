"""
Nessie Transaction Service for managing Nessie branches and transactions
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BranchStatus:
    """Status of a Nessie branch"""
    name: str
    hash: str
    exists: bool
    created_at: Optional[datetime] = None
    commit_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hash": self.hash,
            "exists": self.exists,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "commit_count": self.commit_count
        }


class NessieTransactionService:
    """Service for managing Nessie branches and transactions (NOT INTEGRATED IN PIPELINE)"""
    
    def __init__(self, nessie_uri: str = "http://nessie:19120/api/v1"):
        """
        Initialize the Nessie transaction service
        
        Args:
            nessie_uri: URI of the Nessie server
        """
        self.nessie_uri = nessie_uri
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    async def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """
        Create a new Nessie branch for transactional processing
        
        Args:
            branch_name: Name of the branch to create
            from_branch: Source branch to create from
            
        Returns:
            True if branch was created successfully
        """
        logger.info(f"Creating Nessie branch: {branch_name} from {from_branch}")
        
        try:
            # Get source branch reference
            source_response = self.session.get(f"{self.nessie_uri}/trees/tree/{from_branch}")
            if source_response.status_code != 200:
                logger.error(f"Failed to get source branch {from_branch}: {source_response.text}")
                return False
            
            source_hash = source_response.json().get("hash")
            if not source_hash:
                logger.error(f"Could not get hash for source branch {from_branch}")
                return False
            
            # Create branch using Nessie API v1 format
            create_data = {
                "sourceRefName": from_branch,
                "hash": source_hash
            }
            
            response = self.session.put(
                f"{self.nessie_uri}/trees/branch/{branch_name}", 
                json=create_data
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully created Nessie branch: {branch_name}")
                return True
            else:
                logger.error(f"Failed to create branch {branch_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create Nessie branch {branch_name}: {str(e)}")
            return False
    
    async def merge_branch(self, branch_name: str, to_branch: str = "main") -> bool:
        """
        Merge a Nessie branch to another branch (commit transaction)
        
        Args:
            branch_name: Name of the branch to merge
            to_branch: Target branch to merge into
            
        Returns:
            True if branch was merged successfully
        """
        logger.info(f"Merging Nessie branch {branch_name} to {to_branch}")
        
        try:
            # Get source branch reference
            branch_response = self.session.get(f"{self.nessie_uri}/trees/tree/{branch_name}")
            if branch_response.status_code != 200:
                logger.error(f"Failed to get branch {branch_name}: {branch_response.text}")
                return False
            
            branch_hash = branch_response.json().get("hash")
            if not branch_hash:
                logger.error(f"Could not get hash for branch {branch_name}")
                return False
            
            # Merge branch using Nessie API v1 format
            merge_data = {
                "fromHash": branch_hash,
                "fromRefName": branch_name
            }
            
            response = self.session.post(
                f"{self.nessie_uri}/trees/branch/{to_branch}/merge", 
                json=merge_data
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully merged branch {branch_name} to {to_branch}")
                return True
            else:
                logger.error(f"Failed to merge branch {branch_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to merge Nessie branch {branch_name}: {str(e)}")
            return False
    
    async def delete_branch(self, branch_name: str) -> bool:
        """
        Delete a Nessie branch
        
        Args:
            branch_name: Name of the branch to delete
            
        Returns:
            True if branch was deleted successfully
        """
        logger.info(f"Deleting Nessie branch: {branch_name}")
        
        try:
            response = self.session.delete(f"{self.nessie_uri}/trees/branch/{branch_name}")
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted Nessie branch: {branch_name}")
                return True
            elif response.status_code == 404:
                logger.info(f"Branch {branch_name} does not exist (already deleted)")
                return True
            else:
                logger.error(f"Failed to delete branch {branch_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete Nessie branch {branch_name}: {str(e)}")
            return False
    
    async def rollback_branch(self, branch_name: str) -> bool:
        """
        Rollback a branch by deleting it (transaction rollback)
        
        Args:
            branch_name: Name of the branch to rollback
            
        Returns:
            True if rollback was successful
        """
        logger.info(f"Rolling back Nessie branch: {branch_name}")
        return await self.delete_branch(branch_name)
    
    def get_branch_status(self, branch_name: str) -> BranchStatus:
        """
        Get the status of a Nessie branch
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            BranchStatus object with branch information
        """
        logger.debug(f"Getting status for Nessie branch: {branch_name}")
        
        try:
            response = self.session.get(f"{self.nessie_uri}/trees/tree/{branch_name}")
            
            if response.status_code == 200:
                data = response.json()
                return BranchStatus(
                    name=branch_name,
                    hash=data.get("hash", ""),
                    exists=True,
                    created_at=datetime.now()  # Nessie doesn't provide creation time in basic API
                )
            elif response.status_code == 404:
                return BranchStatus(
                    name=branch_name,
                    hash="",
                    exists=False
                )
            else:
                logger.error(f"Failed to get branch status for {branch_name}: {response.status_code}")
                return BranchStatus(
                    name=branch_name,
                    hash="",
                    exists=False
                )
                
        except Exception as e:
            logger.error(f"Failed to get branch status for {branch_name}: {str(e)}")
            return BranchStatus(
                name=branch_name,
                hash="",
                exists=False
            )
    
    async def list_branches(self) -> List[str]:
        """
        List all branches in the Nessie repository
        
        Returns:
            List of branch names
        """
        logger.info("Listing all Nessie branches")
        
        try:
            response = self.session.get(f"{self.nessie_uri}/trees")
            
            if response.status_code == 200:
                data = response.json()
                branches = []
                
                for ref in data.get("references", []):
                    if ref.get("type") == "BRANCH":
                        branches.append(ref.get("name"))
                
                logger.info(f"Found {len(branches)} branches")
                return branches
            else:
                logger.error(f"Failed to list branches: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to list branches: {str(e)}")
            return []
    
    async def create_transaction_branch(self, job_id: str, base_branch: str = "main") -> Optional[str]:
        """
        Create a transaction branch for a specific job
        
        Args:
            job_id: Unique job identifier
            base_branch: Base branch to create from
            
        Returns:
            Branch name if created successfully, None otherwise
        """
        branch_name = f"transaction-{job_id}"
        
        if await self.create_branch(branch_name, base_branch):
            return branch_name
        return None
    
    async def commit_transaction(self, branch_name: str, target_branch: str = "main") -> bool:
        """
        Commit a transaction by merging the branch and cleaning up
        
        Args:
            branch_name: Name of the transaction branch
            target_branch: Target branch to merge into
            
        Returns:
            True if transaction was committed successfully
        """
        logger.info(f"Committing transaction: {branch_name} -> {target_branch}")
        
        try:
            # Merge the branch
            if not await self.merge_branch(branch_name, target_branch):
                logger.error(f"Failed to merge transaction branch {branch_name}")
                return False
            
            # Clean up the transaction branch
            if not await self.delete_branch(branch_name):
                logger.warning(f"Failed to clean up transaction branch {branch_name}")
                # Don't fail the transaction for cleanup issues
            
            logger.info(f"Successfully committed transaction: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit transaction {branch_name}: {str(e)}")
            return False
    
    async def rollback_transaction(self, branch_name: str) -> bool:
        """
        Rollback a transaction by deleting the branch
        
        Args:
            branch_name: Name of the transaction branch
            
        Returns:
            True if transaction was rolled back successfully
        """
        logger.info(f"Rolling back transaction: {branch_name}")
        
        try:
            success = await self.delete_branch(branch_name)
            
            if success:
                logger.info(f"Successfully rolled back transaction: {branch_name}")
            else:
                logger.error(f"Failed to rollback transaction: {branch_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to rollback transaction {branch_name}: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test connection to Nessie server
        
        Returns:
            True if connection is successful
        """
        try:
            response = self.session.get(f"{self.nessie_uri}/config")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Nessie connection test failed: {str(e)}")
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Nessie service
        
        Returns:
            Dictionary with service information
        """
        try:
            # Test connection
            connected = self.test_connection()
            
            info = {
                "nessie_uri": self.nessie_uri,
                "connected": connected,
                "service_status": "available" if connected else "unavailable"
            }
            
            if connected:
                # Try to get version info
                try:
                    response = self.session.get(f"{self.nessie_uri}/config")
                    if response.status_code == 200:
                        config = response.json()
                        info["version"] = config.get("specVersion", "unknown")
                except Exception:
                    pass
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get Nessie service info: {str(e)}")
            return {
                "nessie_uri": self.nessie_uri,
                "connected": False,
                "service_status": "error",
                "error": str(e)
            }

