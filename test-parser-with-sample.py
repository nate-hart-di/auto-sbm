#!/usr/bin/env python3

import os
import sys
import re
from sbm.utils.logger import setup_logger, logger

# Set up logger
logger = setup_logger(level="DEBUG")

# Import the parse_style_rules and distribute_rules functions from our improved parser
from improved_style_parser import parse_style_rules, distribute_rules

# Read the test file
test_file = os.path.join(os.path.dirname(__file__), "test-sample-style.scss")
with open(test_file, 'r') as f:
    content = f.read()

logger.info(f"Parsing test file: {test_file}")
logger.info(f"File contains {len(content.splitlines())} lines")

# Parse the style rules
rules = parse_style_rules(content)

# Count rules by category
counts = {'vdp': 0, 'vrp': 0, 'inside': 0}
for rule in rules:
    counts[rule['category']] += 1
    logger.info(f"Rule categorized as {rule['category']}: {rule['rule'].splitlines()[0].strip()[:60]}...")

logger.info(f"Found {len(rules)} total style rules")
logger.info(f"  - VDP rules: {counts['vdp']}")
logger.info(f"  - VRP rules: {counts['vrp']}")
logger.info(f"  - Inside rules: {counts['inside']}")

# Distribute rules to appropriate files
categorized = distribute_rules(rules)

# Create output directory if it doesn't exist
os.makedirs("test-output", exist_ok=True)

# Write to output files
with open("test-output/sb-vdp.scss", 'w') as f:
    f.write(categorized['vdp'])

with open("test-output/sb-vrp.scss", 'w') as f:
    f.write(categorized['vrp'])

with open("test-output/sb-inside.scss", 'w') as f:
    f.write(categorized['inside'])

logger.info("Saved categorized styles to test-output/ directory")
