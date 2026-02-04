"""
Command-line interface for xswl-yaml-nsis
"""

import argparse
import sys
import os
import subprocess
from .config import PackageConfig
from .converter import YamlToNsisConverter


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="xswl-yaml-nsis: Convert YAML configuration to NSIS installer script"
    )
    parser.add_argument(
        "config",
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output NSIS script path (default: <config_dir>/installer.nsi)",
        default=None
    )
    parser.add_argument(
        "-b", "--build",
        action="store_true",
        help="Build installer using makensis after generating script"
    )
    parser.add_argument(
        "--makensis",
        help="Path to makensis executable (default: makensis)",
        default="makensis"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file '{args.config}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    if args.output is None:
        config_dir = os.path.dirname(os.path.abspath(args.config))
        args.output = os.path.join(config_dir, "installer.nsi")
    
    try:
        # Load configuration
        if args.verbose:
            print(f"Loading configuration from {args.config}...")
        config = PackageConfig.from_yaml(args.config)
        
        # Convert to NSIS
        if args.verbose:
            print(f"Converting YAML to NSIS script...")
        converter = YamlToNsisConverter(config)
        
        # Save NSIS script
        if args.verbose:
            print(f"Saving NSIS script to {args.output}...")
        converter.save(args.output)
        
        print(f"✓ Generated NSIS script: {args.output}")
        
        # Build installer if requested
        if args.build:
            if args.verbose:
                print(f"Building installer with {args.makensis}...")
            
            # Check if makensis is available
            try:
                result = subprocess.run(
                    [args.makensis, args.output],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if args.verbose:
                    print(result.stdout)
                
                installer_name = f"{config.app.name}-{config.app.version}-Setup.exe"
                print(f"✓ Built installer: {installer_name}")
                
            except FileNotFoundError:
                print(f"Error: makensis not found. Please install NSIS or specify path with --makensis", file=sys.stderr)
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                print(f"Error building installer:", file=sys.stderr)
                print(e.stderr, file=sys.stderr)
                sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
