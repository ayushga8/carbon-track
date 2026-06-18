"""
Vercel build hook — runs collectstatic during deployment.
This file is automatically executed by @vercel/python during build.
"""
import subprocess
import sys

def build():
    """Collect static files for WhiteNoise to serve."""
    subprocess.run(
        [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
        check=True,
    )

if __name__ == '__main__':
    build()
