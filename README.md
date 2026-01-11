# MVR API Client

Reverse-engineered Python client for Bulgarian Ministry of Internal Affairs (MVR) document query service.

Query for issued and unreceived Bulgarian identity documents programmatically.

## Features

- **Fully automated CAPTCHA solving** using ddddocr with automatic retries (~10-20% success per attempt)
- Manual CAPTCHA solving fallback (if OCR fails)
- Clean Python API
- Session management with cookie persistence
- Realistic browser headers to avoid blocking
- Proper handling of gzip compression

## Project Structure

```
mvr-api-client/
├── venv/                    # Virtual environment
├── captured_data/           # Captured network traffic (gitignored)
├── interceptor.py           # Network traffic interceptor
├── mvr_client.py           # Main API client
├── requirements.txt        # Python dependencies
├── ANALYSIS.md             # Technical analysis of the API
└── README.md              # This file
```

## Installation

```bash
cd ~/personal-projects/mvr-api-client
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Basic Usage (Fully Automated)

```bash
python mvr_client.py "<YOUR_EGN>" "<YOUR_LAST_NAME>"
```

This will:
1. Automatically fetch the form page and CAPTCHA
2. Use ddddocr to solve the CAPTCHA
3. Retry up to 15 times if CAPTCHA solving fails
4. Submit the query and display the result

### With Manual CAPTCHA Solving

If you prefer to solve the CAPTCHA manually:

```bash
python mvr_client.py "<YOUR_EGN>" "<YOUR_LAST_NAME>" --manual
```

### Custom Retry Count

Adjust the number of CAPTCHA retry attempts:

```bash
python mvr_client.py "<YOUR_EGN>" "<YOUR_LAST_NAME>" --retries 20
```

### With Pre-solved CAPTCHA

If you already know the CAPTCHA (useful for testing):

```bash
python mvr_client.py "<YOUR_EGN>" "<YOUR_LAST_NAME>" --captcha "ABC123"
```

**Note:** Pre-solved CAPTCHAs must be used immediately as they expire with the session.

### Programmatic Usage

```python
from mvr_client import MVRClient

# Initialize client (with OCR enabled)
client = MVRClient(use_ocr=True)

# Query for documents
result = client.query_documents(
    egn="<YOUR_EGN>",
    last_name="<YOUR_LAST_NAME>"
)

print(result['result'])
# Output: "След DD.MM.YYYY г. лицето с ЕГН [XXXXXXXXXX] няма издаден
#          документ от избрания вид или същият вече е получен."
```

## API Details

See [ANALYSIS.md](ANALYSIS.md) for technical details about the MVR service API.

**Key Points:**
- Service URL: `https://www.mvr.bg/електронизирани-услуги/справка-за-издадени-и-неполучени-български-лични-документи`
- Method: GET request with query parameters
- CAPTCHA: Custom image-based text CAPTCHA
- Response: HTML page (parsed for result text)

## Rate Limiting

- Respect the service: Add delays between requests (1-2 seconds minimum)
- CAPTCHA naturally limits request rate
- Cloudflare protection may block aggressive automation

## Development

### Intercepting Network Traffic

To analyze the API yourself:

```bash
python interceptor.py
```

This opens a browser and captures all network requests/responses to `captured_data/`.

## Known Limitations

1. **No JSON API**: Service returns HTML, requires parsing
2. **CAPTCHA required**: Every query needs CAPTCHA solving
3. **OCR accuracy**: ~10-20% per attempt due to diagonal strikethrough lines (automatic retries compensate)
4. **Cloudflare**: May require additional anti-bot bypass techniques
5. **Session-bound CAPTCHA**: Each CAPTCHA is tied to a session and expires quickly

## Troubleshooting

**OCR not working?**
- Ensure ddddocr is installed: `pip install ddddocr`
- Use manual mode: `--manual`
- Increase retries: `--retries 20`

**Getting blocked?**
- Add delays between requests
- Check if Cloudflare is challenging the requests
- Use realistic headers (already configured in client)

**Can't parse results?**
- Check `raw_html` in result dictionary
- HTML structure may have changed

## Legal & Ethical Use

This client accesses a public government service. Use responsibly:
- Don't abuse rate limits
- Don't attempt to bypass security measures maliciously
- Only query data you're authorized to access
- Respect the service's terms of use

## License

MIT

## Usage Notes

- **ЕГН**: Your 10-digit Bulgarian personal identification number
- **Last Name**: Your last name in Cyrillic characters
