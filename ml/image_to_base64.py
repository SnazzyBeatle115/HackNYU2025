"""
Image to Base64 Converter Utility
Simple tool for converting images to base64 format.
NOT for production use.
"""
import base64
import sys
import argparse
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


def main():
    parser = argparse.ArgumentParser(
        description='Convert image to base64 string',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python image_to_base64.py image.png
  python image_to_base64.py screenshot.jpg --data-url
  python image_to_base64.py photo.png --output output.txt
  python image_to_base64.py test.png --preview
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
    
    args = parser.parse_args()
    
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

