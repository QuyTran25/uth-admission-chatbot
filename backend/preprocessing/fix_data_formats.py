# -*- coding: utf-8 -*-
"""
fix_data_formats.py
Tự động dọn dẹp URL bị lồng nhau và điền mã ngành còn thiếu trong các file chunks JSON.
URL được lấy động từ các file LINK*.docx tương ứng của từng thư mục hệ đào tạo.
"""
import os
import re
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from utils import logger, load_json, save_json, FOLDER_MAPPING
from chunking import classify_code, load_whitelist

# Đảo ngược mapping để lấy tên thư mục tiếng Việt từ program_type
REV_FOLDER_MAPPING = {v: k for k, v in FOLDER_MAPPING.items()}
CHUNKS_DIR = Path(r"d:\uth-admission-chatbot\backend\data\processed\chunks")
RAW_DIR = Path(r"d:\uth-admission-chatbot\backend\data\raw")
SOURCE_URLS_PATH = Path(r"d:\uth-admission-chatbot\backend\data\source_urls.json")

def get_docx_urls(docx_path: Path) -> list:
    """Đọc text và trích xuất tất cả URLs có trong file docx."""
    urls = []
    text_content = []
    try:
        with zipfile.ZipFile(docx_path) as z:
            # Đọc text từ document.xml
            doc_xml = z.read("word/document.xml")
            root = ET.fromstring(doc_xml)
            for elem in root.iter():
                if elem.tag.endswith('t'):
                    if elem.text:
                        text_content.append(elem.text)
            
            # Đọc các relationships (link liên kết đính kèm)
            try:
                rels_xml = z.read("word/_rels/document.xml.rels")
                rels_root = ET.fromstring(rels_xml)
                for rel in rels_root:
                    target = rel.attrib.get('Target', '')
                    if target.startswith('http://') or target.startswith('https://'):
                        urls.append(target)
            except KeyError:
                pass
    except Exception as e:
        logger.error(f"Lỗi khi đọc file docx {docx_path}: {e}")
    
    # Dùng regex quét thêm URL từ text
    full_text = " ".join(text_content)
    urls_in_text = re.findall(r'https?://[^\s()<>]+', full_text)
    urls.extend(urls_in_text)
    
    return sorted(list(set(urls)))

def clean_url(url: str) -> str:
    """Làm sạch URL lồng nhau (loại bỏ đoạn tabs lỗi)."""
    if "https-tuyensinh-ut-edu-vn" in url:
        # Thay thế đoạn lồng nhau thành URL chuẩn
        url = url.replace("https-tuyensinh-ut-edu-vn-dt-tabs-1/", "")
    return url

def partition_urls(program_type: str, urls: list) -> tuple:
    """Phân chia URLs thành source_urls và extra_urls theo logic chuẩn."""
    source_urls = []
    extra_urls = []
    for u in urls:
        u_clean = clean_url(u)
        if program_type == "dai_hoc_chinh_quy":
            if "tuyensinh.ut.edu.vn" in u_clean:
                source_urls.append(u_clean)
            else:
                extra_urls.append(u_clean)
        elif program_type == "sau_dai_hoc":
            if u_clean.strip("/") == "https://sdh.ut.edu.vn":
                source_urls.append(u_clean)
            else:
                extra_urls.append(u_clean)
        else:
            source_urls.append(u_clean)
    return source_urls, extra_urls

def process_all_files():
    whitelist = load_whitelist()
    json_files = sorted(CHUNKS_DIR.glob("*_chunks.json"))
    
    # Để cập nhật lại source_urls.json đồng bộ
    source_urls_updated = {}
    
    logger.info(f"Tìm thấy {len(json_files)} file JSON trong thư mục chunks.")
    
    for jf in json_files:
        doc = load_json(str(jf))
        if not doc:
            continue
            
        source_meta = doc.get("source_file") or doc.get("file_metadata") or {}
        program_type = source_meta.get("program_type")
        if not program_type:
            # Fallback nếu không có metadata
            chunks = doc.get("chunks", [])
            if chunks:
                program_type = chunks[0].get("program_type")
        
        if not program_type:
            logger.warning(f"Không nhận diện được program_type của file {jf.name}. Bỏ qua.")
            continue
            
        # Tìm thư mục raw tiếng Việt tương ứng
        folder_vn = REV_FOLDER_MAPPING.get(program_type)
        raw_folder_path = RAW_DIR / folder_vn if folder_vn else None
        
        extracted_urls = []
        if raw_folder_path and raw_folder_path.exists():
            # Tìm file LINK*.docx
            link_files = list(raw_folder_path.glob("LINK*.docx"))
            if link_files:
                link_file = link_files[0]
                extracted_urls = get_docx_urls(link_file)
                logger.info(f"Đọc URLs từ {link_file.name} cho {jf.name}: {extracted_urls}")
            else:
                logger.warning(f"Không thấy file LINK*.docx trong {raw_folder_path}")
        else:
            logger.warning(f"Không tìm thấy thư mục raw: {raw_folder_path}")
            
        # Phân chia và làm sạch URLs
        source_urls, extra_urls = partition_urls(program_type, extracted_urls)
        
        # Cập nhật source_urls_updated để ghi vào source_urls.json sau
        if program_type not in source_urls_updated:
            source_urls_updated[program_type] = {
                "source_urls": source_urls,
                "extra_urls": extra_urls
            }
            
        chunks = doc.get("chunks", [])
        modified_chunks = 0
        modified_urls = 0
        
        # Xác định các URL cũ để thay thế trong text
        # (Ở đây URL lỗi là các URL gốc có chứa 'https-tuyensinh-ut-edu-vn')
        url_replacements = {}
        for u in extracted_urls:
            u_clean = clean_url(u)
            if u != u_clean:
                url_replacements[u] = u_clean
        
        for c in chunks:
            ri = c.get("row_identifiers") or {}
            code_info = c.get("code_info")
            ma_nganh = ri.get("ma_nganh") or ri.get("ma_xtuyen")
            
            chunk_changed = False
            
            # 1) Sửa URL lồng trong source_urls và extra_urls
            if extracted_urls:
                c["source_urls"] = source_urls
                c["extra_urls"] = extra_urls
                chunk_changed = True
                
            # 2) Sửa URL lồng trong trường text của chunk
            text = c.get("text") or ""
            text_original = text
            for old_url, new_url in url_replacements.items():
                if old_url in text:
                    text = text.replace(old_url, new_url)
            
            # Thêm trường hợp nếu URL lồng đã được lưu trong text nhưng không khớp chính xác
            # (Ví dụ: do ký tự phân tách hoặc khoảng trắng)
            for old_url, new_url in url_replacements.items():
                # Thử tìm phần lỗi và thay thế
                old_part = "https-tuyensinh-ut-edu-vn-dt-tabs-1/"
                if old_part in text:
                    text = text.replace(old_part, "")
            
            if text != text_original:
                c["text"] = text
                chunk_changed = True
                modified_urls += 1
            
            # 3) Bổ sung code_info nếu null nhưng có mã ngành
            if code_info in (None, {}):
                # Quét xem có mã tuyển sinh không
                has_code = False
                if ma_nganh:
                    has_code = True
                else:
                    # Quét trong row_identifiers
                    for val in ri.values():
                        if re.search(r"\d{6,}[A-Za-z]?[AHDEL]?", str(val)):
                            ma_nganh = val
                            has_code = True
                            break
                
                if has_code:
                    new_code_info = classify_code(ma_nganh, whitelist)
                    c["code_info"] = new_code_info
                    
                    # Cập nhật needs_review tương ứng
                    issues = c.get("needs_review") or []
                    if new_code_info.get("code_needs_verification"):
                        msg = f"mã cần xác minh: {new_code_info['code_raw']} -> {new_code_info['code_corrected']}"
                        if msg not in issues:
                            issues.append(msg)
                    if new_code_info.get("code_raw") != new_code_info.get("code_corrected"):
                        msg = f"mã OCR bị sửa: {new_code_info['code_raw']}"
                        if msg not in issues:
                            issues.append(msg)
                    c["needs_review"] = issues
                    chunk_changed = True
                    modified_chunks += 1
                    
        if modified_chunks > 0 or modified_urls > 0:
            save_json(doc, str(jf))
            logger.info(f"Đã cập nhật {jf.name}: điền {modified_chunks} code_info, sửa {modified_urls} URL text.")
            
    # Ghi đè cập nhật lại source_urls.json
    if source_urls_updated:
        # Giữ lại các mục không thay đổi từ file cũ nếu có
        old_urls = load_json(str(SOURCE_URLS_PATH)) or {}
        for k, v in source_urls_updated.items():
            old_urls[k] = v
        save_json(old_urls, str(SOURCE_URLS_PATH))
        logger.info("Đã cập nhật file source_urls.json")

if __name__ == "__main__":
    process_all_files()
