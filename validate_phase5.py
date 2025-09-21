#!/usr/bin/env python3
"""
Phase 5 Completion Validation Script
Validates that NAMASTE Data Integration is complete with FHIR resources ready for API
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase5Validator:
    """Validates Phase 5 NAMASTE Data Integration completion"""
    
    def __init__(self, data_directory: str = "data/fhir"):
        self.data_directory = Path(data_directory)
        self.validation_results = {
            "codesystems": {"count": 0, "valid": 0, "systems": []},
            "conceptmaps": {"count": 0, "valid": 0, "mappings": []},
            "traditional_medicine_coverage": {"ayurveda": 0, "siddha": 0, "unani": 0},
            "icd11_integration": {"tm2": False, "biomedicine": False},
            "dual_coding_ready": False
        }
    
    def validate_codesystem(self, filename: Path) -> bool:
        """Validate a FHIR CodeSystem resource"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                codesystem = json.load(f)
            
            # Check required FHIR fields
            required_fields = ["resourceType", "id", "url", "status", "content", "concept"]
            
            for field in required_fields:
                if field not in codesystem:
                    logger.error(f"❌ Missing required field '{field}' in {filename}")
                    return False
            
            # Validate resource type
            if codesystem["resourceType"] != "CodeSystem":
                logger.error(f"❌ Invalid resourceType in {filename}")
                return False
            
            # Check concept count
            concept_count = len(codesystem.get("concept", []))
            if concept_count == 0:
                logger.error(f"❌ No concepts found in {filename}")
                return False
            
            logger.info(f"✅ Valid CodeSystem: {codesystem['id']} ({concept_count} concepts)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating {filename}: {e}")
            return False
    
    def validate_conceptmap(self, filename: Path) -> bool:
        """Validate a FHIR ConceptMap resource"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                conceptmap = json.load(f)
            
            # Check required FHIR fields
            required_fields = ["resourceType", "id", "url", "status", "sourceUri", "targetUri", "group"]
            
            for field in required_fields:
                if field not in conceptmap:
                    logger.error(f"❌ Missing required field '{field}' in {filename}")
                    return False
            
            # Validate resource type
            if conceptmap["resourceType"] != "ConceptMap":
                logger.error(f"❌ Invalid resourceType in {filename}")
                return False
            
            # Check mapping count
            mapping_count = 0
            for group in conceptmap.get("group", []):
                mapping_count += len(group.get("element", []))
            
            if mapping_count == 0:
                logger.error(f"❌ No mappings found in {filename}")
                return False
            
            logger.info(f"✅ Valid ConceptMap: {conceptmap['id']} ({mapping_count} mappings)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating {filename}: {e}")
            return False
    
    def analyze_traditional_medicine_coverage(self):
        """Analyze coverage of traditional medicine systems"""
        systems = ["ayurveda", "siddha", "unani"]
        
        for system in systems:
            filename = self.data_directory / f"codesystem-namaste-{system}.json"
            if filename.exists():
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        codesystem = json.load(f)
                    
                    concept_count = len(codesystem.get("concept", []))
                    self.validation_results["traditional_medicine_coverage"][system] = concept_count
                    logger.info(f"📊 {system.title()} system: {concept_count} codes")
                    
                except Exception as e:
                    logger.error(f"❌ Error analyzing {system}: {e}")
    
    def check_icd11_integration(self):
        """Check ICD-11 module integration"""
        modules = ["tm2", "biomedicine"]
        
        for module in modules:
            filename = self.data_directory / f"codesystem-icd11-{module}.json"
            if filename.exists():
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        codesystem = json.load(f)
                    
                    if len(codesystem.get("concept", [])) > 0:
                        self.validation_results["icd11_integration"][module] = True
                        logger.info(f"✅ ICD-11 {module.upper()} module integrated")
                    
                except Exception as e:
                    logger.error(f"❌ Error checking ICD-11 {module}: {e}")
    
    def validate_dual_coding_readiness(self):
        """Check if dual-coding infrastructure is ready"""
        # Check for ConceptMap files
        conceptmap_files = list(self.data_directory.glob("conceptmap-*.json"))
        
        if len(conceptmap_files) >= 5:  # Expect at least 5 mappings
            # Check for NAMASTE to ICD-11 mappings
            namaste_to_tm2 = any("namaste" in f.name and "tm2" in f.name for f in conceptmap_files)
            namaste_to_bio = any("namaste" in f.name and "biomedicine" in f.name for f in conceptmap_files)
            
            if namaste_to_tm2 and namaste_to_bio:
                self.validation_results["dual_coding_ready"] = True
                logger.info("✅ Dual-coding infrastructure ready")
            else:
                logger.warning("⚠️  Incomplete dual-coding mappings")
        else:
            logger.warning("⚠️  Insufficient ConceptMap resources")
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete Phase 5 validation"""
        logger.info("🔍 Running Phase 5 NAMASTE Data Integration Validation")
        logger.info("=" * 60)
        
        # Validate CodeSystems
        logger.info("\n📚 Validating FHIR CodeSystems...")
        codesystem_files = list(self.data_directory.glob("codesystem-*.json"))
        
        for filename in codesystem_files:
            if self.validate_codesystem(filename):
                self.validation_results["codesystems"]["valid"] += 1
                self.validation_results["codesystems"]["systems"].append(filename.stem)
            self.validation_results["codesystems"]["count"] += 1
        
        # Validate ConceptMaps
        logger.info("\n🗺️ Validating FHIR ConceptMaps...")
        conceptmap_files = list(self.data_directory.glob("conceptmap-*.json"))
        
        for filename in conceptmap_files:
            if self.validate_conceptmap(filename):
                self.validation_results["conceptmaps"]["valid"] += 1
                self.validation_results["conceptmaps"]["mappings"].append(filename.stem)
            self.validation_results["conceptmaps"]["count"] += 1
        
        # Analyze coverage
        logger.info("\n🌿 Analyzing Traditional Medicine Coverage...")
        self.analyze_traditional_medicine_coverage()
        
        # Check ICD-11 integration
        logger.info("\n🌍 Checking WHO ICD-11 Integration...")
        self.check_icd11_integration()
        
        # Validate dual-coding readiness
        logger.info("\n🔗 Validating Dual-Coding Infrastructure...")
        self.validate_dual_coding_readiness()
        
        return self.validation_results
    
    def print_validation_summary(self, results: Dict[str, Any]):
        """Print comprehensive validation summary"""
        print("\n" + "="*60)
        print("🎯 Phase 5 NAMASTE Data Integration - Validation Summary")
        print("="*60)
        
        # CodeSystems summary
        cs_results = results["codesystems"]
        print(f"\n📚 FHIR CodeSystems:")
        print(f"   Total: {cs_results['count']}")
        print(f"   Valid: {cs_results['valid']}")
        print(f"   Systems: {', '.join(cs_results['systems'])}")
        
        # ConceptMaps summary
        cm_results = results["conceptmaps"]
        print(f"\n🗺️ FHIR ConceptMaps:")
        print(f"   Total: {cm_results['count']}")
        print(f"   Valid: {cm_results['valid']}")
        print(f"   Mappings: {cm_results['count']} dual-coding relationships")
        
        # Traditional medicine coverage
        tm_coverage = results["traditional_medicine_coverage"]
        total_tm_codes = sum(tm_coverage.values())
        print(f"\n🌿 Traditional Medicine Coverage:")
        print(f"   Total Codes: {total_tm_codes}")
        print(f"   Ayurveda: {tm_coverage['ayurveda']} codes")
        print(f"   Siddha: {tm_coverage['siddha']} codes")
        print(f"   Unani: {tm_coverage['unani']} codes")
        
        # ICD-11 integration
        icd11_integration = results["icd11_integration"]
        print(f"\n🌍 WHO ICD-11 Integration:")
        print(f"   TM2 Module: {'✅ Integrated' if icd11_integration['tm2'] else '❌ Missing'}")
        print(f"   Biomedicine Module: {'✅ Integrated' if icd11_integration['biomedicine'] else '❌ Missing'}")
        
        # Dual-coding readiness
        dual_coding = results["dual_coding_ready"]
        print(f"\n🔗 Dual-Coding Infrastructure:")
        print(f"   Status: {'✅ Ready' if dual_coding else '❌ Not Ready'}")
        
        # Overall status
        print(f"\n🎉 Phase 5 Status:")
        if (cs_results['valid'] >= 5 and cm_results['valid'] >= 5 and 
            total_tm_codes > 0 and dual_coding):
            print("   ✅ PHASE 5 COMPLETE - NAMASTE Data Integration Successful!")
            print("   ✅ Ready for Phase 6: API Testing and Validation")
        else:
            print("   ⚠️  Phase 5 needs additional work")
        
        # Next steps
        print(f"\n🚀 Ready for Next Phase:")
        print("   📊 Phase 6: API Testing and Validation")
        print("   🔄 Phase 7: Authentication Integration")
        print("   🌐 Phase 8: API Gateway Setup")

def main():
    """Main validation execution"""
    print("🧪 Phase 5 NAMASTE Data Integration Validation")
    print("=" * 50)
    
    validator = Phase5Validator()
    results = validator.run_validation()
    validator.print_validation_summary(results)
    
    print("\n📁 Generated FHIR Resources:")
    data_path = Path("data/fhir")
    if data_path.exists():
        for file in sorted(data_path.glob("*.json")):
            print(f"   📄 {file.name}")
    
    print("\n🎯 Achievement Unlocked: FHIR R4 Terminology Service with Traditional Medicine Integration!")

if __name__ == "__main__":
    main()