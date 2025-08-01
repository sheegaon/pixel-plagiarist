#!/usr/bin/env python3
"""
Generate Secure Secret Key for Pixel Plagiarist
Utility script to generate a cryptographically secure SECRET_KEY for Flask applications.
"""

import secrets


def generate_secret_key():
    """Generate a cryptographically secure secret key."""
    return secrets.token_hex(32)  # 64-character hex string


def main():
    """Generate and display a new secret key with usage instructions."""
    key = generate_secret_key()

    print("🔐 Generated Secure Secret Key for Pixel Plagiarist")
    print("=" * 60)
    print(f"SECRET_KEY: {key}")
    print("=" * 60)
    print("\n📋 Usage Instructions:")
    print("\n1. For Local Development:")
    print("   Keep the current hardcoded key in server.py")
    print("\n2. For Production Deployment:")
    print("   Set this as an environment variable:")
    print(f"   export SECRET_KEY='{key}'")
    print("\n3. For Heroku:")
    print(f"   heroku config:set SECRET_KEY='{key}'")
    print("\n⚠️  Security Notes:")
    print("   - Never commit this key to version control")
    print("   - Generate a new key for each environment")
    print("   - Store securely in your deployment system")
    print("   - Changing the key will invalidate all active sessions")


if __name__ == "__main__":
    main()
