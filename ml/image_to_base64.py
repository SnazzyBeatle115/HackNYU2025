"""
Image to Base64 Converter Utility
Simple tool for converting images to base64 format for testing purposes.
NOT for production use.
"""
import base64
import sys
import argparse
import json
import requests
from pathlib import Path


def image_to_base64(image_path: str, data_url: bool = False) -> str:
    """
    Convert an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        data_url: If True, return as data URL format (data:image/...;base64,...)
                  If False, return raw base64 string
    
    Returns:
        Base64 encoded string (raw or data URL format)
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Read image file
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
    
    # Encode to base64
    base64_string = base64.b64encode(image_data).decode('utf-8')
    
    if data_url:
        # Determine MIME type from file extension
        ext = image_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')
        return f"data:{mime_type};base64,{base64_string}"
    
    return base64_string


def test_detectscreen_endpoint(image_path: str, endpoint_url: str = "http://localhost:5000/detectscreen"):
    """
    Test the /detectscreen endpoint by sending an image and displaying the LLM analysis.
    
    Args:
        image_path: Path to the image file
        endpoint_url: URL of the detectscreen endpoint
    """
    print(f"Converting image to base64...")
    base64_string = image_to_base64(image_path, data_url=False)
    print(f"Image converted (length: {len(base64_string)} characters)")
    print(f"\nSending to {endpoint_url}...")
    
    try:
        # Prepare request
        payload = {
            "image": base64_string
        }
        
        # Send request
        response = requests.post(
            endpoint_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Vision models can take a while
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("\n" + "="*60)
            print("LLM ANALYSIS RESULTS")
            print("="*60)
            
            print(f"\nStatus: {result.get('status', 'unknown')}")
            
            if 'model_used' in result:
                print(f"Model Used: {result['model_used']}")
            
            print(f"\n{'─'*60}")
            print("EXTRACTED TEXT:")
            print(f"{'─'*60}")
            text_extracted = result.get('text_extracted', 'N/A')
            if text_extracted:
                print(text_extracted[:500] + ("..." if len(text_extracted) > 500 else ""))
            else:
                print("No text extracted")
            
            print(f"\n{'─'*60}")
            print("ACTIVITY DETECTED:")
            print(f"{'─'*60}")
            activity = result.get('activity_detected', 'N/A')
            print(activity)
            
            print(f"\n{'─'*60}")
            print("STUDY STATUS:")
            print(f"{'─'*60}")
            is_studying = result.get('is_studying', None)
            if is_studying is True:
                print("✓ User IS studying")
            elif is_studying is False:
                print("✗ User is NOT studying")
            else:
                print("? Unable to determine")
            
            if 'details' in result and result['details']:
                print(f"\n{'─'*60}")
                print("DETAILS:")
                print(f"{'─'*60}")
                print(result['details'])
            
            print(f"\n{'─'*60}")
            print("FULL AI ANALYSIS:")
            print(f"{'─'*60}")
            analysis = result.get('analysis', 'N/A')
            print(analysis)
            print("="*60)
            
            return 0
        else:
            print(f"\nError: Endpoint returned status code {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response: {response.text}")
            return 1
            
    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to {endpoint_url}")
        print("Make sure the API server is running (python api_server.py)")
        return 1
    except requests.exceptions.Timeout:
        print(f"\nError: Request timed out (took longer than 60 seconds)")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Convert image to base64 string (testing utility)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python image_to_base64.py image.png
  python image_to_base64.py screenshot.jpg --data-url
  python image_to_base64.py photo.png --output output.txt
  python image_to_base64.py test.png --test-endpoint
        """
    )
    parser.add_argument('image', help='Path to image file')
    parser.add_argument(
        '--data-url',
        action='store_true',
        help='Output as data URL format (data:image/...;base64,...)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Save output to file (optional)'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Show first 100 characters of base64 string'
    )
    parser.add_argument(
        '--test-endpoint',
        action='store_true',
        help='Test the /detectscreen endpoint with this image'
    )
    parser.add_argument(
        '--endpoint-url',
        default='http://localhost:5000/detectscreen',
        help='URL of the detectscreen endpoint (default: http://localhost:5000/detectscreen)'
    )
    
    args = parser.parse_args()
    
    # If testing endpoint, do that and exit
    if args.test_endpoint:
        return test_detectscreen_endpoint(args.image, args.endpoint_url)
    
    try:
        # Convert image
        base64_result = image_to_base64(args.image, data_url=args.data_url)
        
        # Output result
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                f.write(base64_result)
            print(f"Base64 string saved to: {output_path}")
            print(f"Length: {len(base64_result)} characters")
        else:
            if args.preview:
                preview = base64_result[:100]
                print(f"Base64 string (first 100 chars): {preview}...")
                print(f"Full length: {len(base64_result)} characters")
            else:
                print(base64_result)
        
        return 0
    
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error converting image: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

