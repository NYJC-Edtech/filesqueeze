"""FileSqueeze - Main entry point for CLI commands."""

import argparse
import sys
from pathlib import Path


def cmd_init_config(args):
    """Generate an example configuration file."""
    # Import here to avoid issues if config module has errors
    from filesqueeze.config import Config

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

    # Copy example config to output location
    import shutil
    shutil.copy(example_config, output_path)

    print(f"Configuration file created at: {output_path}")
    print("\nNext steps:")
    print("1. Edit the configuration file to customize your settings")
    print("2. Run 'python -m filesqueeze --scan' to process files")
    print("\nFor more information, see the README.md file")


def main():
    """Main entry point for FileSqueeze CLI."""
    parser = argparse.ArgumentParser(
        description="FileSqueeze - Compress videos, PDFs, and images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m filesqueeze --init-config           Create example config file
  python -m filesqueeze --scan                  Process all files
  python -m filesqueeze --scan --input . --output ./compressed
  python -m filesqueeze --watch                 Monitor directory for new files
  python -m filesqueeze --service               Run with system tray icon
  python -m filesqueeze --status                Show queue status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # --init-config command
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
    if args.command == 'init-config':
        return cmd_init_config(args)

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
