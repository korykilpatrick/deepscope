#!/bin/bash
# get_tree.sh – generate a project tree excluding config files/folders and docs

# Change to the project root (assumes this script lives in the scripts/ directory)
cd "$(dirname "$0")/.."

# Run tree while ignoring common config files and docs; output to project_tree.txt
tree -I "docs|venv|config|scripts|README.md|LICENSE|project_tree.txt|__pycache__|*.pyc" > project_tree.txt

echo "Project tree generated in project_tree.txt"