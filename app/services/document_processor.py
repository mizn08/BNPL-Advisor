"""
Document and File Processing Service
Handles file uploads, parsing, and data extraction
"""
import io
import csv
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process uploaded financial documents"""
    
    # Supported MIME types
    SUPPORTED_TYPES = {
        "text/csv": ".csv",
        "application/json": ".json",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
    }
    
    @staticmethod
    def process_csv(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Process CSV file containing financial transactions
        
        Expected CSV columns:
        - date/transaction_date
        - type/transaction_type (sale, purchase, payment, receipt)
        - amount
        - description
        - category (optional)
        """
        try:
            # Read CSV from bytes
            text_content = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(text_content))
            
            # Normalize column names to lowercase
            df.columns = [col.lower().strip() for col in df.columns]
            
            # Map common column name variations
            column_mapping = {
                'transaction_date': ['date', 'transaction_date', 'date_of_transaction'],
                'transaction_type': ['type', 'transaction_type', 'tx_type'],
                'amount': ['amount', 'value', 'total'],
                'description': ['description', 'desc', 'remarks'],
                'category': ['category', 'cat', 'classification'],
            }
            
            # Rename columns based on mapping
            for standard_name, alternatives in column_mapping.items():
                for alt_name in alternatives:
                    if alt_name in df.columns:
                        df = df.rename(columns={alt_name: standard_name})
                        break
            
            # Ensure required columns exist
            required_cols = ['transaction_date', 'transaction_type', 'amount']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            # Convert to list of dicts
            transactions = []
            for idx, row in df.iterrows():
                try:
                    transaction = {
                        "transaction_date": str(row['transaction_date']),
                        "transaction_type": str(row['transaction_type']).lower(),
                        "amount": float(row['amount']),
                        "description": str(row.get('description', '')),
                        "category": str(row.get('category', 'other')),
                    }
                    transactions.append(transaction)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid row {idx}: {str(e)}")
                    continue
            
            logger.info(f"Processed {len(transactions)} transactions from CSV")
            return transactions
            
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
            raise
    
    @staticmethod
    def process_json(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Process JSON file containing financial data
        
        Expected format:
        {
            "transactions": [
                {
                    "date": "2024-04-25",
                    "type": "sale",
                    "amount": 5000,
                    "description": "Product sales",
                    "category": "revenue"
                }
            ]
        }
        or direct array:
        [
            { "date": ..., "type": ..., "amount": ... }
        ]
        """
        try:
            data = json.loads(file_content.decode('utf-8'))
            
            # Handle different JSON structures
            if isinstance(data, dict):
                transactions = data.get('transactions', [])
            elif isinstance(data, list):
                transactions = data
            else:
                raise ValueError("JSON must be object with 'transactions' key or array")
            
            # Normalize transaction structure
            normalized = []
            for tx in transactions:
                normalized_tx = {
                    "transaction_date": str(tx.get('date') or tx.get('transaction_date', '')),
                    "transaction_type": str(tx.get('type') or tx.get('transaction_type', '')).lower(),
                    "amount": float(tx.get('amount', 0)),
                    "description": str(tx.get('description', '')),
                    "category": str(tx.get('category', 'other')),
                }
                normalized.append(normalized_tx)
            
            logger.info(f"Processed {len(normalized)} transactions from JSON")
            return normalized
            
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}")
            raise
    
    @staticmethod
    def process_pdf(file_content: bytes) -> Dict[str, Any]:
        """
        Extract text and data from PDF invoice
        
        Uses pattern matching to extract:
        - Invoice number
        - Date
        - Vendor/supplier
        - Total amount
        - Line items
        """
        try:
            # For basic text extraction, try using PyPDF2 if available
            # For now, we'll implement a text-based version
            
            extracted_data = {
                "invoice_number": None,
                "date": None,
                "vendor": None,
                "total_amount": None,
                "line_items": [],
                "raw_text": "",
                "confidence": 0.0,
            }
            
            # Attempt PDF text extraction
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                extracted_data["raw_text"] = text
            except ImportError:
                logger.warning("PyPDF2 not installed, using basic text extraction")
                try:
                    # Fallback: try to extract as text
                    extracted_data["raw_text"] = file_content.decode('utf-8', errors='ignore')
                except:
                    logger.error("Could not extract PDF text")
                    return extracted_data
            
            # Parse extracted text
            text = extracted_data["raw_text"].lower()
            lines = text.split('\n')
            
            # Extract invoice number
            for line in lines:
                if 'invoice' in line and any(char.isdigit() for char in line):
                    match = re.search(r'invoice\s*[:#]*\s*(\w+[-\d]*)', line)
                    if match:
                        extracted_data["invoice_number"] = match.group(1)
                        break
            
            # Extract date
            for line in lines:
                if any(date_keyword in line for date_keyword in ['date', 'issued', 'invoice date']):
                    # Look for date patterns
                    date_patterns = [
                        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                    ]
                    for pattern in date_patterns:
                        match = re.search(pattern, line)
                        if match:
                            extracted_data["date"] = match.group(1)
                            break
                if extracted_data["date"]:
                    break
            
            # Extract total amount
            for line in lines:
                if 'total' in line:
                    match = re.search(r'[\$₹₽¥€₩]?\s*(\d+[,.]?\d*)', line)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        try:
                            extracted_data["total_amount"] = float(amount_str)
                            break
                        except ValueError:
                            continue
            
            # Calculate confidence
            fields_found = sum(1 for v in [
                extracted_data["invoice_number"],
                extracted_data["date"],
                extracted_data["total_amount"],
            ] if v is not None)
            extracted_data["confidence"] = fields_found / 3.0
            
            logger.info(f"Extracted PDF data with {fields_found}/3 confidence")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    @staticmethod
    def validate_file(
        filename: str,
        file_content: bytes,
        max_size_mb: int = 10,
    ) -> Tuple[bool, str]:
        """
        Validate uploaded file
        
        Args:
            filename: Name of the file
            file_content: File content as bytes
            max_size_mb: Maximum file size in MB
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, f"File too large: {file_size_mb:.1f}MB (max: {max_size_mb}MB)"
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        valid_extensions = ['.csv', '.json', '.pdf', '.txt']
        if file_ext not in valid_extensions:
            return False, f"Unsupported file type: {file_ext}. Supported: {valid_extensions}"
        
        # Check file is not empty
        if len(file_content) == 0:
            return False, "File is empty"
        
        return True, ""
    
    @staticmethod
    def process_file(
        filename: str,
        file_content: bytes,
    ) -> Dict[str, Any]:
        """
        Main file processing method
        
        Determines file type and calls appropriate processor
        
        Args:
            filename: Name of the file
            file_content: File content as bytes
            
        Returns:
            Processed data
        """
        
        # Validate file
        is_valid, error = DocumentProcessor.validate_file(filename, file_content)
        if not is_valid:
            raise ValueError(error)
        
        file_ext = Path(filename).suffix.lower()
        
        try:
            if file_ext == '.csv':
                transactions = DocumentProcessor.process_csv(file_content)
                return {
                    "type": "transactions",
                    "data": transactions,
                    "count": len(transactions),
                    "filename": filename,
                }
            
            elif file_ext == '.json':
                transactions = DocumentProcessor.process_json(file_content)
                return {
                    "type": "transactions",
                    "data": transactions,
                    "count": len(transactions),
                    "filename": filename,
                }
            
            elif file_ext == '.pdf':
                invoice_data = DocumentProcessor.process_pdf(file_content)
                return {
                    "type": "invoice",
                    "data": invoice_data,
                    "filename": filename,
                    "confidence": invoice_data.get("confidence", 0),
                }
            
            elif file_ext == '.txt':
                # Try to parse as CSV first
                try:
                    transactions = DocumentProcessor.process_csv(file_content)
                    return {
                        "type": "transactions",
                        "data": transactions,
                        "count": len(transactions),
                        "filename": filename,
                    }
                except:
                    # Fallback to plain text extraction
                    text = file_content.decode('utf-8', errors='ignore')
                    return {
                        "type": "text",
                        "data": text,
                        "filename": filename,
                    }
            
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
        
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise
