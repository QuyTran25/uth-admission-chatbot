import os
import time
import argparse
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, OcrEngine, OcrMode
from utils import logger, get_raw_files, save_json, load_json

def setup_converter(ocr_engine: str = "easyocr", force_ocr: bool = False) -> DocumentConverter:
    """
    Initializes the Docling DocumentConverter with layout, table parsing options, and selected OCR engine.
    Enables OCR and high-accuracy table structure extraction.
    """
    logger.info(f"Initializing Docling DocumentConverter (ocr_engine={ocr_engine}, force_ocr={force_ocr})...")
    pipeline_options = PdfPipelineOptions()
    
    # Configure pipeline options
    pipeline_options.do_ocr = True  # Enable OCR for scanned/image PDFs
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # High accuracy table structure
    
    # Configure OCR Engine & Vietnamese language
    if ocr_engine == "easyocr":
        from docling.datamodel.pipeline_options import EasyOcrOptions
        ocr_options = EasyOcrOptions()
        ocr_options.lang = ["vi"]
    elif ocr_engine == "tesseract":
        from docling.datamodel.pipeline_options import TesseractOcrOptions
        ocr_options = TesseractOcrOptions()
        ocr_options.lang = ["vie"]
    else:
        logger.warning(f"Unknown OCR engine '{ocr_engine}'. Using default.")
        from docling.datamodel.pipeline_options import OcrAutoOptions
        ocr_options = OcrAutoOptions()
        
    if force_ocr:
        ocr_options.mode = OcrMode.FULL_PAGE
        
    pipeline_options.ocr_options = ocr_options
    
    # Instantiate the converter
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    logger.info("Converter successfully initialized.")
    return converter

def parse_all_documents(
    raw_dir: str = "backend/data/raw", 
    output_dir: str = "backend/data/processed/docling",
    ocr_engine: str = "easyocr",
    single_stem: str = None
):
    """
    Scans the raw data folder and parses all documents using Docling.
    Saves the structured output for each file to output_dir.
    """
    start_time = time.time()
    raw_files = get_raw_files(raw_dir)
    
    # Filter files if in single-file mode
    if single_stem:
        raw_files = [
            f for f in raw_files 
            if (single_stem in f["file_stem"] or single_stem in f"{f['program_type']}_{f['file_stem']}")
        ]
        logger.info(f"Single-file mode: targeting '{single_stem}', found {len(raw_files)} file(s).")
    else:
        logger.info(f"Found {len(raw_files)} raw files to parse.")
        
    if not raw_files:
        logger.warning("No files found to parse.")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Setup two converters to avoid re-initializing
    converter_normal = setup_converter(ocr_engine=ocr_engine, force_ocr=False)
    converter_force_ocr = setup_converter(ocr_engine=ocr_engine, force_ocr=True)
    
    parsed_count = 0
    skipped_count = 0

    for file_info in raw_files:
        file_path = file_info["file_path"]
        file_name = file_info["file_name"]
        file_stem = file_info["file_stem"]
        
        # Save path for the parsed document
        dest_json_path = output_path / f"{file_info['program_type']}_{file_stem}_docling.json"
        
        # Skip if already parsed to optimize re-runs
        if dest_json_path.exists():
            logger.info(f"Skipping {file_name} - already parsed at {dest_json_path.name}")
            skipped_count += 1
            continue
            
        logger.info(f"Parsing file: {file_name} ({file_info['program_type']}) at {file_path}")
        
        # Force OCR for all "dai_hoc_chinh_quy" documents due to corrupt/missing text layers,
        # or other documents explicitly needing force OCR.
        use_force_ocr = file_info["program_type"] == "dai_hoc_chinh_quy" or any(p in file_name for p in ["2024_diem-chuan", "2025_diem-chuan"])
        converter = converter_force_ocr if use_force_ocr else converter_normal
        
        try:
            parse_start = time.time()
            
            # Run Docling conversion
            result = converter.convert(file_path)
            doc = result.document
            
            # Export document content as a dictionary
            doc_dict = doc.export_to_dict()
            
            # Create a structured record wrapping document data and custom file metadata
            output_data = {
                "file_metadata": {
                    "file_name": file_name,
                    "file_stem": file_stem,
                    "extension": file_info["extension"],
                    "program_type": file_info["program_type"],
                    "admission_year": file_info["admission_year"]
                },
                "docling_output": doc_dict
            }
            
            # Save to processed directory
            save_json(output_data, str(dest_json_path))
            logger.info(f"Successfully parsed {file_name} in {time.time() - parse_start:.2f}s")
            parsed_count += 1
            
        except Exception as e:
            logger.error(f"Error parsing file {file_name}: {e}", exc_info=True)

    total_time = time.time() - start_time
    logger.info(f"Completed parsing run. Parsed: {parsed_count}, Skipped: {skipped_count}, Total time: {total_time:.2f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser Step 1: Layout Analysis & Reading Order Recovery with OCR")
    parser.main_group = parser.add_argument_group("Main Options")
    parser.main_group.add_argument("--ocr-engine", type=str, default="easyocr", choices=["easyocr", "tesseract"], help="OCR engine to use (default: easyocr)")
    parser.main_group.add_argument("--single", type=str, default=None, help="Parse a single file by its file stem name")
    parser.main_group.add_argument("--raw-dir", type=str, default="backend/data/raw", help="Path to raw files directory")
    parser.main_group.add_argument("--output-dir", type=str, default="backend/data/processed/docling", help="Path to output processed files directory")
    
    args = parser.parse_args()
    parse_all_documents(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        ocr_engine=args.ocr_engine,
        single_stem=args.single
    )
