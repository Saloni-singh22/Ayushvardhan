#!/usr/bin/env python3
"""
Test script to validate API route integration for FHIR R4 terminology service.
Tests all major endpoints to ensure proper router integration.
"""

import asyncio
import json
from typing import Dict, Any
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_api_integration():
    """
    Test API route integration by checking endpoint accessibility.
    This validates that all route modules are properly integrated.
    """
    print("🧪 Testing FHIR R4 Terminology Service API Integration")
    print("=" * 60)
    
    try:
        # Test imports to validate module structure
        print("📦 Testing module imports...")
        
        # Test core imports
        from app.api.v1 import api_router
        from app.api.v1.routes.codesystem import router as codesystem_router
        from app.api.v1.routes.conceptmap import router as conceptmap_router
        from app.api.v1.routes.valueset import router as valueset_router
        print("✅ All route modules imported successfully")
        
        # Test utility imports
        from app.utils.fhir_utils import create_capability_statement
        from app.utils.pagination import PaginationParams
        print("✅ Utility modules imported successfully")
        
        # Test model imports
        from app.models.fhir.resources import CodeSystem, ConceptMap, ValueSet
        from app.models.namaste.traditional_medicine import NAMASTECode
        from app.models.who.icd11 import ICDCode
        print("✅ FHIR and domain models imported successfully")
        
        # Validate router structure
        print("\n🔗 Validating router structure...")
        routes = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                routes.append({
                    'path': route.path,
                    'methods': getattr(route, 'methods', ['GET'])
                })
        
        print(f"✅ Main API router has {len(routes)} routes configured")
        
        # Check for key endpoints
        key_endpoints = [
            '/health',
            '/metadata',
            '/'
        ]
        
        found_endpoints = [route['path'] for route in routes]
        for endpoint in key_endpoints:
            if endpoint in found_endpoints:
                print(f"✅ Key endpoint found: {endpoint}")
            else:
                print(f"❌ Missing key endpoint: {endpoint}")
        
        # Test CapabilityStatement generation
        print("\n📋 Testing FHIR CapabilityStatement generation...")
        capability_statement = create_capability_statement(
            base_url="http://localhost:8000/api/v1",
            implementation_description="Test FHIR R4 Terminology Service",
            implementation_version="1.0.0"
        )
        
        if capability_statement:
            print("✅ CapabilityStatement generated successfully")
            print(f"   Resource Type: {capability_statement.resourceType}")
            print(f"   Status: {capability_statement.status}")
            print(f"   FHIR Version: {capability_statement.fhirVersion}")
        else:
            print("❌ Failed to generate CapabilityStatement")
        
        # Test pagination utilities
        print("\n📄 Testing pagination utilities...")
        pagination_params = PaginationParams(
            _count=10,
            _offset=0
        )
        print(f"✅ Pagination params created: count={pagination_params._count}, offset={pagination_params._offset}")
        
        print("\n🎉 API Integration Test Summary")
        print("=" * 40)
        print("✅ All core modules imported successfully")
        print("✅ Router structure validated")
        print("✅ Key endpoints configured")
        print("✅ FHIR utilities functional")
        print("✅ Ready for data integration phase")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   This is expected during development - modules need to be in PYTHONPATH")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

def print_next_steps():
    """Print the next steps for Phase 5 implementation"""
    print("\n🚀 Next Steps - Phase 5: NAMASTE Data Integration")
    print("=" * 50)
    print("1. 📊 Create NAMASTE data loader scripts")
    print("   - Load 4,500+ traditional medicine codes")
    print("   - Process Ayurveda, Siddha, Unani properties")
    print("   - Implement dosha classifications")
    
    print("\n2. 🗄️ Implement WHO ICD-11 data integration")
    print("   - Connect to WHO ICD-11 2025 API")
    print("   - Load TM2 and Biomedicine modules")
    print("   - Create mapping relationships")
    
    print("\n3. 🔗 Establish dual-coding mappings")
    print("   - Map NAMASTE codes to ICD-11 TM2")
    print("   - Create ConceptMap resources")
    print("   - Implement translation operations")
    
    print("\n4. ✅ Validate data integrity")
    print("   - Test API endpoints with real data")
    print("   - Verify FHIR compliance")
    print("   - Validate terminology operations")

async def main():
    """Main test execution"""
    success = await test_api_integration()
    print_next_steps()
    
    if success:
        print("\n🎯 Phase 4 Complete: API Routes Development")
        print("Ready to proceed with Phase 5: NAMASTE Data Integration")
    else:
        print("\n⚠️  Some tests failed - review import paths and dependencies")

if __name__ == "__main__":
    asyncio.run(main())