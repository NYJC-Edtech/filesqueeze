"""FileSqueeze setup.py for PyPI distribution."""

from pathlib import Path
from setuptools import setup, find_packages

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read version from __init__.py
version = "0.1.0"

setup(
    name="filesqueeze",
    version=version,
    description="Utility package for compressing videos, PDFs, and images",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="JS Ng",
    author_email="ngjunsiang@gmail.com",
    url="https://github.com/yourusername/filesqueeze",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/filesqueeze/issues",
        "Source": "https://github.com/yourusername/filesqueeze",
        "Documentation": "https://github.com/yourusername/filesqueeze/blob/main/README.md",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.11",
    install_requires=[
        "tomli>=2.0.0; python_version<'3.11'",
        "tomli-w>=1.0.0",
        "watchdog>=6.0.0,<7.0.0",
        "pystray>=0.19.5,<0.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        "ocr": [
            "pdfminer-six>=20231228",
        ],
    },
    entry_points={
        "console_scripts": [
            "filesqueeze=filesqueeze.__main__:main",
            "filesqueeze-compress=filesqueeze.__main__:main",
            "filesqueeze-scan=filesqueeze.__main__:main",
            "filesqueeze-watch=filesqueeze.__main__:main",
            "filesqueeze-service=filesqueeze.__main__:main",
            "filesqueeze-init=filesqueeze.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "filesqueeze": [
            "default.toml",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    keywords="compression video pdf image ffmpeg ghostscript",
    license="MIT",
    zip_safe=False,
)
