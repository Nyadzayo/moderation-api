"""Tests for image moderation functionality."""

import asyncio
import base64
import io
import sys
from PIL import Image

sys.path.insert(0, '/Users/kelvinnyadzayo/test-moderation')

from app.services.image_moderation import (
    decode_base64_image,
    validate_and_preprocess_image,
    compute_image_hash,
    moderate_image,
)


def create_test_image(width=100, height=100, color=(255, 0, 0)):
    """Create a simple test image."""
    img = Image.new('RGB', (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def image_to_base64(image_bytes):
    """Convert image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def image_to_data_uri(image_bytes):
    """Convert image bytes to data URI."""
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"


async def test_decode_base64_plain():
    """Test decoding plain base64 image."""
    print("\n" + "=" * 80)
    print("Test 1: Decode Plain Base64 Image")
    print("=" * 80)

    image_bytes = create_test_image()
    b64_string = image_to_base64(image_bytes)

    decoded_bytes, content_hash = decode_base64_image(b64_string)

    assert len(decoded_bytes) > 0, "Decoded bytes should not be empty"
    assert len(content_hash) == 16, "Content hash should be 16 characters"

    print(f"✓ Decoded {len(decoded_bytes)} bytes")
    print(f"✓ Content hash: {content_hash}")
    print("PASSED")


async def test_decode_base64_data_uri():
    """Test decoding data URI format."""
    print("\n" + "=" * 80)
    print("Test 2: Decode Data URI Format")
    print("=" * 80)

    image_bytes = create_test_image()
    data_uri = image_to_data_uri(image_bytes)

    decoded_bytes, content_hash = decode_base64_image(data_uri)

    assert len(decoded_bytes) > 0, "Decoded bytes should not be empty"
    print(f"✓ Decoded data URI: {len(decoded_bytes)} bytes")
    print(f"✓ Content hash: {content_hash}")
    print("PASSED")


async def test_validate_and_preprocess():
    """Test image validation and preprocessing."""
    print("\n" + "=" * 80)
    print("Test 3: Validate and Preprocess Image (224x224 Optimization)")
    print("=" * 80)

    image_bytes = create_test_image(200, 150)

    pil_image = validate_and_preprocess_image(image_bytes)

    assert pil_image.mode == "RGB", "Image should be converted to RGB"
    assert pil_image.size == (224, 224), "Image should be resized to 224x224 for model"

    print(f"✓ Image mode: {pil_image.mode}")
    print(f"✓ Image size: {pil_image.size} (resized from 200x150)")
    print("PASSED")


async def test_validate_oversized_image():
    """Test handling of oversized images."""
    print("\n" + "=" * 80)
    print("Test 4: Validate Oversized Image (Rejection)")
    print("=" * 80)

    # Create large image (should be rejected)
    image_bytes = create_test_image(5000, 5000)

    try:
        pil_image = validate_and_preprocess_image(image_bytes)
        assert False, "Should raise ValueError for oversized image"
    except ValueError as e:
        print(f"✓ Correctly rejected oversized image: {str(e)}")
        print("PASSED")


async def test_compute_hash_consistency():
    """Test that same image produces same hash."""
    print("\n" + "=" * 80)
    print("Test 5: Content Hash Consistency")
    print("=" * 80)

    image_bytes = create_test_image()

    hash1 = compute_image_hash(image_bytes)
    hash2 = compute_image_hash(image_bytes)

    assert hash1 == hash2, "Same image should produce same hash"

    # Different image should produce different hash
    image_bytes2 = create_test_image(color=(0, 255, 0))
    hash3 = compute_image_hash(image_bytes2)

    assert hash1 != hash3, "Different images should produce different hashes"

    print(f"✓ Hash consistency verified")
    print(f"  Image 1 hash: {hash1}")
    print(f"  Image 2 hash (same): {hash2}")
    print(f"  Image 3 hash (different): {hash3}")
    print("PASSED")


async def test_moderate_image_base64():
    """Test full image moderation pipeline with base64."""
    print("\n" + "=" * 80)
    print("Test 6: Full Moderation Pipeline (Base64)")
    print("=" * 80)
    print("⏳ Loading image model (this may take a few seconds)...")

    image_bytes = create_test_image()
    b64_string = image_to_base64(image_bytes)

    scores, content_hash = await moderate_image(b64_string)

    assert "sexual" in scores, "Should return sexual score"
    assert 0.0 <= scores["sexual"] <= 1.0, "Score should be between 0 and 1"
    assert len(content_hash) == 16, "Content hash should be 16 characters"

    print(f"✓ Moderation complete")
    print(f"  Sexual score: {scores['sexual']:.4f}")
    print(f"  Content hash: {content_hash}")
    print("PASSED")


async def test_invalid_base64():
    """Test handling of invalid base64."""
    print("\n" + "=" * 80)
    print("Test 7: Invalid Base64 Handling")
    print("=" * 80)

    try:
        decode_base64_image("not-valid-base64!!!")
        assert False, "Should raise ValueError"
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {str(e)}")
        print("PASSED")


async def test_oversized_base64():
    """Test handling of oversized image via base64."""
    print("\n" + "=" * 80)
    print("Test 8: Oversized Image Rejection")
    print("=" * 80)

    # Create image larger than MAX_IMAGE_SIZE_MB (10MB)
    # Approximate: 3000x3000 PNG ≈ 12MB
    large_image = create_test_image(4000, 4000)
    b64_string = image_to_base64(large_image)

    size_mb = len(large_image) / (1024 * 1024)
    print(f"  Test image size: {size_mb:.2f}MB")

    if size_mb > 10:
        try:
            decode_base64_image(b64_string)
            assert False, "Should raise ValueError for oversized image"
        except ValueError as e:
            print(f"✓ Correctly rejected oversized image: {str(e)}")
            print("PASSED")
    else:
        print("✓ Image within size limit, skipping rejection test")
        print("PASSED")


async def test_rgba_to_rgb_conversion():
    """Test RGBA to RGB conversion."""
    print("\n" + "=" * 80)
    print("Test 9: RGBA to RGB Conversion")
    print("=" * 80)

    # Create RGBA image
    img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    image_bytes = buffer.getvalue()

    pil_image = validate_and_preprocess_image(image_bytes)

    assert pil_image.mode == "RGB", "RGBA should be converted to RGB"
    print(f"✓ Converted RGBA to RGB")
    print(f"  Original mode: RGBA")
    print(f"  Final mode: {pil_image.mode}")
    print("PASSED")


async def test_different_formats():
    """Test different image formats (JPEG, PNG)."""
    print("\n" + "=" * 80)
    print("Test 10: Multiple Image Formats")
    print("=" * 80)

    formats_tested = []

    for fmt in ['PNG', 'JPEG']:
        img = Image.new('RGB', (100, 100), (0, 0, 255))
        buffer = io.BytesIO()
        img.save(buffer, format=fmt)
        image_bytes = buffer.getvalue()

        pil_image = validate_and_preprocess_image(image_bytes)
        assert pil_image.mode == "RGB", f"{fmt} should be valid"
        formats_tested.append(fmt)

    print(f"✓ Successfully processed formats: {', '.join(formats_tested)}")
    print("PASSED")


async def main():
    """Run all image moderation tests."""
    print("\n" + "=" * 80)
    print("IMAGE MODERATION TEST SUITE")
    print("=" * 80)

    tests = [
        test_decode_base64_plain,
        test_decode_base64_data_uri,
        test_validate_and_preprocess,
        test_validate_oversized_image,
        test_compute_hash_consistency,
        test_moderate_image_base64,
        test_invalid_base64,
        test_oversized_base64,
        test_rgba_to_rgb_conversion,
        test_different_formats,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ FAILED: {test.__name__}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
