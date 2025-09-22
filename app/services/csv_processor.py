"""
NAMASTE Data File to FHIR CodeSystem Processor
Converts traditional medicine data files (CSV/Excel) to FHIR R4 CodeSystems
Supports Ayurveda, Unani, and Siddha systems
"""

import csv
import io
import json
import pandas as pd
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError
from enum import Enum

from app.models.fhir.resources import CodeSystem, CodeSystemConcept, CodeSystemProperty
from app.models.fhir.base import PublicationStatusEnum


class TraditionalMedicineSystem(str, Enum):
    """Traditional medicine systems supported"""
    AYURVEDA = "ayurveda"
    UNANI = "unani"
    SIDDHA = "siddha"


class CSVFieldMapping(BaseModel):
    """Field mapping configuration for CSV columns"""
    sr_no: str = "Sr No."
    id_field: str = "NAMC_ID"
    code_field: str = "NAMC_CODE"
    term_field: str = "NAMC_TERM"
    definition_field: Optional[str] = None
    long_definition_field: Optional[str] = None
    native_term_field: Optional[str] = None
    diacritical_field: Optional[str] = None
    devanagari_field: Optional[str] = None


class AyurvedaCSVMapping(CSVFieldMapping):
    """Ayurveda CSV field mapping"""
    term_field: str = "NAMC_term"
    definition_field: str = "Short_definition"
    long_definition_field: str = "Long_definition"
    diacritical_field: str = "NAMC_term_diacritical"
    devanagari_field: str = "NAMC_term_DEVANAGARI"


class UnaniCSVMapping(CSVFieldMapping):
    """Unani CSV field mapping"""
    id_field: str = "NUMC_ID"
    code_field: str = "NUMC_CODE"
    term_field: str = "NUMC_TERM"
    native_term_field: str = "Arabic_term"


class SiddhaCSVMapping(CSVFieldMapping):
    """Siddha CSV field mapping"""
    term_field: str = "NAMC_TERM"
    native_term_field: str = "Tamil_term"
    definition_field: str = "Short_definition"


class ProcessingResult(BaseModel):
    """Result of CSV processing"""
    success: bool
    code_system: Optional[CodeSystem] = None
    concepts_processed: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class NAMASTEDataProcessor:
    """Processes NAMASTE data files (CSV/Excel) into FHIR CodeSystems"""
    
    def __init__(self):
        self.field_mappings = {
            TraditionalMedicineSystem.AYURVEDA: AyurvedaCSVMapping(),
            TraditionalMedicineSystem.UNANI: UnaniCSVMapping(),
            TraditionalMedicineSystem.SIDDHA: SiddhaCSVMapping()
        }
    
    def read_data_file(self, file_content: bytes, filename: str) -> pd.DataFrame:
        """Read data from CSV or Excel file and return as DataFrame"""
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # Handle CSV files
            try:
                # Try UTF-8 first
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1 for older CSV files
                text_content = file_content.decode('latin-1')
            
            return pd.read_csv(io.StringIO(text_content))
            
        elif file_extension in ['xls', 'xlsx']:
            # Handle Excel files
            return pd.read_excel(io.BytesIO(file_content), engine='openpyxl' if file_extension == 'xlsx' else 'xlrd')
            
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Supported formats: CSV, XLS, XLSX")
    
    def dataframe_to_csv_content(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to CSV string for compatibility with existing methods"""
        return df.to_csv(index=False)
    
    def detect_system_from_data(self, file_content: bytes, filename: str) -> Optional[TraditionalMedicineSystem]:
        """Auto-detect traditional medicine system from file headers"""
        try:
            df = self.read_data_file(file_content, filename)
            headers = df.columns.tolist()
            
            # Check for system-specific markers
            if "NAMC_term_DEVANAGARI" in headers:
                return TraditionalMedicineSystem.AYURVEDA
            elif "Arabic_term" in headers:
                return TraditionalMedicineSystem.UNANI
            elif "Tamil_term" in headers:
                return TraditionalMedicineSystem.SIDDHA
            elif "NAMC_TERM" in headers:
                return TraditionalMedicineSystem.AYURVEDA  # Default fallback
            
            return None
        except Exception:
            return None
    
    def detect_system_from_csv(self, csv_content: str) -> Optional[TraditionalMedicineSystem]:
        """Legacy method for CSV content - converts to DataFrame approach"""
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            headers = df.columns.tolist()
            
            # Check for system-specific markers
            if "NAMC_term_DEVANAGARI" in headers:
                return TraditionalMedicineSystem.AYURVEDA
            elif "Arabic_term" in headers:
                return TraditionalMedicineSystem.UNANI
            elif "Tamil_term" in headers:
                return TraditionalMedicineSystem.SIDDHA
            elif "NAMC_TERM" in headers:
                return TraditionalMedicineSystem.AYURVEDA  # Default fallback
            
            return None
        except Exception:
            return None
    
    def validate_csv_format(self, csv_content: str, system: TraditionalMedicineSystem) -> List[str]:
        """Validate CSV format against expected schema"""
        errors = []
        
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            headers = csv_reader.fieldnames or []
            mapping = self.field_mappings[system]
            
            # Check required fields
            required_fields = [mapping.sr_no, mapping.id_field, mapping.code_field, mapping.term_field]
            missing_fields = [field for field in required_fields if field not in headers]
            
            if missing_fields:
                errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Check data rows
            row_count = 0
            for row_num, row in enumerate(csv_reader, start=2):
                row_count += 1
                
                # Validate required field values
                if not row.get(mapping.code_field, "").strip():
                    errors.append(f"Row {row_num}: Missing code value")
                
                if not row.get(mapping.term_field, "").strip():
                    errors.append(f"Row {row_num}: Missing term value")
                
                # Stop validation after 100 errors to prevent overflow
                if len(errors) >= 100:
                    errors.append("... Too many errors, validation stopped")
                    break
            
            if row_count == 0:
                errors.append("CSV file contains no data rows")
        
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return errors
    
    def validate_data_file_format(self, file_content: bytes, filename: str, 
                                 system: TraditionalMedicineSystem) -> List[str]:
        """Validate data file format against expected schema"""
        try:
            # Read file into DataFrame
            df = self.read_data_file(file_content, filename)
            
            # Convert to CSV string for compatibility with existing validation
            csv_content = self.dataframe_to_csv_content(df)
            
            # Use existing CSV validation logic
            return self.validate_csv_format(csv_content, system)
            
        except Exception as e:
            return [f"Error reading file: {str(e)}"]
    
    def create_code_system_properties(self, system: TraditionalMedicineSystem) -> List[CodeSystemProperty]:
        """Create CodeSystem properties based on traditional medicine system"""
        properties = [
            CodeSystemProperty(
                code="definition",
                description="Concept definition in English",
                type="string"
            ),
            CodeSystemProperty(
                code="longDefinition",
                description="Detailed concept definition",
                type="string"
            )
        ]
        
        if system == TraditionalMedicineSystem.AYURVEDA:
            properties.extend([
                CodeSystemProperty(
                    code="diacritical",
                    description="Term with diacritical marks",
                    type="string"
                ),
                CodeSystemProperty(
                    code="devanagari",
                    description="Term in Devanagari script",
                    type="string"
                )
            ])
        elif system == TraditionalMedicineSystem.UNANI:
            properties.append(
                CodeSystemProperty(
                    code="arabic",
                    description="Term in Arabic script",
                    type="string"
                )
            )
        elif system == TraditionalMedicineSystem.SIDDHA:
            properties.append(
                CodeSystemProperty(
                    code="tamil",
                    description="Term in Tamil script",
                    type="string"
                )
            )
        
        return properties
    
    def create_concept_from_row(self, row: Dict[str, str], mapping: CSVFieldMapping, 
                               system: TraditionalMedicineSystem) -> Optional[CodeSystemConcept]:
        """Create a FHIR CodeSystemConcept from a CSV row"""
        try:
            code = row.get(mapping.code_field, "").strip()
            display = row.get(mapping.term_field, "").strip()
            
            if not code or not display:
                return None
            
            # Create base concept
            concept = CodeSystemConcept(
                code=code,
                display=display
            )
            
            # Add definition if available
            definition = row.get(mapping.definition_field or "", "").strip()
            if definition:
                concept.definition = definition
            
            # Add properties based on system
            properties = []
            
            # Long definition
            long_def = row.get(mapping.long_definition_field or "", "").strip()
            if long_def:
                properties.append({
                    "code": "longDefinition",
                    "valueString": long_def
                })
            
            # System-specific properties
            if system == TraditionalMedicineSystem.AYURVEDA:
                diacritical = row.get(mapping.diacritical_field or "", "").strip()
                if diacritical:
                    properties.append({
                        "code": "diacritical",
                        "valueString": diacritical
                    })
                
                devanagari = row.get(mapping.devanagari_field or "", "").strip()
                if devanagari:
                    properties.append({
                        "code": "devanagari",
                        "valueString": devanagari
                    })
            
            elif system == TraditionalMedicineSystem.UNANI:
                arabic = row.get(mapping.native_term_field or "", "").strip()
                if arabic:
                    properties.append({
                        "code": "arabic",
                        "valueString": arabic
                    })
            
            elif system == TraditionalMedicineSystem.SIDDHA:
                tamil = row.get(mapping.native_term_field or "", "").strip()
                if tamil:
                    properties.append({
                        "code": "tamil",
                        "valueString": tamil
                    })
            
            if properties:
                concept.property = properties
            
            return concept
        
        except Exception as e:
            return None
    
    def process_data_file_to_codesystem(self, file_content: bytes, filename: str,
                                       system: Optional[TraditionalMedicineSystem] = None,
                                       code_system_id: Optional[str] = None) -> ProcessingResult:
        """Process data file (CSV/Excel) and convert to FHIR CodeSystem"""
        
        try:
            # Read file into DataFrame
            df = self.read_data_file(file_content, filename)
            
            # Convert to CSV string for compatibility with existing processing
            csv_content = self.dataframe_to_csv_content(df)
            
            # Auto-detect system if not provided
            if system is None:
                system = self.detect_system_from_data(file_content, filename)
                if system is None:
                    return ProcessingResult(
                        success=False,
                        errors=["Unable to detect traditional medicine system from file"]
                    )
            
            # Use existing CSV processing logic
            return self.process_csv_to_codesystem(csv_content, system, code_system_id)
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                errors=[f"Error processing file: {str(e)}"]
            )
    
    def process_csv_to_codesystem(self, csv_content: str, 
                                 system: Optional[TraditionalMedicineSystem] = None,
                                 code_system_id: Optional[str] = None) -> ProcessingResult:
        """Process CSV content and convert to FHIR CodeSystem"""
        
        # Auto-detect system if not provided
        if system is None:
            system = self.detect_system_from_csv(csv_content)
            if system is None:
                return ProcessingResult(
                    success=False,
                    errors=["Unable to detect traditional medicine system from CSV"]
                )
        
        # Validate CSV format
        validation_errors = self.validate_csv_format(csv_content, system)
        if validation_errors:
            return ProcessingResult(
                success=False,
                errors=validation_errors
            )
        
        # Process CSV
        mapping = self.field_mappings[system]
        concepts = []
        errors = []
        warnings = []
        
        try:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            for row_num, row in enumerate(csv_reader, start=2):
                concept = self.create_concept_from_row(row, mapping, system)
                
                if concept:
                    concepts.append(concept)
                else:
                    code = row.get(mapping.code_field, "").strip()
                    warnings.append(f"Row {row_num}: Skipped concept with code '{code}' due to missing required data")
            
            if not concepts:
                return ProcessingResult(
                    success=False,
                    errors=["No valid concepts found in CSV"]
                )
            
            # Create CodeSystem
            system_id = code_system_id or f"namaste-{system.value}"
            
            code_system = CodeSystem(
                id=system_id,
                url=f"http://terminology.ayushvardhan.com/CodeSystem/{system_id}",
                version="1.0.0",
                name=f"NAMASTE{system.value.title()}",
                title=f"NAMASTE {system.value.title()} Traditional Medicine CodeSystem",
                status=PublicationStatusEnum.ACTIVE,
                experimental=False,
                date=datetime.now(timezone.utc),
                publisher="Ministry of AYUSH, Government of India",
                description=f"NAMASTE standardized terminology for {system.value.title()} traditional medicine system",
                caseSensitive=True,
                content="complete",
                count=len(concepts),
                property=self.create_code_system_properties(system),
                concept=concepts
            )
            
            return ProcessingResult(
                success=True,
                code_system=code_system,
                concepts_processed=len(concepts),
                errors=errors,
                warnings=warnings
            )
        
        except Exception as e:
            return ProcessingResult(
                success=False,
                errors=[f"Processing error: {str(e)}"]
            )
    
    def export_codesystem_to_csv(self, code_system: CodeSystem, 
                                system: TraditionalMedicineSystem) -> str:
        """Export FHIR CodeSystem back to CSV format"""
        
        mapping = self.field_mappings[system]
        output = io.StringIO()
        
        # Determine fieldnames based on system
        fieldnames = [mapping.sr_no, mapping.id_field, mapping.code_field, mapping.term_field]
        
        if mapping.definition_field:
            fieldnames.append(mapping.definition_field)
        if mapping.long_definition_field:
            fieldnames.append(mapping.long_definition_field)
        if mapping.diacritical_field:
            fieldnames.append(mapping.diacritical_field)
        if mapping.devanagari_field:
            fieldnames.append(mapping.devanagari_field)
        if mapping.native_term_field:
            fieldnames.append(mapping.native_term_field)
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write concepts
        for idx, concept in enumerate(code_system.concept or [], start=1):
            row = {
                mapping.sr_no: str(idx),
                mapping.id_field: str(idx),
                mapping.code_field: concept.code,
                mapping.term_field: concept.display or ""
            }
            
            # Add definition
            if mapping.definition_field and concept.definition:
                row[mapping.definition_field] = concept.definition
            
            # Add properties
            for prop in concept.property or []:
                prop_code = prop.get("code", "")
                prop_value = prop.get("valueString", "")
                
                if prop_code == "longDefinition" and mapping.long_definition_field:
                    row[mapping.long_definition_field] = prop_value
                elif prop_code == "diacritical" and mapping.diacritical_field:
                    row[mapping.diacritical_field] = prop_value
                elif prop_code == "devanagari" and mapping.devanagari_field:
                    row[mapping.devanagari_field] = prop_value
                elif prop_code in ["arabic", "tamil"] and mapping.native_term_field:
                    row[mapping.native_term_field] = prop_value
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def get_system_info(self, system: TraditionalMedicineSystem) -> Dict[str, Any]:
        """Get information about a traditional medicine system"""
        
        system_info = {
            TraditionalMedicineSystem.AYURVEDA: {
                "name": "Ayurveda",
                "description": "Ancient Indian system of medicine",
                "language": "Sanskrit",
                "scripts": ["Latin", "Devanagari"],
                "fields": ["code", "term", "diacritical", "devanagari", "definition", "long_definition"]
            },
            TraditionalMedicineSystem.UNANI: {
                "name": "Unani",
                "description": "Traditional system of medicine practiced in India",
                "language": "Arabic/Persian",
                "scripts": ["Latin", "Arabic"],
                "fields": ["code", "term", "arabic_term"]
            },
            TraditionalMedicineSystem.SIDDHA: {
                "name": "Siddha",
                "description": "Traditional system of medicine from Tamil Nadu",
                "language": "Tamil",
                "scripts": ["Latin", "Tamil"],
                "fields": ["code", "term", "tamil_term", "definition"]
            }
        }
        
        return system_info.get(system, {})
