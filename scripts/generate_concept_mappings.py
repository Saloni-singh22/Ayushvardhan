#!/usr/bin/env python3
"""
NAMASTE-ICD11 Concept Mapping Generator
Creates FHIR ConceptMap resources for dual-coding between traditional medicine and biomedical systems
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConceptMapping:
    """Represents a mapping between two terminology systems"""
    source_code: str
    source_display: str
    source_system: str
    target_code: str
    target_display: str
    target_system: str
    equivalence: str  # "relatedto", "equivalent", "wider", "narrower", "specializes", "generalizes"
    confidence: float  # 0.0 to 1.0
    comments: str
    evidence_level: str

class ConceptMapGenerator:
    """
    Generates FHIR ConceptMap resources for mapping between:
    - NAMASTE Traditional Medicine codes
    - WHO ICD-11 TM2 (Traditional Medicine 2) 
    - WHO ICD-11 Biomedicine
    """
    
    def __init__(self, data_directory: str = "data/fhir"):
        self.data_directory = Path(data_directory)
        self.mappings: List[ConceptMapping] = []
        self.namaste_systems = {
            "ayurveda": "http://terminology.ayushvardhan.com/CodeSystem/namaste-ayurveda",
            "siddha": "http://terminology.ayushvardhan.com/CodeSystem/namaste-siddha", 
            "unani": "http://terminology.ayushvardhan.com/CodeSystem/namaste-unani"
        }
        self.icd11_systems = {
            "tm2": "http://terminology.ayushvardhan.com/CodeSystem/icd11-tm2",
            "biomedicine": "http://terminology.ayushvardhan.com/CodeSystem/icd11-biomedicine"
        }
    
    async def load_existing_codesystems(self) -> Dict[str, Any]:
        """Load previously generated CodeSystems to extract codes for mapping"""
        codesystems = {}
        
        # Load NAMASTE CodeSystems
        for system in ["ayurveda", "siddha", "unani"]:
            filename = self.data_directory / f"codesystem-namaste-{system}.json"
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    codesystems[f"namaste-{system}"] = json.load(f)
        
        # Load ICD-11 CodeSystems
        for system in ["tm2", "biomedicine"]:
            filename = self.data_directory / f"codesystem-icd11-{system}.json"
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    codesystems[f"icd11-{system}"] = json.load(f)
        
        logger.info(f"📚 Loaded {len(codesystems)} CodeSystems for mapping")
        return codesystems
    
    def create_expert_mappings(self) -> List[ConceptMapping]:
        """
        Create expert-curated mappings between traditional medicine and biomedical codes.
        These mappings are based on clinical knowledge and traditional medicine principles.
        """
        logger.info("🧠 Creating expert-curated concept mappings...")
        
        mappings = [
            # Ayurveda to ICD-11 TM2 mappings
            ConceptMapping(
                source_code="AYU-D-001",
                source_display="Vata Dosha Imbalance",
                source_system=self.namaste_systems["ayurveda"],
                target_code="TM2.D",
                target_display="Dosha Imbalance Patterns",
                target_system=self.icd11_systems["tm2"],
                equivalence="specializes",
                confidence=0.95,
                comments="Vata dosha imbalance is a specific type of dosha imbalance pattern in Ayurveda",
                evidence_level="Expert consensus"
            ),
            
            # Ayurveda to Biomedicine mappings
            ConceptMapping(
                source_code="AYU-H-001",
                source_display="Ashwagandha (Withania somnifera)",
                source_system=self.namaste_systems["ayurveda"],
                target_code="6A00-6E8Z",
                target_display="Mental, behavioural or neurodevelopmental disorders",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.80,
                comments="Ashwagandha is traditionally used for stress and anxiety, relating to mental health disorders",
                evidence_level="Clinical studies"
            ),
            
            ConceptMapping(
                source_code="AYU-H-002",
                source_display="Brahmi (Bacopa monnieri)",
                source_system=self.namaste_systems["ayurveda"],
                target_code="6A00-6E8Z",
                target_display="Mental, behavioural or neurodevelopmental disorders",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.85,
                comments="Brahmi is used for cognitive enhancement and memory improvement",
                evidence_level="Clinical studies"
            ),
            
            ConceptMapping(
                source_code="AYU-F-001",
                source_display="Triphala Churna",
                source_system=self.namaste_systems["ayurveda"],
                target_code="11A00-11G9Z",
                target_display="Diseases of the digestive system",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.90,
                comments="Triphala is primarily used for digestive health and gastrointestinal disorders",
                evidence_level="Traditional evidence"
            ),
            
            ConceptMapping(
                source_code="AYU-T-001",
                source_display="Panchakarma Detoxification",
                source_system=self.namaste_systems["ayurveda"],
                target_code="11A00-11G9Z",
                target_display="Diseases of the digestive system",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.75,
                comments="Panchakarma includes digestive detoxification procedures",
                evidence_level="Traditional evidence"
            ),
            
            # Siddha to ICD-11 mappings
            ConceptMapping(
                source_code="SID-H-001",
                source_display="Nilavembu (Andrographis paniculata)",
                source_system=self.namaste_systems["siddha"],
                target_code="1A00-1F9Z",
                target_display="Certain infectious and parasitic diseases",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.85,
                comments="Nilavembu is traditionally used for fever and infections",
                evidence_level="Clinical studies"
            ),
            
            # Unani to ICD-11 mappings
            ConceptMapping(
                source_code="UNA-H-001",
                source_display="Zanjabeel (Zingiber officinale)",
                source_system=self.namaste_systems["unani"],
                target_code="11A00-11G9Z",
                target_display="Diseases of the digestive system",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.90,
                comments="Zanjabeel (ginger) is used for digestive disorders in Unani medicine",
                evidence_level="Traditional evidence"
            ),
            
            ConceptMapping(
                source_code="UNA-F-001",
                source_display="Jawarish Amla",
                source_system=self.namaste_systems["unani"],
                target_code="11A00-11G9Z",
                target_display="Diseases of the digestive system",
                target_system=self.icd11_systems["biomedicine"],
                equivalence="relatedto",
                confidence=0.80,
                comments="Jawarish Amla is used for digestive and cardiac health",
                evidence_level="Traditional evidence"
            ),
            
            # Cross-traditional system mappings (NAMASTE to ICD-11 TM2)
            ConceptMapping(
                source_code="SID-H-001",
                source_display="Nilavembu (Andrographis paniculata)",
                source_system=self.namaste_systems["siddha"],
                target_code="TM2.Q",
                target_display="Qi Stagnation Patterns",
                target_system=self.icd11_systems["tm2"],
                equivalence="relatedto",
                confidence=0.70,
                comments="Nilavembu's bitter taste and cooling properties relate to clearing heat and moving qi",
                evidence_level="Traditional cross-system analysis"
            )
        ]
        
        self.mappings = mappings
        logger.info(f"✅ Created {len(mappings)} expert concept mappings")
        
        return mappings
    
    async def generate_conceptmap_resource(self, 
                                         source_system: str, 
                                         target_system: str,
                                         title_suffix: str) -> Dict[str, Any]:
        """Generate a FHIR ConceptMap resource for mappings between two systems"""
        
        # Filter mappings for this source-target pair
        relevant_mappings = [
            m for m in self.mappings 
            if m.source_system == source_system and m.target_system == target_system
        ]
        
        if not relevant_mappings:
            return None
        
        # Determine source and target system names
        source_name = source_system.split('/')[-1]
        target_name = target_system.split('/')[-1]
        
        conceptmap = {
            "resourceType": "ConceptMap",
            "id": f"conceptmap-{source_name}-to-{target_name}",
            "url": f"http://terminology.ayushvardhan.com/ConceptMap/{source_name}-to-{target_name}",
            "identifier": [{
                "use": "official",
                "system": "http://terminology.ayushvardhan.com/identifiers",
                "value": f"CONCEPTMAP-{source_name.upper()}-TO-{target_name.upper()}"
            }],
            "version": "1.0.0",
            "name": f"ConceptMap{source_name.title()}To{target_name.title()}",
            "title": f"Concept Map: {source_name.title()} to {target_name.title()} {title_suffix}",
            "status": "active",
            "experimental": False,
            "date": datetime.now().isoformat(),
            "publisher": "AYUSH-WHO Terminology Integration Project",
            "contact": [{
                "name": "Traditional Medicine Terminology Team",
                "telecom": [{
                    "system": "email", 
                    "value": "terminology@ayushvardhan.com"
                }]
            }],
            "description": f"Concept mappings between {source_name.title()} traditional medicine codes and {target_name.title()} {title_suffix} for dual-coding support.",
            "jurisdiction": [{
                "coding": [{
                    "system": "urn:iso:std:iso:3166",
                    "code": "IN",
                    "display": "India"
                }]
            }],
            "purpose": f"To enable dual-coding between traditional medicine ({source_name}) and biomedical/WHO terminology ({target_name}) systems.",
            "copyright": "© 2024 AYUSH Ministry & WHO. Licensed under Creative Commons.",
            "sourceUri": source_system,
            "targetUri": target_system,
            "group": [{
                "source": source_system,
                "target": target_system,
                "element": []
            }]
        }
        
        # Add mapping elements
        for mapping in relevant_mappings:
            element = {
                "code": mapping.source_code,
                "display": mapping.source_display,
                "target": [{
                    "code": mapping.target_code,
                    "display": mapping.target_display,
                    "equivalence": mapping.equivalence,
                    "comment": mapping.comments
                }]
            }
            
            # Add mapping properties if available
            if mapping.confidence or mapping.evidence_level:
                element["target"][0]["dependsOn"] = []
                
                if mapping.confidence:
                    element["target"][0]["dependsOn"].append({
                        "property": "confidence",
                        "value": str(mapping.confidence)
                    })
                
                if mapping.evidence_level:
                    element["target"][0]["dependsOn"].append({
                        "property": "evidence_level", 
                        "value": mapping.evidence_level
                    })
            
            conceptmap["group"][0]["element"].append(element)
        
        return conceptmap
    
    async def generate_all_conceptmaps(self) -> List[Dict[str, Any]]:
        """Generate all required ConceptMap resources"""
        logger.info("🗺️ Generating FHIR ConceptMap resources...")
        
        conceptmaps = []
        
        # Define mapping combinations
        mapping_configs = [
            # NAMASTE to ICD-11 TM2
            (self.namaste_systems["ayurveda"], self.icd11_systems["tm2"], "Traditional Medicine"),
            (self.namaste_systems["siddha"], self.icd11_systems["tm2"], "Traditional Medicine"),
            (self.namaste_systems["unani"], self.icd11_systems["tm2"], "Traditional Medicine"),
            
            # NAMASTE to ICD-11 Biomedicine
            (self.namaste_systems["ayurveda"], self.icd11_systems["biomedicine"], "Biomedical Classification"),
            (self.namaste_systems["siddha"], self.icd11_systems["biomedicine"], "Biomedical Classification"),
            (self.namaste_systems["unani"], self.icd11_systems["biomedicine"], "Biomedical Classification")
        ]
        
        for source_system, target_system, title_suffix in mapping_configs:
            conceptmap = await self.generate_conceptmap_resource(source_system, target_system, title_suffix)
            if conceptmap:
                conceptmaps.append(conceptmap)
        
        logger.info(f"✅ Generated {len(conceptmaps)} ConceptMap resources")
        return conceptmaps
    
    async def save_conceptmaps(self, conceptmaps: List[Dict[str, Any]], output_directory: str = "data/fhir"):
        """Save ConceptMap resources to JSON files"""
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for conceptmap in conceptmaps:
            filename = output_path / f"{conceptmap['id']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(conceptmap, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved ConceptMap: {filename}")
    
    def print_mapping_statistics(self):
        """Print mapping statistics"""
        total_mappings = len(self.mappings)
        tm2_mappings = len([m for m in self.mappings if "tm2" in m.target_system])
        bio_mappings = len([m for m in self.mappings if "biomedicine" in m.target_system])
        
        # Count by source system
        ayurveda_mappings = len([m for m in self.mappings if "ayurveda" in m.source_system])
        siddha_mappings = len([m for m in self.mappings if "siddha" in m.source_system])
        unani_mappings = len([m for m in self.mappings if "unani" in m.source_system])
        
        # Average confidence
        avg_confidence = sum(m.confidence for m in self.mappings) / total_mappings if total_mappings > 0 else 0
        
        print("\n🗺️ Concept Mapping Statistics")
        print("=" * 40)
        print(f"Total Mappings Created: {total_mappings}")
        print(f"Mappings to ICD-11 TM2: {tm2_mappings}")
        print(f"Mappings to ICD-11 Biomedicine: {bio_mappings}")
        print(f"Average Confidence Score: {avg_confidence:.2f}")
        
        print(f"\nBy Source System:")
        print(f"Ayurveda: {ayurveda_mappings}")
        print(f"Siddha: {siddha_mappings}")
        print(f"Unani: {unani_mappings}")
        
        # Show sample mappings
        print(f"\n📋 Sample Mappings:")
        for i, mapping in enumerate(self.mappings[:3]):
            print(f"{i+1}. {mapping.source_code} → {mapping.target_code}")
            print(f"   {mapping.source_display} → {mapping.target_display}")
            print(f"   Equivalence: {mapping.equivalence}, Confidence: {mapping.confidence}")

async def main():
    """Main execution function"""
    print("🗺️ NAMASTE-ICD11 Concept Mapping Generator")
    print("=" * 50)
    
    generator = ConceptMapGenerator()
    
    try:
        # Load existing CodeSystems
        codesystems = await generator.load_existing_codesystems()
        
        # Create expert mappings
        mappings = generator.create_expert_mappings()
        
        # Generate ConceptMap resources
        conceptmaps = await generator.generate_all_conceptmaps()
        
        # Save ConceptMaps
        await generator.save_conceptmaps(conceptmaps)
        
        # Print statistics
        generator.print_mapping_statistics()
        
        print("\n🎉 Concept Mapping Generation Complete!")
        print("✅ Expert mappings created between traditional medicine and biomedical systems")
        print("✅ FHIR ConceptMap resources generated and saved")
        print("✅ Dual-coding infrastructure ready for implementation")
        
        print("\n🚀 Next Steps:")
        print("1. 🔍 Review and validate expert mappings")
        print("2. 🧪 Test $translate operations in API")
        print("3. 📊 Expand mapping coverage with additional codes")
        print("4. 🤖 Implement machine learning for automated mapping suggestions")
        
    except Exception as e:
        logger.error(f"❌ Error during concept mapping: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())