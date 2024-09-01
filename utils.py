# utils.py

import os
import requests
from datetime import datetime
from urllib.parse import quote
import streamlit as st

def format_date(date_str):
    """Convert date from ISO 8601 format to dd/mm/yyyy."""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%d/%m/%Y')
    except ValueError:
        return 'Không có dữ liệu'

def download_pdfs(file_urls, download_dir="PDF_Documents"):
    """Download PDF files from a list of URLs into the specified directory, removing old files first."""
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    for file_name in os.listdir(download_dir):
        file_path = os.path.join(download_dir, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith('.pdf'):
            os.remove(file_path)
    
    for i, url in enumerate(file_urls):
        try:
            response = requests.get(url)
            response.raise_for_status()
            file_path = os.path.join(download_dir, f"document_{i+1}.pdf")
            with open(file_path, "wb") as file:
                file.write(response.content)
        except requests.exceptions.RequestException as e:
            st.error(f"Không thể tải tệp từ URL: {url}. Lỗi: {e}")

def file_url(path, type="view"):
    """Return a URL for a file."""
    base_url = os.getenv('BASE_URL')  # Assume BASE_URL is defined in .env
    return f"{base_url}/{path}?type={type}"
