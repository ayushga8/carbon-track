#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Copy static files to the build output directory
mkdir -p staticfiles_build/static
cp -r staticfiles/* staticfiles_build/static/
