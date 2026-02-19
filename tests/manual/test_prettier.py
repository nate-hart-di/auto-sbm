import logging
from sbm.scss.formatter import format_all_scss_files

logging.basicConfig(level=logging.DEBUG)
slug = "lexusofkendall"
theme_dir = f"/Users/nathanhart/di-websites-platform/dealer-themes/{slug}"

print("Formatting SCSS files...")
format_all_scss_files(theme_dir)
