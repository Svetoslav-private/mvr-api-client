#!/usr/bin/env python3
"""
MVR Document Query Client
Programmatic access to Bulgarian Ministry of Internal Affairs document query service
"""

import re
import time
from io import BytesIO
from typing import Dict, Optional
from urllib.parse import urlencode, quote

import requests
from bs4 import BeautifulSoup
from PIL import Image

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


class MVRClient:
    """Client for querying MVR document status"""

    BASE_URL = "https://www.mvr.bg"
    SERVICE_PATH = "/електронизирани-услуги/справка-за-издадени-и-неполучени-български-лични-документи"

    def __init__(self, use_ocr: bool = True, max_retries: int = 5):
        """
        Initialize MVR client

        Args:
            use_ocr: Whether to use OCR for automatic CAPTCHA solving
            max_retries: Maximum number of CAPTCHA solving retries (default 5)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'bg,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',  # Exclude br/zstd - requests doesn't support them natively
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        })

        self.use_ocr = use_ocr
        self.max_retries = max_retries
        self.ocr = None
        self.easyocr_reader = None

        if self.use_ocr:
            if DDDDOCR_AVAILABLE:
                print("Initializing ddddocr CAPTCHA solver...")
                self.ocr = ddddocr.DdddOcr(show_ad=False)
            elif EASYOCR_AVAILABLE:
                print("Initializing EasyOCR reader (fallback)...")
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            else:
                print("Warning: No OCR library available. Install ddddocr or easyocr.")
                self.use_ocr = False

    def get_form_page(self) -> BeautifulSoup:
        """
        Fetch the initial form page

        Returns:
            BeautifulSoup object of the page
        """
        url = f"{self.BASE_URL}{self.SERVICE_PATH}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')

    def extract_captcha_image(self, soup: BeautifulSoup) -> Optional[Image.Image]:
        """
        Extract CAPTCHA image from the form page (handles both URL and base64)

        Args:
            soup: BeautifulSoup object of the form page

        Returns:
            PIL Image object or None
        """
        # Look for CAPTCHA image by class first (most reliable)
        captcha_img = soup.find('img', {'class': re.compile(r'captcha', re.I)})
        if not captcha_img:
            captcha_img = soup.find('img', {'alt': re.compile(r'captcha|защитен код', re.I)})
        if not captcha_img:
            captcha_img = soup.find('img', {'id': re.compile(r'captcha', re.I)})

        if captcha_img and captcha_img.get('src'):
            src = captcha_img['src']

            # Handle base64 inline image
            if src.startswith('data:image'):
                import base64
                # Extract base64 data after the comma
                base64_data = src.split(',', 1)[1]
                image_data = base64.b64decode(base64_data)
                return Image.open(BytesIO(image_data))

            # Handle URL
            if src.startswith('/'):
                url = f"{self.BASE_URL}{src}"
            elif src.startswith('http'):
                url = src
            else:
                url = f"{self.BASE_URL}/{src}"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))

        return None

    def download_captcha_image(self, image_url: str) -> Image.Image:
        """
        Download CAPTCHA image

        Args:
            image_url: URL of the CAPTCHA image

        Returns:
            PIL Image object
        """
        response = self.session.get(image_url, timeout=30)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))

    def _preprocess_captcha(self, image: Image.Image) -> Image.Image:
        """Preprocess CAPTCHA image for better OCR accuracy"""
        import numpy as np
        try:
            import cv2
        except ImportError:
            return image  # Return original if cv2 not available

        # Convert to RGB if needed
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        # Convert to numpy array
        img_array = np.array(image)

        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Apply threshold to get cleaner binary image
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        return Image.fromarray(binary)

    def solve_captcha_ocr(self, image: Image.Image) -> str:
        """
        Solve CAPTCHA using OCR (ddddocr preferred, easyocr fallback)

        Args:
            image: PIL Image of the CAPTCHA

        Returns:
            Solved CAPTCHA text
        """
        # Try ddddocr first (better for CAPTCHAs)
        if self.ocr:
            # Preprocess for better accuracy
            processed = self._preprocess_captcha(image)

            img_bytes = BytesIO()
            processed.save(img_bytes, format='PNG')
            result = self.ocr.classification(img_bytes.getvalue())
            # Clean result - remove any non-alphanumeric chars
            result = re.sub(r'[^A-Za-z0-9]', '', result)
            return result

        # Fallback to easyocr
        if self.easyocr_reader:
            import numpy as np
            img_array = np.array(image)
            results = self.easyocr_reader.readtext(img_array, detail=0)
            if results:
                captcha_text = ''.join(results).strip()
                captcha_text = re.sub(r'[^A-Za-z0-9]', '', captcha_text)
                return captcha_text

        raise RuntimeError("No OCR library available. Install ddddocr or easyocr.")

    def solve_captcha_manual(self, image: Image.Image) -> str:
        """
        Solve CAPTCHA manually by displaying it to the user

        Args:
            image: PIL Image of the CAPTCHA

        Returns:
            User-entered CAPTCHA text
        """
        # Save temporarily and display
        temp_path = "/tmp/mvr_captcha.png"
        image.save(temp_path)
        print(f"\nCAPTCHA image saved to: {temp_path}")
        print("Please open the image and enter the CAPTCHA text below.")

        # Try to open the image automatically
        import subprocess
        import platform
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', temp_path], check=False)
            elif platform.system() == 'Linux':
                subprocess.run(['xdg-open', temp_path], check=False)
        except:
            pass

        captcha_text = input("Enter CAPTCHA text: ").strip()
        return captcha_text

    def _do_query(self, egn: str, last_name: str, captcha: str) -> Dict:
        """Internal method to submit a single query attempt"""
        params = {
            'type': '6729',
            'egn': egn,
            'name': last_name,
            'captcha': captcha,
            'submitted': '1'
        }

        query_url = f"{self.BASE_URL}{self.SERVICE_PATH}?{urlencode(params, quote_via=quote)}"
        response = self.session.get(query_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Look for result in various containers
        result_div = None
        for selector in [
            lambda: soup.find(class_=lambda x: x and 'alert' in str(x).lower() if x else False),
            lambda: soup.find('div', class_=re.compile(r'info-bubble', re.I)),
            lambda: soup.find(class_=lambda x: x and 'result' in str(x).lower() if x else False),
        ]:
            result_div = selector()
            if result_div:
                break

        is_error = False
        is_captcha_error = False
        result_text = ""

        if result_div:
            result_text = result_div.get_text(separator=' ', strip=True)
            if 'Грешка' in result_text or 'Невалидна' in result_text:
                is_error = True
                if 'капча' in result_text.lower():
                    is_captcha_error = True
        else:
            text = soup.get_text()
            success_match = re.search(r'(След\s+\d{2}\.\d{2}\.\d{4}.*?получен\.)', text, re.DOTALL)
            if success_match:
                result_text = success_match.group(1)
            else:
                error_match = re.search(r'(Грешка.*?капча|Невалидна.*?капча)', text, re.DOTALL | re.I)
                if error_match:
                    result_text = error_match.group(1)
                    is_error = True
                    is_captcha_error = True
                else:
                    result_text = "Could not parse result"

        return {
            'success': not is_error,
            'is_captcha_error': is_captcha_error,
            'egn': egn,
            'last_name': last_name,
            'result': result_text,
            'raw_html': response.text
        }

    def query_documents(self, egn: str, last_name: str, captcha: Optional[str] = None) -> Dict:
        """
        Query for issued and unreceived documents

        Args:
            egn: Bulgarian ID number (ЕГН)
            last_name: Last name in Cyrillic
            captcha: Optional pre-solved CAPTCHA (if None, will auto-solve with retries)

        Returns:
            Dictionary with query results
        """
        # If pre-solved CAPTCHA provided, use it directly
        if captcha:
            print(f"Using pre-solved CAPTCHA: {captcha}")
            return self._do_query(egn, last_name, captcha)

        # Auto-solve with retries
        for attempt in range(1, self.max_retries + 1):
            print(f"\n--- Attempt {attempt}/{self.max_retries} ---")

            # Reset session for fresh CAPTCHA
            self.session.cookies.clear()

            print("Fetching form page...")
            soup = self.get_form_page()

            print("Extracting CAPTCHA...")
            captcha_image = self.extract_captcha_image(soup)

            if not captcha_image:
                print("No CAPTCHA found, proceeding without it...")
                captcha = ""
            elif self.use_ocr:
                print("Solving CAPTCHA with OCR...")
                captcha = self.solve_captcha_ocr(captcha_image)
                print(f"OCR result: '{captcha}'")
            else:
                captcha = self.solve_captcha_manual(captcha_image)
                # Manual mode doesn't retry
                return self._do_query(egn, last_name, captcha)

            # Submit query
            print("Submitting query...")
            result = self._do_query(egn, last_name, captcha)

            if result['success']:
                print(f"Success on attempt {attempt}!")
                return result

            if result['is_captcha_error']:
                print(f"CAPTCHA error, retrying...")
                continue
            else:
                # Non-CAPTCHA error, don't retry
                return result

        # All retries exhausted
        print(f"Failed after {self.max_retries} attempts")
        return result


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Query MVR for document status')
    parser.add_argument('egn', help='Bulgarian ID number (ЕГН)')
    parser.add_argument('last_name', help='Last name in Cyrillic')
    parser.add_argument('--manual', action='store_true', help='Use manual CAPTCHA solving instead of OCR')
    parser.add_argument('--captcha', help='Pre-solved CAPTCHA (skips CAPTCHA fetching)')
    parser.add_argument('--retries', type=int, default=15, help='Max CAPTCHA retry attempts (default: 15)')

    args = parser.parse_args()

    # Default to OCR mode with ddddocr (automatic)
    client = MVRClient(use_ocr=not args.manual, max_retries=args.retries)

    try:
        result = client.query_documents(args.egn, args.last_name, args.captcha)

        print("\n" + "="*80)
        status = "SUCCESS" if result['success'] else "FAILED"
        print(f"QUERY RESULT - {status}")
        print("="*80)
        print(f"ЕГН: {result['egn']}")
        print(f"Last Name: {result['last_name']}")
        print(f"\nResult: {result['result']}")
        print("="*80)

        # Exit with error code if query failed
        if not result['success']:
            exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()
