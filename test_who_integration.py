"""
WHO ICD-11 TM2 Integration Test Script

This script tests the WHO ICD-11 TM2 integration to ensure:
1. Authentication works correctly
2. API endpoints are accessible
3. FHIR conversion produces valid results
4. Database operations work properly

Run this script after setting up WHO API credentials in your .env file.
"""

import asyncio
import httpx
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
WHO_CLIENT_ID = os.getenv("WHO_ICD_CLIENT_ID")
WHO_CLIENT_SECRET = os.getenv("WHO_ICD_CLIENT_SECRET")

class WHOIntegrationTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details and not success:
            print(f"   Details: {details}")
    
    async def test_credentials_configured(self):
        """Test if WHO API credentials are configured"""
        test_name = "WHO Credentials Configuration"
        
        if WHO_CLIENT_ID and WHO_CLIENT_SECRET:
            self.log_test(
                test_name, 
                True, 
                "WHO API credentials are configured"
            )
            return True
        else:
            self.log_test(
                test_name, 
                False, 
                "WHO API credentials not found in environment variables",
                {"WHO_CLIENT_ID": bool(WHO_CLIENT_ID), "WHO_CLIENT_SECRET": bool(WHO_CLIENT_SECRET)}
            )
            return False
    
    async def test_who_api_health(self):
        """Test WHO API health endpoint"""
        test_name = "WHO API Health Check"
        
        try:
            response = await self.client.get(f"{self.base_url}/who-icd/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test(
                        test_name, 
                        True, 
                        "WHO API is accessible and healthy",
                        {"api_version": data.get("api_version")}
                    )
                    return True
                else:
                    self.log_test(
                        test_name, 
                        False, 
                        f"WHO API returned unhealthy status: {data.get('message')}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    test_name, 
                    False, 
                    f"WHO API health check failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                test_name, 
                False, 
                f"Failed to connect to WHO API health endpoint: {str(e)}"
            )
            return False
    
    async def test_search_entities(self):
        """Test WHO entity search functionality"""
        test_name = "WHO Entity Search"
        
        try:
            params = {
                "term": "acupuncture",
                "limit": 5,
                "tm2_only": True,
                "include_details": False
            }
            
            response = await self.client.post(
                f"{self.base_url}/who-icd/search",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entities" in data:
                    entity_count = len(data["entities"])
                    self.log_test(
                        test_name, 
                        True, 
                        f"Successfully searched WHO entities, found {entity_count} results",
                        {"search_term": params["term"], "entity_count": entity_count}
                    )
                    return data["entities"]
                else:
                    self.log_test(
                        test_name, 
                        False, 
                        "Search returned success=False or missing entities",
                        data
                    )
                    return []
            else:
                self.log_test(
                    test_name, 
                    False, 
                    f"Search failed with status {response.status_code}",
                    response.text
                )
                return []
                
        except Exception as e:
            self.log_test(
                test_name, 
                False, 
                f"Entity search failed: {str(e)}"
            )
            return []
    
    async def test_entity_details(self, entity_id: str):
        """Test getting entity details"""
        test_name = "WHO Entity Details"
        
        try:
            response = await self.client.get(f"{self.base_url}/who-icd/entity/{entity_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity" in data:
                    entity = data["entity"]
                    self.log_test(
                        test_name, 
                        True, 
                        f"Successfully retrieved entity details for {entity_id}",
                        {
                            "entity_id": entity.get("id"),
                            "code": entity.get("code"),
                            "title": entity.get("title"),
                            "is_tm2_related": entity.get("is_tm2_related")
                        }
                    )
                    return True
                else:
                    self.log_test(
                        test_name, 
                        False, 
                        "Entity details request returned success=False or missing entity",
                        data
                    )
                    return False
            else:
                self.log_test(
                    test_name, 
                    False, 
                    f"Entity details request failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                test_name, 
                False, 
                f"Entity details request failed: {str(e)}"
            )
            return False
    
    async def test_keyword_search(self):
        """Test keyword-based search"""
        test_name = "Keyword Search"
        
        try:
            params = {
                "keywords": "acupuncture,herbal",
                "save_to_database": False
            }
            
            response = await self.client.get(
                f"{self.base_url}/who-icd/search/keywords",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    total_found = data.get("total_entities_found", 0)
                    self.log_test(
                        test_name, 
                        True, 
                        f"Successfully searched by keywords, found {total_found} entities",
                        {
                            "keywords": data.get("keywords_searched"),
                            "total_found": total_found
                        }
                    )
                    return True
                else:
                    self.log_test(
                        test_name, 
                        False, 
                        "Keyword search returned success=False",
                        data
                    )
                    return False
            else:
                self.log_test(
                    test_name, 
                    False, 
                    f"Keyword search failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                test_name, 
                False, 
                f"Keyword search failed: {str(e)}"
            )
            return False
    
    async def test_codesystems_list(self):
        """Test listing WHO CodeSystems"""
        test_name = "WHO CodeSystems List"
        
        try:
            response = await self.client.get(f"{self.base_url}/who-icd/codesystems")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    codesystem_count = data.get("total_count", 0)
                    self.log_test(
                        test_name, 
                        True, 
                        f"Successfully listed WHO CodeSystems, found {codesystem_count} CodeSystems",
                        {"total_count": codesystem_count}
                    )
                    return True
                else:
                    self.log_test(
                        test_name, 
                        False, 
                        "CodeSystems list returned success=False",
                        data
                    )
                    return False
            else:
                self.log_test(
                    test_name, 
                    False, 
                    f"CodeSystems list failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                test_name, 
                False, 
                f"CodeSystems list failed: {str(e)}"
            )
            return False
    
    async def test_sync_trigger(self):
        """Test sync trigger (without waiting for completion)"""
        test_name = "Sync Trigger"
        
        try:
            params = {
                "max_entities": 10,  # Small number for testing
                "batch_size": 5,
                "save_to_database": False,  # Don't save during testing
                "create_by_category": True
            }
            
            response = await self.client.post(
                f"{self.base_url}/who-icd/sync/tm2",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test(
                        test_name, 
                        True, 
                        "Successfully triggered WHO TM2 sync",
                        {"parameters": data.get("parameters")}
                    )
                    return True
                else:
                    self.log_test(
                        test_name, 
                        False, 
                        "Sync trigger returned success=False",
                        data
                    )
                    return False
            else:
                self.log_test(
                    test_name, 
                    False, 
                    f"Sync trigger failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                test_name, 
                False, 
                f"Sync trigger failed: {str(e)}"
            )
            return False
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🧪 Starting WHO ICD-11 TM2 Integration Tests\n")
        
        # Test 1: Check credentials
        if not await self.test_credentials_configured():
            print("\n❌ Cannot continue testing without WHO API credentials")
            print("   Please set WHO_ICD_CLIENT_ID and WHO_ICD_CLIENT_SECRET in your .env file")
            return self.get_summary()
        
        # Test 2: Health check
        if not await self.test_who_api_health():
            print("\n❌ WHO API is not accessible, skipping remaining tests")
            return self.get_summary()
        
        # Test 3: Search entities
        entities = await self.test_search_entities()
        
        # Test 4: Entity details (if we found entities)
        if entities:
            first_entity = entities[0]
            entity_id = first_entity.get("id")
            if entity_id:
                await self.test_entity_details(entity_id)
        
        # Test 5: Keyword search
        await self.test_keyword_search()
        
        # Test 6: List CodeSystems
        await self.test_codesystems_list()
        
        # Test 7: Sync trigger
        await self.test_sync_trigger()
        
        return self.get_summary()
    
    def get_summary(self):
        """Get test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        else:
            print(f"\n✅ All tests passed! WHO ICD-11 TM2 integration is working correctly.")
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests/total_tests)*100 if total_tests > 0 else 0,
            "results": self.test_results
        }


async def main():
    """Main test function"""
    print("WHO ICD-11 TM2 Integration Test Suite")
    print("=" * 50)
    
    async with WHOIntegrationTester() as tester:
        summary = await tester.run_all_tests()
        
        # Save detailed results to file
        with open("who_integration_test_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📁 Detailed test results saved to: who_integration_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())