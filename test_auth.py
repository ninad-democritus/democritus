#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/app')

from app.services.metadata_service import MetadataService

async def test_auth():
    print("=== Testing OpenMetadata Authentication ===")
    
    service = MetadataService()
    
    # Test health check
    print("1. Testing health check...")
    health = await service._check_openmetadata_health()
    print(f"   Health: {health}")
    
    # Test authentication
    print("2. Testing authentication...")
    auth_success = await service._authenticate()
    print(f"   Auth success: {auth_success}")
    
    if service.auth_token:
        token_type = 'JWT' if not service.auth_token.startswith('Basic') else 'Basic Auth'
        print(f"   Token type: {token_type}")
        print(f"   Token preview: {str(service.auth_token)[:50]}...")
        
        # Test API calls
        print("3. Testing API access...")
        import requests
        headers = service._get_auth_headers()
        
        try:
            # Test system version (should work without auth)
            response = requests.get(f'http://{service.host}:{service.port}/api/v1/system/version', headers=headers, timeout=5)
            print(f"   System version API: {response.status_code}")
            
            # Test users API (requires auth)
            response = requests.get(f'http://{service.host}:{service.port}/api/v1/users', headers=headers, timeout=5)
            print(f"   Users API: {response.status_code}")
            
            if response.status_code == 200:
                print("   🎉 SUCCESS: Can access protected endpoints!")
                return True
            else:
                print(f"   ⚠️ Partial success: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ API test failed: {e}")
    else:
        print("   ❌ No authentication token obtained")
    
    return False

if __name__ == "__main__":
    result = asyncio.run(test_auth())
    print(f"\nAuthentication test result: {'PASS' if result else 'FAIL'}")
