#!/usr/bin/env python3
"""
Seed test data for NAMASTE Traditional Medicine and WHO ICD-11 integration testing
Creates sample CodeSystems, ConceptMaps, and ValueSets for Phase 6 validation
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.database.connection import init_database, get_database, close_database
from app.models.fhir.resources import CodeSystem, ConceptMap, ValueSet
from app.models.namaste.traditional_medicine import NAMASTECodeSystem, AyushSystemEnum
from app.models.who.icd11 import ICD11CodeSystem, ICD11ModuleEnum


async def create_namaste_ayurveda_codesystem() -> Dict[str, Any]:
    """Create NAMASTE Ayurveda CodeSystem with sample codes"""
    concepts = [
        {
            "code": "AYU-H-001",
            "display": "Jwara (Fever)",
            "definition": "A general term for fever conditions in Ayurveda, characterized by elevated body temperature",
            "property": [
                {
                    "code": "dosha",
                    "valueString": "Pitta"
                },
                {
                    "code": "category",
                    "valueString": "Clinical Condition"
                },
                {
                    "code": "severity",
                    "valueString": "Moderate"
                }
            ]
        },
        {
            "code": "AYU-H-002", 
            "display": "Atisara (Diarrhea)",
            "definition": "Loose, watery bowel movements in Ayurvedic terms",
            "property": [
                {
                    "code": "dosha",
                    "valueString": "Vata-Pitta"
                },
                {
                    "code": "category", 
                    "valueString": "Digestive Disorder"
                }
            ]
        },
        {
            "code": "AYU-M-001",
            "display": "Ashwagandha (Withania somnifera)",
            "definition": "A rejuvenative herb used in Ayurveda for strength and vitality",
            "property": [
                {
                    "code": "rasa",
                    "valueString": "Tikta, Kashaya"
                },
                {
                    "code": "virya",
                    "valueString": "Ushna"
                },
                {
                    "code": "category",
                    "valueString": "Medicinal Plant"
                }
            ]
        },
        {
            "code": "AYU-T-001",
            "display": "Panchakarma",
            "definition": "Five-fold detoxification and rejuvenation therapies in Ayurveda",
            "property": [
                {
                    "code": "category",
                    "valueString": "Therapeutic Procedure"
                },
                {
                    "code": "duration",
                    "valueString": "21-28 days"
                }
            ]
        }
    ]
    
    return {
        "resourceType": "CodeSystem",
        "id": "namaste-ayurveda",
        "url": "http://terminology.ayushvardhan.com/CodeSystem/namaste-ayurveda",
        "version": "1.0.0",
        "name": "NAMASTEAyurveda",
        "title": "NAMASTE Ayurveda Traditional Medicine CodeSystem",
        "status": "active",
        "experimental": False,
        "date": datetime.utcnow().isoformat(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": "NAMASTE (National AYUSH Morbidity and Standardized Terminologies Electronic) CodeSystem for Ayurveda traditional medicine system",
        "caseSensitive": True,
        "content": "complete",
        "count": len(concepts),
        "property": [
            {
                "code": "dosha",
                "description": "Ayurvedic constitutional type or imbalance",
                "type": "string"
            },
            {
                "code": "rasa", 
                "description": "Taste quality of medicinal substances",
                "type": "string"
            },
            {
                "code": "virya",
                "description": "Potency or thermal quality",
                "type": "string"
            },
            {
                "code": "category",
                "description": "Classification category",
                "type": "string"
            }
        ],
        "concept": concepts
    }


async def create_namaste_siddha_codesystem() -> Dict[str, Any]:
    """Create NAMASTE Siddha CodeSystem with sample codes"""
    concepts = [
        {
            "code": "SID-H-001",
            "display": "Suram (Fever)",
            "definition": "Fever condition in Siddha medicine",
            "property": [
                {
                    "code": "thathu",
                    "valueString": "Pitham"
                },
                {
                    "code": "category",
                    "valueString": "Clinical Condition"
                }
            ]
        },
        {
            "code": "SID-M-001", 
            "display": "Nilavembu (Andrographis paniculata)",
            "definition": "A bitter herb used in Siddha medicine for fever and infections",
            "property": [
                {
                    "code": "suvai",
                    "valueString": "Kaippu"
                },
                {
                    "code": "category",
                    "valueString": "Medicinal Plant"
                }
            ]
        }
    ]
    
    return {
        "resourceType": "CodeSystem",
        "id": "namaste-siddha",
        "url": "http://terminology.ayushvardhan.com/CodeSystem/namaste-siddha",
        "version": "1.0.0", 
        "name": "NAMASTESiddha",
        "title": "NAMASTE Siddha Traditional Medicine CodeSystem",
        "status": "active",
        "experimental": False,
        "date": datetime.utcnow().isoformat(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": "NAMASTE CodeSystem for Siddha traditional medicine system",
        "caseSensitive": True,
        "content": "complete",
        "count": len(concepts),
        "property": [
            {
                "code": "thathu",
                "description": "Siddha constitutional elements",
                "type": "string" 
            },
            {
                "code": "suvai",
                "description": "Taste classification in Siddha",
                "type": "string"
            },
            {
                "code": "category",
                "description": "Classification category",
                "type": "string"
            }
        ],
        "concept": concepts
    }


async def create_icd11_biomedicine_codesystem() -> Dict[str, Any]:
    """Create WHO ICD-11 Biomedicine CodeSystem with sample codes"""
    concepts = [
        {
            "code": "1C62.Z",
            "display": "Fever, unspecified",
            "definition": "Fever without specification of cause or type"
        },
        {
            "code": "1D2Z", 
            "display": "Diarrhoea, unspecified",
            "definition": "Loose or liquid stools occurring more frequently than normal"
        },
        {
            "code": "XM8V38",
            "display": "Withania somnifera",
            "definition": "Plant species used in traditional medicine, commonly known as Ashwagandha"
        }
    ]
    
    return {
        "resourceType": "CodeSystem",
        "id": "icd11-biomedicine",
        "url": "http://terminology.ayushvardhan.com/CodeSystem/icd11-biomedicine",
        "version": "2024-01",
        "name": "ICD11Biomedicine", 
        "title": "WHO ICD-11 Biomedicine Module",
        "status": "active",
        "experimental": False,
        "date": datetime.utcnow().isoformat(),
        "publisher": "World Health Organization",
        "description": "WHO ICD-11 Biomedicine module for biomedical conditions and entities",
        "caseSensitive": True,
        "content": "complete",
        "count": len(concepts),
        "concept": concepts
    }


async def create_ayurveda_to_icd11_conceptmap() -> Dict[str, Any]:
    """Create ConceptMap mapping NAMASTE Ayurveda to ICD-11 Biomedicine"""
    return {
        "resourceType": "ConceptMap",
        "id": "namaste-ayurveda-to-icd11-biomedicine",
        "url": "http://terminology.ayushvardhan.com/ConceptMap/namaste-ayurveda-to-icd11-biomedicine",
        "version": "1.0.0",
        "name": "NAMASTEAyurvedaToICD11Biomedicine",
        "title": "NAMASTE Ayurveda to WHO ICD-11 Biomedicine Mapping",
        "status": "active",
        "experimental": False,
        "date": datetime.utcnow().isoformat(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": "Concept mapping between NAMASTE Ayurveda traditional medicine codes and WHO ICD-11 Biomedicine codes",
        "sourceUri": "http://terminology.ayushvardhan.com/CodeSystem/namaste-ayurveda",
        "targetUri": "http://terminology.ayushvardhan.com/CodeSystem/icd11-biomedicine",
        "group": [
            {
                "source": "http://terminology.ayushvardhan.com/CodeSystem/namaste-ayurveda",
                "target": "http://terminology.ayushvardhan.com/CodeSystem/icd11-biomedicine",
                "element": [
                    {
                        "code": "AYU-H-001",
                        "display": "Jwara (Fever)",
                        "target": [
                            {
                                "code": "1C62.Z",
                                "display": "Fever, unspecified",
                                "equivalence": "equivalent",
                                "comment": "Direct mapping from Ayurvedic fever concept to ICD-11 fever"
                            }
                        ]
                    },
                    {
                        "code": "AYU-H-002",
                        "display": "Atisara (Diarrhea)", 
                        "target": [
                            {
                                "code": "1D2Z",
                                "display": "Diarrhoea, unspecified",
                                "equivalence": "equivalent",
                                "comment": "Mapping Ayurvedic diarrhea concept to ICD-11 diarrhea"
                            }
                        ]
                    },
                    {
                        "code": "AYU-M-001",
                        "display": "Ashwagandha (Withania somnifera)",
                        "target": [
                            {
                                "code": "XM8V38", 
                                "display": "Withania somnifera",
                                "equivalence": "equivalent",
                                "comment": "Direct plant species mapping"
                            }
                        ]
                    }
                ]
            }
        ]
    }


async def create_ayush_herbs_valueset() -> Dict[str, Any]:
    """Create ValueSet for AYUSH medicinal herbs"""
    return {
        "resourceType": "ValueSet",
        "id": "ayush-medicinal-herbs",
        "url": "http://terminology.ayushvardhan.com/ValueSet/ayush-medicinal-herbs",
        "version": "1.0.0",
        "name": "AYUSHMedicinalHerbs",
        "title": "AYUSH Medicinal Herbs ValueSet",
        "status": "active",
        "experimental": False,
        "date": datetime.utcnow().isoformat(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": "ValueSet containing medicinal herbs used across AYUSH systems",
        "compose": {
            "include": [
                {
                    "system": "http://terminology.ayushvardhan.com/CodeSystem/namaste-ayurveda",
                    "filter": [
                        {
                            "property": "category",
                            "op": "=",
                            "value": "Medicinal Plant"
                        }
                    ]
                },
                {
                    "system": "http://terminology.ayushvardhan.com/CodeSystem/namaste-siddha",
                    "filter": [
                        {
                            "property": "category", 
                            "op": "=",
                            "value": "Medicinal Plant"
                        }
                    ]
                }
            ]
        }
    }


async def seed_database():
    """Seed the database with test data"""
    try:
        print("🌱 Starting database seeding...")
        await init_database()
        db = await get_database()
        
        # Create CodeSystems
        print("📚 Creating CodeSystems...")
        
        ayurveda_cs = await create_namaste_ayurveda_codesystem()
        await db.codesystems.insert_one(ayurveda_cs)
        print(f"✅ Created NAMASTE Ayurveda CodeSystem with {ayurveda_cs['count']} concepts")
        
        siddha_cs = await create_namaste_siddha_codesystem()
        await db.codesystems.insert_one(siddha_cs)
        print(f"✅ Created NAMASTE Siddha CodeSystem with {siddha_cs['count']} concepts")
        
        icd11_cs = await create_icd11_biomedicine_codesystem()
        await db.codesystems.insert_one(icd11_cs)
        print(f"✅ Created ICD-11 Biomedicine CodeSystem with {icd11_cs['count']} concepts")
        
        # Create ConceptMaps
        print("🔗 Creating ConceptMaps...")
        
        conceptmap = await create_ayurveda_to_icd11_conceptmap()
        await db.conceptmaps.insert_one(conceptmap)
        print(f"✅ Created Ayurveda to ICD-11 ConceptMap with {len(conceptmap['group'][0]['element'])} mappings")
        
        # Create ValueSets
        print("📋 Creating ValueSets...")
        
        valueset = await create_ayush_herbs_valueset()
        await db.valuesets.insert_one(valueset)
        print("✅ Created AYUSH Medicinal Herbs ValueSet")
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nSeeded Resources:")
        print("- 3 CodeSystems (NAMASTE Ayurveda, NAMASTE Siddha, ICD-11 Biomedicine)")
        print("- 1 ConceptMap (Ayurveda to ICD-11 mappings)")  
        print("- 1 ValueSet (AYUSH Medicinal Herbs)")
        print(f"\nTotal concepts: {ayurveda_cs['count'] + siddha_cs['count'] + icd11_cs['count']}")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(seed_database())