"""
QR/Barcode Decoder Module for Sprint 8
Pure Python solution using pyzbar for reliable decoding on mobile.
"""

import base64
from typing import Optional, Dict
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

# Try importing pyzbar, but provide a graceful fallback
try:
    from pyzbar.pyzbar import decode, ZBarSymbol
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar not installed. Install it with: pip install pyzbar python-zbar")


class BarcodeDecoder:
    """Handles QR and Barcode decoding."""
    
    @staticmethod
    def decode_from_base64(base64_image: str) -> Optional[Dict]:
        """
        Decode QR/Barcode from base64 image.
        Returns: {'type': 'qr'|'ean'|'upca'|..., 'data': '...', 'raw': '...'}
        or None if no barcode found.
        """
        if not PYZBAR_AVAILABLE:
            logger.error("pyzbar not available. Cannot decode barcodes.")
            return None
        
        try:
            # Decode base64
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
            
            # Attempt decode
            results = decode(image)
            
            if not results:
                logger.info("No barcode found in image")
                return None
            
            # Return first match
            barcode = results[0]
            barcode_type = barcode.type
            barcode_data = barcode.data.decode('utf-8')
            
            logger.info(f"Barcode detected: type={barcode_type}, data={barcode_data}")
            
            return {
                'type': barcode_type,
                'data': barcode_data,
                'raw': barcode_data,
                'confidence': 'high'  # pyzbar is deterministic
            }
        except Exception as e:
            logger.error(f"Barcode decoding failed: {e}")
            return None


async def decode_barcode_async(base64_image: str) -> Optional[Dict]:
    """Async wrapper for barcode decoding."""
    import asyncio
    return await asyncio.to_thread(BarcodeDecoder.decode_from_base64, base64_image)
