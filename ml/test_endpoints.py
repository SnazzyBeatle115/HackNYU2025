"""
API Endpoint Testing Utility
Test the /detectscreen and /detectcamera endpoints with images.
NOT for production use.
"""
import base64
import sys
import argparse
import json
import requests
from pathlib import Path


def image_to_base64(image_path: str) -> str:
    """
    Convert an image file to base64 string.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Base64 encoded string
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Read image file
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
    
    # Encode to base64
    base64_string = base64.b64encode(image_data).decode('utf-8')
    return base64_string


def test_detectcamera_endpoint(image_path: str, endpoint_url: str = "http://localhost:5000/detectcamera"):
    """
    Test the /detectcamera endpoint by sending an image and displaying the LLM analysis.
    
    Args:
        image_path: Path to the image file
        endpoint_url: URL of the detectcamera endpoint
    """
    print(f"Converting image to base64...")
    base64_string = image_to_base64(image_path)
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
            print("CAMERA DETECTION RESULTS")
            print("="*60)
            print("\n" + json.dumps(result, indent=2))
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


def test_detectscreen_endpoint(image_path: str, endpoint_url: str = "http://localhost:5000/detectscreen"):
    """
    Test the /detectscreen endpoint by sending an image and displaying the LLM analysis.
    
    Args:
        image_path: Path to the image file
        endpoint_url: URL of the detectscreen endpoint
    """
    print(f"Converting image to base64...")
    base64_string = image_to_base64(image_path)
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
            print("SCREEN DETECTION RESULTS")
            print("="*60)
            print("\n" + json.dumps(result, indent=2))
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
        description='Test API endpoints with images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_endpoints.py test_camera.jpg --camera
  python test_endpoints.py test.png --screen
  python test_endpoints.py screenshot.jpg --screen --url http://localhost:8080/detectscreen
        """
    )
    parser.add_argument('image', help='Path to image file')
    parser.add_argument(
        '--camera',
        action='store_true',
        help='Test the /detectcamera endpoint'
    )
    parser.add_argument(
        '--screen',
        action='store_true',
        help='Test the /detectscreen endpoint'
    )
    parser.add_argument(
        '--url',
        help='Custom endpoint URL (overrides default)'
    )
    
    args = parser.parse_args()
    
    # Determine which endpoint to test
    if args.camera and args.screen:
        print("Error: Cannot test both endpoints at once. Use either --camera or --screen")
        return 1
    
    if not args.camera and not args.screen:
        print("Error: Must specify either --camera or --screen")
        return 1
    
    # Set endpoint URL
    if args.camera:
        endpoint_url = args.url or "http://localhost:5000/detectcamera"
        return test_detectcamera_endpoint(args.image, endpoint_url)
    else:  # args.screen
        endpoint_url = args.url or "http://localhost:5000/detectscreen"
        return test_detectscreen_endpoint(args.image, endpoint_url)


if __name__ == '__main__':
    sys.exit(main())

