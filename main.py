"""FileSqueeze - Main entry point for CLI commands."""

import argparse
import sys
from pathlib import Path


def cmd_init_config(args):
    """Generate an example configuration file with auto-detected binaries."""
    # Import here to avoid issues if config module has errors
    from filesqueeze.config import Config
    from filesqueeze.binaries import detect_binaries

    output_path = Path(args.output) if args.output else Path.cwd() / 'filesqueeze.toml'

    # If file exists and --force not specified, warn user
    if output_path.exists() and not args.force:
        print(f"Error: Configuration file already exists at {output_path}")
        print("Use --force to overwrite it, or specify a different path with --output")
        sys.exit(1)

    # Find the example config - it should be in the same directory as this file (main.py)
    # When running as module, __file__ will be in the package directory
    script_dir = Path(__file__).parent
    example_config = script_dir / 'default.toml'

    # If not found, try in the package directory
    if not example_config.exists():
        import filesqueeze
        package_dir = Path(filesqueeze.__file__).parent
        example_config = package_dir / 'default.toml'

    if not example_config.exists():
        print(f"Error: Example configuration not found")
        print(f"Searched in: {script_dir} and package directory")
        sys.exit(1)

    # Detect binaries
    print("Detecting FFmpeg, Ghostscript, and Tesseract...")
    detection = detect_binaries()

    # Read example config
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open(example_config, 'rb') as f:
        config_data = tomllib.load(f)

    # Update config with detected binary paths
    if detection['ffmpeg']['found'] and detection['ffmpeg']['path']:
        config_data['ffmpeg']['path'] = detection['ffmpeg']['path']
        print(f"  [OK] FFmpeg detected: {detection['ffmpeg']['path']}")
    else:
        print(f"  [X] FFmpeg not found - using default (PATH)")

    if detection['ghostscript']['found'] and detection['ghostscript']['path']:
        config_data['document']['ghostscript_path'] = detection['ghostscript']['path']
        print(f"  [OK] Ghostscript detected: {detection['ghostscript']['path']}")
    else:
        print(f"  [X] Ghostscript not found - using default (PATH)")

    if detection['tesseract']['found'] and detection['tesseract']['path']:
        config_data['ocr']['tesseract_path'] = detection['tesseract']['path']
        print(f"  [OK] Tesseract detected: {detection['tesseract']['path']}")
    else:
        print(f"  [X] Tesseract not found - using default (PATH)")
    print()

    # Write updated config to output location
    try:
        import tomli_w
    except ImportError:
        # If tomli_w is not available, just copy the example config
        import shutil
        shutil.copy(example_config, output_path)
        print(f"Note: tomli_w not installed, using default config without auto-detected paths")
    else:
        with open(output_path, 'wb') as f:
            tomli_w.dump(config_data, f)

    print(f"Configuration file created at: {output_path}")
    print("\nNext steps:")
    print("1. Review and edit the configuration file if needed")
    print("2. Run 'python -m filesqueeze scan' to process files")
    print("\nFor more information, see the README.md file")


def cmd_compress(args):
    """Compress a single file."""
    from filesqueeze.config import Config
    from filesqueeze import make_video, make_pdf, make_image

    # Load config
    config = Config()

    # Get input file
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: Input file does not exist: {input_file}")
        sys.exit(1)

    if not input_file.is_file():
        print(f"Error: Input is not a file: {input_file}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Generate output filename: input_compressed.ext
        output_path = input_file.parent / f"{input_file.stem}_compressed{input_file.suffix}"

    # Determine file type
    ext = input_file.suffix.lstrip('.').lower()

    print(f"Input: {input_file}")
    print(f"Output: {output_path}")
    print(f"Type: {ext.upper()}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Process file based on type
        if ext in ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv']:
            print("Compressing video...")
            result_path = make_video(str(input_file), config=config, output_path=str(output_path))
        elif ext == 'pdf':
            print("Compressing PDF...")
            result_path = make_pdf(str(input_file), config=config, output_path=str(output_path))
        elif ext in ['jpg', 'jpeg', 'png']:
            print("Compressing image...")
            result_path = make_image(str(input_file), config=config, output_path=str(output_path))
        elif ext in ['ppt', 'pptx']:
            print("Error: PowerPoint files are not yet supported")
            sys.exit(1)
        else:
            print(f"Error: Unsupported file type: {ext}")
            print("Supported types: mp4, wmv, avi, mkv, mov, flv, pdf, jpg, jpeg, png")
            sys.exit(1)

        print(f"\n[OK] Success!")
        print(f"Output: {result_path}")

        # Show file size reduction if possible
        input_size = input_file.stat().st_size
        output_size = Path(result_path).stat().st_size
        reduction = (1 - output_size / input_size) * 100

        print(f"\nFile sizes:")
        print(f"  Input:  {input_size:,} bytes ({input_size / 1024 / 1024:.2f} MB)")
        print(f"  Output: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
        if reduction > 0:
            print(f"  Saved:  {reduction:.1f}% smaller")
        else:
            print(f"  Note:  Output is larger (original may be highly compressed)")

    except Exception as e:
        print(f"\n[X] Error: {e}")
        sys.exit(1)


def cmd_scan(args):
    """Scan input directory and process files."""
    # Import here to avoid issues if modules have errors
    from filesqueeze.config import Config
    from filesqueeze.scanner import FileScanner
    from filesqueeze.output import (
        generate_output_path,
        ensure_output_dir,
        save_metadata,
        preserve_timestamps,
        get_unique_output_path
    )
    from filesqueeze import make_video, make_pdf, make_image
    import filesqueeze

    # Load config
    config = Config()

    # Override config with CLI args if specified
    input_dir = Path(args.input) if args.input else Path(config.get('directories.input', 'upload'))
    output_dir = Path(args.output) if args.output else Path(config.get('directories.output', 'compressed'))

    # Validate directories
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create scanner
    scanner = FileScanner(config)

    # Scan for files
    print(f"Scanning directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    file_count = 0
    success_count = 0
    error_count = 0

    for filepath in scanner.scan(input_dir):
        file_count += 1
        print(f"\n[{file_count}] Processing: {filepath.name}")

        try:
            # Determine file type
            ext = filepath.suffix.lstrip('.').lower()

            # Generate output path
            output_path = generate_output_path(
                filepath,
                output_dir,
                structure=config.get('output.structure', 'flat'),
                config=config
            )

            # Ensure output directory exists
            ensure_output_dir(output_path)

            # Get unique output path if file exists
            output_path = get_unique_output_path(output_path)

            # Process file based on type
            if ext in ['mp4', 'wmv', 'avi']:
                print(f"  Type: Video")
                print(f"  Output: {output_path}")
                result_path = make_video(str(filepath), config=config, output_path=str(output_path))
            elif ext == 'pdf':
                print(f"  Type: PDF")
                print(f"  Output: {output_path}")
                result_path = make_pdf(str(filepath), config=config, output_path=str(output_path))
            elif ext in ['jpg', 'jpeg', 'png']:
                print(f"  Type: Image")
                print(f"  Output: {output_path}")
                result_path = make_image(str(filepath), config=config, output_path=str(output_path))
            elif ext == 'pptx':
                print(f"  Type: PowerPoint (not yet supported)")
                print(f"  Skipping...")
                continue
            else:
                print(f"  Type: Unknown ({ext})")
                print(f"  Skipping...")
                continue

            # Save metadata if enabled
            from datetime import datetime
            save_metadata(output_path, {
                'source': str(filepath),
                'processed_at': str(datetime.now()),
            }, config=config)

            # Preserve timestamps if enabled
            preserve_timestamps(filepath, output_path, config=config)

            print(f"  [OK] Success")
            success_count += 1

        except Exception as e:
            print(f"  [X] Error: {e}")
            error_count += 1

    print("\n" + "=" * 60)
    print(f"Scan complete!")
    print(f"  Total files found: {file_count}")
    print(f"  Successfully processed: {success_count}")
    print(f"  Errors: {error_count}")
    print("=" * 60)


def cmd_detect(args):
    """Detect FFmpeg and Ghostscript binaries."""
    from filesqueeze.binaries import print_detection_results

    if args.json:
        import json
        from filesqueeze.binaries import detect_binaries
        results = detect_binaries()
        print(json.dumps(results, indent=2))
    else:
        print_detection_results()


def cmd_watch(args):
    """Watch directory for new files and compress them."""
    from filesqueeze.config import Config
    from filesqueeze.service import DirectoryWatcher

    # Load config
    config = Config()

    # Get directories
    input_dir = Path(args.input) if args.input else Path(config.get('directories.input', 'upload'))
    output_dir = Path(args.output) if args.output else Path(config.get('directories.output', 'compressed'))

    # Create watcher
    watcher = DirectoryWatcher(input_dir, output_dir, config)

    # Run watcher
    watcher.run()


def cmd_service(args):
    """Run FileSqueeze as a service with system tray icon."""
    from filesqueeze.config import Config
    from filesqueeze.tray import run_service

    # Load config
    config = Config()

    # Get directories
    input_dir = Path(args.input) if args.input else Path(config.get('directories.input', 'upload'))
    output_dir = Path(args.output) if args.output else Path(config.get('directories.output', 'compressed'))

    # Run service with tray icon
    run_service(input_dir, output_dir, config)


def cmd_service_install(args):
    """Install FileSqueeze to start automatically on boot."""
    from filesqueeze.config import Config
    from filesqueeze.autostart import install_autostart, check_autostart_installed

    # Load config
    config = Config()

    # Get directories
    input_dir = Path(args.input) if args.input else Path(config.get('directories.input', 'upload'))
    output_dir = Path(args.output) if args.output else Path(config.get('directories.output', 'compressed'))

    # Check if already installed
    if check_autostart_installed() and not args.force:
        print("Auto-start is already installed.")
        print("Use --force to reinstall.")
        sys.exit(1)

    # Install auto-start
    install_autostart(input_dir, output_dir)


def cmd_service_uninstall(args):
    """Uninstall FileSqueeze auto-start."""
    from filesqueeze.autostart import uninstall_autostart

    uninstall_autostart()


def cmd_service_status(args):
    """Show auto-start installation status."""
    from filesqueeze.autostart import check_autostart_installed, is_windows

    if not is_windows():
        print("Auto-start is only supported on Windows")
        sys.exit(1)

    if check_autostart_installed():
        print("Auto-start is installed")
        print("FileSqueeze will start automatically when you log in to Windows.")
    else:
        print("Auto-start is not installed")
        print("To install, run: python -m filesqueeze service-install")


def main():
    """Main entry point for FileSqueeze CLI."""
    parser = argparse.ArgumentParser(
        description="FileSqueeze - Compress videos, PDFs, and images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m filesqueeze init-config             Create example config file
  python -m filesqueeze detect                  Detect FFmpeg and Ghostscript binaries
  python -m filesqueeze scan                    Process all files
  python -m filesqueeze scan --input . --output ./compressed
  python -m filesqueeze watch                   Monitor directory for new files
  python -m filesqueeze service                 Run with system tray icon
  python -m filesqueeze status                  Show queue status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # compress command
    compress_parser = subparsers.add_parser(
        'compress',
        help='Compress a single file'
    )
    compress_parser.add_argument(
        'input',
        help='Input file to compress'
    )
    compress_parser.add_argument(
        '--output', '-o',
        help='Output file path (default: <input>_compressed.<ext>)'
    )

    # init-config command
    init_parser = subparsers.add_parser(
        'init-config',
        help='Generate an example configuration file'
    )
    init_parser.add_argument(
        '--output', '-o',
        help='Output path for config file (default: ./filesqueeze.toml)'
    )
    init_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing configuration file'
    )

    # scan command
    scan_parser = subparsers.add_parser(
        'scan',
        help='Process files in input directory'
    )
    scan_parser.add_argument(
        '--input', '-i',
        help='Input directory to scan (default: from config or ./upload)'
    )
    scan_parser.add_argument(
        '--output', '-o',
        help='Output directory for compressed files (default: from config or ./compressed)'
    )

    # watch command
    watch_parser = subparsers.add_parser(
        'watch',
        help='Watch directory for new files and compress them'
    )
    watch_parser.add_argument(
        '--input', '-i',
        help='Input directory to watch (default: from config or ./upload)'
    )
    watch_parser.add_argument(
        '--output', '-o',
        help='Output directory for compressed files (default: from config or ./compressed)'
    )

    # service command
    service_parser = subparsers.add_parser(
        'service',
        help='Run FileSqueeze as a service with system tray icon'
    )
    service_parser.add_argument(
        '--input', '-i',
        help='Input directory to watch (default: from config or ./upload)'
    )
    service_parser.add_argument(
        '--output', '-o',
        help='Output directory for compressed files (default: from config or ./compressed)'
    )

    # service-install command
    service_install_parser = subparsers.add_parser(
        'service-install',
        help='Install FileSqueeze to start automatically on boot'
    )
    service_install_parser.add_argument(
        '--input', '-i',
        help='Input directory to watch (default: from config or ./upload)'
    )
    service_install_parser.add_argument(
        '--output', '-o',
        help='Output directory for compressed files (default: from config or ./compressed)'
    )
    service_install_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Reinstall if already installed'
    )

    # service-uninstall command
    subparsers.add_parser(
        'service-uninstall',
        help='Uninstall FileSqueeze auto-start'
    )

    # service-status command
    subparsers.add_parser(
        'service-status',
        help='Show auto-start installation status'
    )

    # detect command
    detect_parser = subparsers.add_parser(
        'detect',
        help='Detect FFmpeg and Ghostscript binaries'
    )
    detect_parser.add_argument(
        '--json',
        action='store_true',
        help='Output detection results as JSON'
    )

    # For backward compatibility, also support --init-config as a flag
    parser.add_argument(
        '--init-config',
        dest='init_config_flag',
        action='store_true',
        help='Generate an example configuration file (same as init-config command)'
    )
    # Additional arguments that can be used with --init-config flag
    parser.add_argument(
        '--output', '-o',
        help='Output path for config file (when using --init-config)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing configuration file (when using --init-config)'
    )

    # Other commands will be added in future phases
    # scan_parser = subparsers.add_parser('scan', help='Process files in input directory')
    # watch_parser = subparsers.add_parser('watch', help='Monitor directory for new files')
    # service_parser = subparsers.add_parser('service', help='Run as background service')
    # status_parser = subparsers.add_parser('status', help='Show queue status')

    # Legacy mode: if no command specified, treat first positional arg as input file
    parser.add_argument(
        'infile',
        nargs='?',
        help='Input file or directory (legacy mode)'
    )

    args = parser.parse_args()

    # Handle --init-config flag
    if args.init_config_flag:
        # Create a namespace object with the init-config args
        class InitConfigArgs:
            def __init__(self, output, force):
                self.output = output
                self.force = force
        init_args = InitConfigArgs(args.output, args.force)
        return cmd_init_config(init_args)

    # Handle commands
    if args.command == 'compress':
        return cmd_compress(args)

    if args.command == 'init-config':
        return cmd_init_config(args)

    if args.command == 'scan':
        return cmd_scan(args)

    if args.command == 'watch':
        return cmd_watch(args)

    if args.command == 'service':
        return cmd_service(args)

    if args.command == 'service-install':
        return cmd_service_install(args)

    if args.command == 'service-uninstall':
        return cmd_service_uninstall(args)

    if args.command == 'service-status':
        return cmd_service_status(args)

    if args.command == 'detect':
        return cmd_detect(args)

    # Legacy mode: if infile is specified, use old behavior
    if args.infile:
        print("Warning: Legacy mode is deprecated. Use --scan command instead.")
        print(f"Processing: {args.infile}")
        # TODO: Implement legacy mode
        print("Error: Legacy mode not yet implemented. Use --init-config to set up configuration first.")
        sys.exit(1)

    # No command specified
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
