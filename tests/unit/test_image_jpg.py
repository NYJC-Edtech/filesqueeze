"""Unit tests for Pillow-based JPG compression.

Covers filesqueeze.ops.image.compress_image_to_jpg and the image extension
constants: format conversion, target JPEG settings (quality 88, progressive,
4:2:2), transparency flattening, EXIF orientation, keep-if-larger rules and
the always-convert formats (WebP/HEIC).
"""

import random
from pathlib import Path

import pytest
from PIL import Image, JpegImagePlugin

from filesqueeze.constants import FileExtensions
from filesqueeze.file_type_registry import get_file_type_registry
from filesqueeze.fsm.enums import Document
from filesqueeze.ops.image import compress_image_to_jpg, get_image_dimensions


def noisy_rgb(width: int = 800, height: int = 600, seed: int = 42) -> Image.Image:
    """Deterministic noise image (noise defeats PNG compression, so JPG
    conversions reliably shrink)."""
    rng = random.Random(seed)
    return Image.frombytes("RGB", (width, height), rng.randbytes(width * height * 3))


@pytest.fixture
def rgba_png(tmp_path: Path) -> Path:
    """Noisy RGBA PNG with a fully transparent 100x100 corner."""
    im = noisy_rgb().convert("RGBA")
    px = im.load()
    for y in range(100):
        for x in range(100):
            px[x, y] = (0, 0, 0, 0)
    path = tmp_path / "input.png"
    im.save(path)
    return path


@pytest.fixture
def photo_jpg(tmp_path: Path) -> Path:
    """Noisy high-quality JPEG (recompressing at lower quality shrinks it)."""
    path = tmp_path / "photo.jpg"
    noisy_rgb(400, 300).save(path, quality=95, subsampling=0)
    return path


def assert_jpg_settings(path: Path) -> None:
    """Assert the file is a progressive 4:2:2 JPEG."""
    with Image.open(path) as im:
        assert im.format == "JPEG"
        assert im.info.get("progressive") == 1
        assert JpegImagePlugin.get_sampling(im) == 1  # 1 = 4:2:2


class TestConversionToJpg:
    """PNG/BMP/TIFF inputs convert to JPG with the target settings."""

    def test_png_converts_to_jpg(self, rgba_png: Path, tmp_path: Path):
        out = compress_image_to_jpg(str(rgba_png), str(tmp_path / "compressed_input.jpg"))

        assert out.name == "compressed_input.jpg"
        assert out.exists()
        assert_jpg_settings(out)
        # Noise image: JPG at q88 must be smaller than the PNG
        assert out.stat().st_size < rgba_png.stat().st_size

    def test_transparency_flattened_onto_white(self, rgba_png: Path, tmp_path: Path):
        out = compress_image_to_jpg(str(rgba_png), str(tmp_path / "out.jpg"))

        with Image.open(out) as im:
            assert im.mode == "RGB"
            corner = im.getpixel((50, 50))
        assert corner == (255, 255, 255)

    def test_tiff_and_bmp_convert(self, tmp_path: Path):
        src = noisy_rgb(300, 200)
        for ext, kwargs in ((".tiff", {"compression": "tiff_deflate"}), (".bmp", {})):
            input_path = tmp_path / f"img{ext}"
            src.save(input_path, **kwargs)

            out = compress_image_to_jpg(str(input_path), str(tmp_path / f"compressed_img{ext}".replace(ext, ".jpg")))
            assert out.suffix == ".jpg"
            assert_jpg_settings(out)
            assert out.stat().st_size < input_path.stat().st_size

    def test_explicit_non_jpg_output_still_writes_jpg(self, rgba_png: Path, tmp_path: Path):
        """The JPG outcome always lands on a .jpg name, even when the caller
        planned the original extension."""
        out = compress_image_to_jpg(str(rgba_png), str(tmp_path / "planned.png"))
        assert out.name == "planned.jpg"
        assert_jpg_settings(out)

    def test_downscale_applied(self, rgba_png: Path, tmp_path: Path):
        out = compress_image_to_jpg(str(rgba_png), str(tmp_path / "out.jpg"), max_width=1920, max_height=1080)

        with Image.open(out) as im:
            assert im.width <= 1920
            assert im.height <= 1080
            # Aspect preserved
            assert abs(im.width / im.height - 800 / 600) < 0.02

    def test_exif_orientation_applied(self, tmp_path: Path):
        im = noisy_rgb(40, 20)
        exif = Image.Exif()
        exif[274] = 6  # Orientation: rotate 90 CW
        input_path = tmp_path / "rotated.jpg"
        im.save(input_path, exif=exif)

        # Low quality so the re-encode shrinks and the JPG is actually used
        out = compress_image_to_jpg(str(input_path), str(tmp_path / "out.jpg"), quality=20)

        with Image.open(out) as result:
            assert (result.width, result.height) == (20, 40)

    def test_icc_profile_preserved(self, tmp_path: Path):
        ImageCms = pytest.importorskip("PIL.ImageCms")
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

        input_path = tmp_path / "icc.png"
        noisy_rgb(200, 150).save(input_path, icc_profile=profile)

        out = compress_image_to_jpg(str(input_path), str(tmp_path / "out.jpg"))
        with Image.open(out) as im:
            assert im.info.get("icc_profile") == profile

    def test_animated_webp_rejected(self, tmp_path: Path):
        frame_a = noisy_rgb(50, 50, seed=1)
        frame_b = noisy_rgb(50, 50, seed=2)
        input_path = tmp_path / "anim.webp"
        frame_a.save(input_path, save_all=True, append_images=[frame_b], duration=100)

        with Image.open(input_path) as check:
            assert check.is_animated  # fixture really is animated

        with pytest.raises(RuntimeError, match=r"[Aa]nimated"):
            compress_image_to_jpg(str(input_path), str(tmp_path / "out.jpg"))

    def test_dimensions_helper(self, rgba_png: Path):
        assert get_image_dimensions(str(rgba_png)) == (800, 600)


class TestKeepIfLarger:
    """JPG output is only used when it is strictly smaller (except
    WebP/HEIC, which always convert)."""

    def test_tiny_png_kept_when_jpg_grows(self, tmp_path: Path):
        input_path = tmp_path / "tiny.png"
        Image.new("RGB", (10, 10), (0, 255, 0)).save(input_path, optimize=True)

        out = compress_image_to_jpg(str(input_path), str(tmp_path / "compressed_tiny.jpg"))

        assert out.name == "compressed_tiny.png"
        assert out.read_bytes() == input_path.read_bytes()

    def test_jpg_kept_when_recompress_grows(self, tmp_path: Path):
        # Low-quality input, higher-quality re-encode requested: always grows
        input_path = tmp_path / "lowq.jpg"
        Image.new("RGB", (40, 40), (10, 200, 30)).save(input_path, quality=10, optimize=True, progressive=True)

        out = compress_image_to_jpg(str(input_path), str(tmp_path / "compressed_lowq.jpg"), quality=95)

        assert out.name == "compressed_lowq.jpg"
        assert out.read_bytes() == input_path.read_bytes()

    def test_jpg_recompressed_when_smaller(self, photo_jpg: Path, tmp_path: Path):
        out = compress_image_to_jpg(str(photo_jpg), str(tmp_path / "compressed_photo.jpg"), quality=50)

        assert out.name == "compressed_photo.jpg"
        assert out.read_bytes() != photo_jpg.read_bytes()
        assert_jpg_settings(out)
        assert out.stat().st_size < photo_jpg.stat().st_size


class TestAlwaysConvertFormats:
    """WebP/HEIC convert to JPG even when the result is larger."""

    def test_webp_always_converts(self, tmp_path: Path):
        input_path = tmp_path / "tiny.webp"
        Image.new("RGB", (10, 10), (0, 255, 0)).save(input_path, quality=40)

        out = compress_image_to_jpg(str(input_path), str(tmp_path / "compressed_tiny.jpg"))

        assert out.name == "compressed_tiny.jpg"
        assert_jpg_settings(out)
        # Compatibility conversion: output may well be larger than the WebP
        assert out.stat().st_size > 0

    def test_heic_always_converts(self, tmp_path: Path):
        pillow_heif = pytest.importorskip("pillow_heif")
        pillow_heif.register_heif_opener()

        input_path = tmp_path / "tiny.heic"
        Image.new("RGB", (10, 10), (0, 255, 0)).save(input_path, quality=40)

        out = compress_image_to_jpg(str(input_path), str(tmp_path / "compressed_tiny.jpg"))

        assert out.name == "compressed_tiny.jpg"
        assert_jpg_settings(out)


class TestConfigIntegration:
    """Config-driven parameters and validation."""

    def test_invalid_subsampling_config_raises(self, rgba_png: Path, tmp_path: Path):
        from filesqueeze.config import Config

        config = Config({"document": {"jpeg_subsampling": "4:1:1"}})
        with pytest.raises(Exception, match="jpeg_subsampling"):
            compress_image_to_jpg(str(rgba_png), str(tmp_path / "out.jpg"), config=config)

    def test_non_progressive_override(self, rgba_png: Path, tmp_path: Path):
        out = compress_image_to_jpg(str(rgba_png), str(tmp_path / "out.jpg"), progressive=False)

        with Image.open(out) as im:
            assert im.format == "JPEG"
            assert not im.info.get("progressive")


class TestImageExtensionRegistry:
    """All image extensions are registered consistently."""

    def test_registry_lists_all_image_extensions(self):
        registry = get_file_type_registry()
        for ext in FileExtensions.IMAGE:
            assert registry.is_supported(ext)

    def test_fsm_enums_cover_image_extensions(self):
        for ext in FileExtensions.IMAGE:
            Document.validate(ext.upper())

    def test_native_and_always_convert_are_subsets(self):
        assert FileExtensions.IMAGE_NATIVE_JPG < set(FileExtensions.IMAGE)
        assert FileExtensions.IMAGE_ALWAYS_CONVERT < set(FileExtensions.IMAGE)
