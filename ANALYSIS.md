# MVR API Analysis

## Summary

The MVR document query service does NOT have a separate JSON API. It's a simple HTML form-based service with CAPTCHA protection.

## API Endpoint

```
GET https://www.mvr.bg/електронизирани-услуги/справка-за-издадени-и-неполучени-български-лични-документи
```

## Request Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `type` | `6729` | Document type (appears to be constant for this service) |
| `egn` | `XXXXXXXXXX` | Bulgarian ID number (ЕГН) - 10 digits |
| `name` | `<Cyrillic>` | Last name (URL encoded in Cyrillic) |
| `captcha` | `<solved>` | CAPTCHA solution text |
| `submitted` | `1` | Form submission flag |

## Response

- **Format**: HTML page (not JSON)
- **Result location**: Embedded in the HTML within a div with class indicating success/failure
- **Example response**: "След DD.MM.YYYY г. лицето с ЕГН [XXXXXXXXXX] няма издаден документ от избрания вид или същият вече е получен."

## CAPTCHA

- **Type**: Custom text-based CAPTCHA (not reCAPTCHA or hCaptcha)
- **Challenge**: Displayed as an image on the initial form page
- **Solution**: User must read and type the text from the image

## Implementation Strategy

### Option 1: OCR-based (Recommended)
1. Fetch the form page to get the CAPTCHA image
2. Use OCR (Tesseract, EasyOCR, or cloud service) to solve CAPTCHA
3. Submit GET request with parameters
4. Parse HTML response to extract result

### Option 2: Manual CAPTCHA solving
1. Fetch form page
2. Display CAPTCHA to user or send to solving service (2captcha, Anti-Captcha)
3. Submit with solution
4. Parse result

### Option 3: CAPTCHA solving service
1. Use automated CAPTCHA solving API (2captcha, Anti-Captcha)
2. Cost: ~$1-3 per 1000 solves
3. Success rate: 85-95%

## Rate Limiting

- No explicit rate limiting observed in traffic
- CAPTCHA serves as natural rate limiter (~3-5 seconds per query)
- Cloudflare protection detected (challenge-platform requests)
- Recommend: 1-2 second delay between requests

## Security Considerations

- Cloudflare bot detection active
- Must use realistic User-Agent headers
- May need to handle Cloudflare challenges
- Session cookies might be validated

## Challenges

1. **No JSON API**: Must parse HTML responses
2. **CAPTCHA**: Requires OCR or solving service
3. **Cloudflare**: May block automated requests
4. **HTML parsing**: Fragile if site structure changes

## Recommended Approach

Build a Python client that:
1. Uses `requests` with realistic headers
2. Fetches form page and extracts CAPTCHA image
3. Uses EasyOCR or Tesseract for CAPTCHA solving
4. Submits query and parses HTML response with BeautifulSoup
5. Includes retry logic and rate limiting
