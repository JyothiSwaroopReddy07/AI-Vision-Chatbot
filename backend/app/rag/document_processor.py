"""Document processing for RAG pipeline"""

import os
import io
import re
from typing import List, Optional, Tuple
from pathlib import Path
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
import docx
from PIL import Image
import pytesseract

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.core.config import settings


class DocumentProcessor:
    """Processes various document types for RAG pipeline"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def process_file(
        self,
        file_path: str,
        metadata: Optional[dict] = None
    ) -> List[Document]:
        """
        Process a file and extract text
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata to attach to documents
            
        Returns:
            List of Document objects
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_extension == '.txt':
            text = self.extract_text_from_txt(file_path)
        elif file_extension in ['.doc', '.docx']:
            text = self.extract_text_from_docx(file_path)
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            text = self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Create documents with metadata
        base_metadata = metadata or {}
        base_metadata.update({
            "source": file_path,
            "file_type": file_extension
        })
        
        # Split text into chunks
        documents = self.text_splitter.create_documents(
            texts=[text],
            metadatas=[base_metadata]
        )
        
        return documents
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF using multiple methods with fallbacks
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text
        """
        text = ""
        
        # Method 1: PyMuPDF (fitz) - Best for most PDFs
        try:
            text = self._extract_with_pymupdf(file_path)
            if self._is_text_quality_good(text):
                print(f"✅ PyMuPDF extraction successful: {len(text)} chars")
                return text
        except Exception as e:
            print(f"⚠️ PyMuPDF extraction failed: {e}")
        
        # Method 2: pdfplumber - Good for complex layouts
        try:
            text = self._extract_with_pdfplumber(file_path)
            if self._is_text_quality_good(text):
                print(f"✅ pdfplumber extraction successful: {len(text)} chars")
                return text
        except Exception as e:
            print(f"⚠️ pdfplumber extraction failed: {e}")
        
        # Method 3: PyPDF2 - Fallback
        try:
            text = self._extract_with_pypdf2(file_path)
            if self._is_text_quality_good(text):
                print(f"✅ PyPDF2 extraction successful: {len(text)} chars")
                return text
        except Exception as e:
            print(f"⚠️ PyPDF2 extraction failed: {e}")
        
        # Method 4: OCR fallback for scanned PDFs
        try:
            text = self._extract_with_ocr(file_path)
            if self._is_text_quality_good(text):
                print(f"✅ OCR extraction successful: {len(text)} chars")
                return text
        except Exception as e:
            print(f"⚠️ OCR extraction failed: {e}")
        
        print(f"❌ All PDF extraction methods failed for {file_path}")
        return text or "No text could be extracted from PDF"
    
    def _extract_with_pymupdf(self, file_path: str) -> str:
        """Extract text using PyMuPDF (fitz) - fastest and most reliable"""
        doc = fitz.open(file_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            if page_text.strip():
                text += page_text + "\n"
        
        doc.close()
        return text.strip()
    
    def _extract_with_pdfplumber(self, file_path: str) -> str:
        """Extract text using pdfplumber - good for complex layouts"""
        text = ""
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += page_text + "\n"
        
        return text.strip()
    
    def _extract_with_pypdf2(self, file_path: str) -> str:
        """Extract text using PyPDF2 - original method"""
        text = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip()
    
    def _extract_with_ocr(self, file_path: str) -> str:
        """Extract text using OCR for scanned PDFs"""
        try:
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300)
            text = ""
            
            for image in images:
                # Extract text using OCR
                page_text = pytesseract.image_to_string(image, lang='eng')
                if page_text.strip():
                    text += page_text + "\n"
            
            return text.strip()
        except ImportError:
            print("pdf2image not available for OCR")
            return ""
    
    def _is_text_quality_good(self, text: str) -> bool:
        """
        Validate if extracted text is of good quality
        
        Args:
            text: Extracted text
            
        Returns:
            True if text quality is good
        """
        if not text or len(text.strip()) < 50:
            return False
        
        # Check for common PDF extraction issues
        issues = [
            len(re.findall(r'[^\x00-\x7F]', text)) > len(text) * 0.3,  # Too many non-ASCII chars
            len(re.findall(r'\s{10,}', text)) > 5,  # Too many consecutive spaces
            len(re.findall(r'[A-Z]{20,}', text)) > 3,  # Too many consecutive caps
            text.count('\n') > len(text) * 0.1,  # Too many newlines
        ]
        
        return not any(issues)
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from TXT file
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            File content
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from DOCX file
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted text
        """
        doc = docx.Document(file_path)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    
    def extract_text_from_image(self, file_path: str) -> str:
        """
        Extract text from image using OCR
        
        Args:
            file_path: Path to image file
            
        Returns:
            Extracted text
        """
        try:
            # Configure Tesseract path if specified
            if settings.TESSERACT_PATH:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
            
            # Open and process image
            image = Image.open(file_path)
            text = pytesseract.image_to_string(
                image,
                lang=settings.TESSERACT_LANG
            )
            
            return text.strip()
        except Exception as e:
            raise Exception(f"OCR failed: {e}")
    
    def split_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        Split text into chunks
        
        Args:
            text: Text to split
            metadata: Optional metadata
            
        Returns:
            List of Document objects
        """
        documents = self.text_splitter.create_documents(
            texts=[text],
            metadatas=[metadata or {}]
        )
        return documents
    
    def process_pubmed_article(
        self,
        pmid: str,
        title: str,
        abstract: str,
        full_text: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> List[Document]:
        """
        Process PubMed article into documents
        
        Args:
            pmid: PubMed ID
            title: Article title
            abstract: Article abstract
            full_text: Optional full text
            metadata: Optional additional metadata
            
        Returns:
            List of Document objects
        """
        # Combine title and abstract
        text = f"{title}\n\n{abstract}"
        if full_text:
            text += f"\n\n{full_text}"
        
        # Prepare metadata
        doc_metadata = metadata or {}
        doc_metadata.update({
            "source": "pubmed",
            "pmid": pmid,
            "title": title
        })
        
        # Split into chunks
        documents = self.text_splitter.create_documents(
            texts=[text],
            metadatas=[doc_metadata]
        )
        
        return documents


# Global document processor instance
document_processor = DocumentProcessor()

