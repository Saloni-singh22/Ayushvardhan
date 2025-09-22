"""
Data File Processing API Endpoints
FastAPI routes for NAMASTE data file (CSV/Excel) to FHIR CodeSystem conversion
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response, Path
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io
import json
from datetime import datetime

from app.services.csv_processor import NAMASTEDataProcessor, TraditionalMedicineSystem, ProcessingResult
from app.models.fhir.resources import CodeSystem, Bundle, BundleEntry
from app.models.fhir.base import BundleTypeEnum
from app.database import get_database


router = APIRouter(prefix="/data", tags=["Data File Processing"])
data_processor = NAMASTEDataProcessor()


@router.post("/upload", 
             summary="Upload and Process NAMASTE Data File",
             description="Upload a data file (CSV/Excel) containing NAMASTE traditional medicine data and convert it to FHIR CodeSystem",
             response_description="Processing result with FHIR CodeSystem")
async def upload_data_file(
    file: UploadFile = File(..., description="Data file to process (CSV, XLS, XLSX)"),
    system: Optional[TraditionalMedicineSystem] = Query(None, description="Traditional medicine system (auto-detected if not provided)"),
    code_system_id: Optional[str] = Query(None, description="Custom CodeSystem ID"),
    save_to_database: bool = Query(True, description="Save the generated CodeSystem to database")
):
    """
    Upload and process a NAMASTE data file (CSV/Excel) into a FHIR CodeSystem.
    
    Supported File Formats:
    - CSV: Comma-separated values
    - XLS: Legacy Excel format
    - XLSX: Modern Excel format
    
    Supported Systems:
    - Ayurveda: Sanskrit terms with Devanagari script support
    - Unani: Arabic/Persian terms with Arabic script support  
    - Siddha: Tamil terms with Tamil script support
    
    Format Detection:
    - Auto-detects system based on column headers
    - Validates required fields for each system
    
    Returns:
    - FHIR CodeSystem resource
    - Processing statistics
    - Validation errors/warnings
    """
    
    # Validate file format
    if file.filename:
        supported_extensions = ['csv', 'xls', 'xlsx']
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_extension}. Supported formats: {', '.join(supported_extensions).upper()}"
            )
    
    try:
        # Read file content
        content = await file.read()
        
        # Process data file
        result = data_processor.process_data_file_to_codesystem(
            file_content=content,
            filename=file.filename or "data_file.csv",
            system=system,
            code_system_id=code_system_id
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "CSV processing failed",
                    "errors": result.errors
                }
            )
        
        # Save to database if requested
        if save_to_database and result.code_system:
            try:
                db = await get_database()
                
                # Convert to dict for MongoDB and clean data for text indexing
                code_system_dict = result.code_system.model_dump()
                
                # Clean the data to ensure text index compatibility
                def clean_for_text_index(obj):
                    """Recursively clean object to ensure MongoDB text index compatibility"""
                    if isinstance(obj, dict):
                        cleaned = {}
                        for key, value in obj.items():
                            if key == "language" and value is not None:
                                # Ensure language fields are strings for text indexing
                                cleaned[key] = str(value) if value is not None else None
                            else:
                                cleaned[key] = clean_for_text_index(value)
                        return cleaned
                    elif isinstance(obj, list):
                        return [clean_for_text_index(item) for item in obj]
                    else:
                        return obj
                
                code_system_dict = clean_for_text_index(code_system_dict)
                
                # Check if document already exists
                existing_doc = await db.codesystems.find_one(
                    {"url": result.code_system.url, "version": result.code_system.version}
                )
                
                if existing_doc:
                    # Update existing document (remove _id to avoid immutable field error)
                    code_system_dict.pop("_id", None)
                    update_result = await db.codesystems.update_one(
                        {"url": result.code_system.url, "version": result.code_system.version},
                        {"$set": code_system_dict}
                    )
                    print(f"Database update: matched={update_result.matched_count}, modified={update_result.modified_count}")
                else:
                    # Insert new document with _id
                    code_system_dict["_id"] = result.code_system.id
                    insert_result = await db.codesystems.insert_one(code_system_dict)
                    print(f"Database insert: {insert_result.inserted_id}")
                
                # Verify save
                count = await db.codesystems.count_documents({})
                print(f"Total documents in database after save: {count}")
                
            except Exception as db_error:
                print(f"Database save error: {db_error}")
                import traceback
                traceback.print_exc()
                # Don't raise the error to avoid breaking the response
        
        return {
            "success": True,
            "message": f"Successfully processed {result.concepts_processed} concepts",
            "code_system": result.code_system,
            "statistics": {
                "concepts_processed": result.concepts_processed,
                "errors_count": len(result.errors),
                "warnings_count": len(result.warnings)
            },
            "errors": result.errors,
            "warnings": result.warnings,
            "saved_to_database": save_to_database
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid CSV file encoding. Please use UTF-8 encoding.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/validate",
             summary="Validate NAMASTE Data File Format",
             description="Validate a data file (CSV/Excel) format without processing")
async def validate_data_file(
    file: UploadFile = File(..., description="Data file to validate (CSV, XLS, XLSX)"),
    system: Optional[TraditionalMedicineSystem] = Query(None, description="Traditional medicine system to validate against")
):
    """
    Validate data file format and structure without creating a CodeSystem.
    
    Supported File Formats:
    - CSV: Comma-separated values
    - XLS: Legacy Excel format
    - XLSX: Modern Excel format
    
    Validation Checks:
    - Required column headers
    - Data completeness
    - Format consistency
    - System-specific requirements
    
    Returns:
    - Validation status
    - List of errors (if any)
    - List of warnings (if any)
    """
    
    # Validate file format
    if file.filename:
        supported_extensions = ['csv', 'xls', 'xlsx']
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_extension}. Supported formats: {', '.join(supported_extensions).upper()}"
            )
    
    try:
        content = await file.read()
        
        # Auto-detect system if not provided
        if system is None:
            system = data_processor.detect_system_from_data(content, file.filename or "data_file.csv")
            if system is None:
                raise HTTPException(status_code=400, detail="Unable to detect traditional medicine system from data file")
        
        # Validate format
        errors = data_processor.validate_data_file_format(content, file.filename or "data_file.csv", system)
        
        return {
            "valid": len(errors) == 0,
            "detected_system": system,
            "errors": errors,
            "system_info": data_processor.get_system_info(system)
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please ensure the file is properly encoded.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/export/{code_system_id}",
            summary="Export CodeSystem to Data File",
            description="Export a FHIR CodeSystem back to data file format (CSV)")
async def export_codesystem_to_data_file(
    code_system_id: str,
    system: TraditionalMedicineSystem = Query(..., description="Traditional medicine system for data file format"),
    format_type: str = Query("download", enum=["download", "inline"], description="Response format")
):
    """
    Export a FHIR CodeSystem back to data file format (CSV).
    
    Parameters:
    - code_system_id: ID of the CodeSystem to export
    - system: Traditional medicine system for proper data file formatting
    - format_type: 'download' for file download, 'inline' for browser display
    """
    
    try:
        db = await get_database()
        
        # Retrieve CodeSystem
        code_system_data = db.codesystems.find_one({"_id": code_system_id})
        if not code_system_data:
            raise HTTPException(status_code=404, detail=f"CodeSystem '{code_system_id}' not found")
        
        # Convert to Pydantic model
        code_system = CodeSystem(**code_system_data)
        
        # Export to CSV
        csv_content = data_processor.export_codesystem_to_csv(code_system, system)
        
        # Return as file download or inline
        if format_type == "download":
            filename = f"{code_system_id}_{system.value}.csv"
            response = StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            return response
        else:
            return Response(content=csv_content, media_type="text/plain")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@router.get("/systems",
            summary="List Traditional Medicine Systems",
            description="Get information about supported traditional medicine systems")
async def list_systems():
    """
    Get information about all supported traditional medicine systems.
    
    Returns:
    - System names and descriptions
    - Supported languages and scripts
    - Data file field requirements
    """
    
    systems_info = {}
    for system in TraditionalMedicineSystem:
        systems_info[system.value] = data_processor.get_system_info(system)
    
    return {
        "supported_systems": list(TraditionalMedicineSystem),
        "systems_info": systems_info,
        "auto_detection": "Systems can be auto-detected from CSV headers",
        "csv_requirements": {
            "encoding": "UTF-8",
            "format": "Comma-separated values",
            "headers": "First row must contain column headers"
        }
    }


@router.post("/batch-process",
             summary="Batch Process Multiple Data Files",
             description="Process multiple data files (CSV/Excel) in a single request")
async def batch_process_data_files(
    files: List[UploadFile] = File(..., description="List of data files to process (CSV, XLS, XLSX)"),
    save_to_database: bool = Query(True, description="Save generated CodeSystems to database")
):
    """
    Process multiple data files in batch operation.
    
    Use Cases:
    - Import multiple traditional medicine systems at once
    - Bulk data migration
    - Batch updates to existing CodeSystems
    
    Returns:
    - Summary of all processing results
    - Individual file processing status
    - Aggregate statistics
    """
    
    results = []
    total_concepts = 0
    total_errors = 0
    total_warnings = 0
    
    for file in files:
        if not file.filename.endswith('.csv'):
            results.append({
                "filename": file.filename,
                "success": False,
                "error": "File must be a CSV file"
            })
            continue
        
        try:
            content = await file.read()
            csv_content = content.decode('utf-8')
            
            result = data_processor.process_csv_to_codesystem(csv_content)
            
            if result.success and save_to_database and result.code_system:
                db = await get_database()
                code_system_dict = result.code_system.model_dump()
                
                # Clean the data to ensure text index compatibility
                def clean_for_text_index(obj):
                    """Recursively clean object to ensure MongoDB text index compatibility"""
                    if isinstance(obj, dict):
                        cleaned = {}
                        for key, value in obj.items():
                            if key == "language" and value is not None:
                                # Ensure language fields are strings for text indexing
                                cleaned[key] = str(value) if value is not None else None
                            else:
                                cleaned[key] = clean_for_text_index(value)
                        return cleaned
                    elif isinstance(obj, list):
                        return [clean_for_text_index(item) for item in obj]
                    else:
                        return obj
                
                code_system_dict = clean_for_text_index(code_system_dict)
                
                # Check if document already exists
                existing_doc = await db.codesystems.find_one(
                    {"url": result.code_system.url, "version": result.code_system.version}
                )
                
                if existing_doc:
                    # Update existing document (remove _id to avoid immutable field error)
                    code_system_dict.pop("_id", None)
                    await db.codesystems.update_one(
                        {"url": result.code_system.url, "version": result.code_system.version},
                        {"$set": code_system_dict}
                    )
                else:
                    # Insert new document with _id
                    code_system_dict["_id"] = result.code_system.id
                    await db.codesystems.insert_one(code_system_dict)
            
            results.append({
                "filename": file.filename,
                "success": result.success,
                "code_system_id": result.code_system.id if result.code_system else None,
                "concepts_processed": result.concepts_processed,
                "errors": result.errors,
                "warnings": result.warnings
            })
            
            total_concepts += result.concepts_processed
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    successful_files = [r for r in results if r["success"]]
    
    return {
        "batch_summary": {
            "total_files": len(files),
            "successful_files": len(successful_files),
            "failed_files": len(files) - len(successful_files),
            "total_concepts_processed": total_concepts,
            "total_errors": total_errors,
            "total_warnings": total_warnings
        },
        "file_results": results,
        "saved_to_database": save_to_database
    }


@router.get("/template/{system}",
            summary="Download Data File Template",
            description="Download a data file template (CSV) for a specific traditional medicine system")
async def download_data_template(
    system: TraditionalMedicineSystem = Path(..., description="Traditional medicine system")
):
    """
    Download a data file template with proper headers for a traditional medicine system.
    
    Templates Include:
    - Correct column headers
    - Sample data rows
    - Format guidelines
    - System-specific requirements
    
    Output Format: CSV (can be opened in Excel)
    """
    
    # Create template based on system
    templates = {
        TraditionalMedicineSystem.AYURVEDA: [
            ["Sr No.", "NAMC_ID", "NAMC_CODE", "NAMC_term", "NAMC_term_diacritical", "NAMC_term_DEVANAGARI", "Short_definition", "Long_definition"],
            ["1", "1", "AYU-001", "Sample Term", "sample-term", "नमूना शब्द", "Short definition", "Detailed long definition"],
            ["2", "2", "AYU-002", "Another Term", "another-term", "अन्य शब्द", "Another definition", "Another detailed definition"]
        ],
        TraditionalMedicineSystem.UNANI: [
            ["Sr No.", "NUMC_ID", "NUMC_CODE", "Arabic_term", "NUMC_TERM"],
            ["1", "1", "UNA-001", "العربية", "Sample Unani Term"],
            ["2", "2", "UNA-002", "مصطلح", "Another Unani Term"]
        ],
        TraditionalMedicineSystem.SIDDHA: [
            ["Sr No.", "NAMC_ID", "NAMC_CODE", "NAMC_TERM", "Tamil_term", "Short_definition"],
            ["1", "1", "SID-001", "Sample Siddha Term", "தமிழ் சொல்", "Sample definition"],
            ["2", "2", "SID-002", "Another Siddha Term", "வேறு சொல்", "Another definition"]
        ]
    }
    
    template_data = templates.get(system, [])
    
    # Create CSV content
    output = io.StringIO()
    import csv
    writer = csv.writer(output)
    writer.writerows(template_data)
    
    filename = f"namaste_{system.value}_template.csv"
    
    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
