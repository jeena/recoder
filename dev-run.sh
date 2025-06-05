#!/bin/bash

# Compile resources
glib-compile-resources src/resources/resources.xml \
    --target=src/recoder/resources.gresource \
    --sourcedir=src/resources

# Compile GSettings schemas (using correct path)
glib-compile-schemas src/resources

# Run the app with environment variables
GSETTINGS_SCHEMA_DIR=$(pwd)/src/resources \
PYTHONPATH=$(pwd)/src \
python -m recoder.app
