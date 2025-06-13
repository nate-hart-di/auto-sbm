Certainly! Here is the extremely detailed migration guide in Markdown (.md) format:

# Step 3: SiteBuilder Migration – EXTREMELY DETAILED GUIDE

## 3.1. Preparation

- **Ensure you are on the correct branch:**
  ```bash
  git checkout main
  git pull
  git checkout -b {slug}-SBM{MMYY}
  just start {slug}
  Replace {slug} with the dealer slug (e.g., bmwseattle).
  ```

Replace {MMYY} with the migration month and year (e.g., 0625 for June 2025).

3.2. Migrating Styles
3.2.1. Copy Styles from Legacy Files
lvdp → sb-vdp.scss

Source: dealer-themes/{slug}/css/lvdp.scss

Destination: dealer-themes/{slug}/css/sb-vdp.scss

Copy all relevant styles unless they are OEM-specific.

lvrp → sb-vrp.scss

Source: dealer-themes/{slug}/css/lvrp.scss

Destination: dealer-themes/{slug}/css/sb-vrp.scss

Copy all relevant styles unless they are OEM-specific.

style.scss → sb-vrp.scss, sb-vdp.scss, sb-inside.scss

Source: dealer-themes/{slug}/css/style.scss

Destination:

Inventory/Results: sb-vrp.scss

Inventory/Details: sb-vdp.scss

Internal/Custom pages: sb-inside.scss

Audit each style block and move only those still needed for inventory or internal pages. Ignore homepage, header, or footer styles unless specifically required (e.g., third-party rows like Roadster).

inside or styles → sb-inside.scss

Source: dealer-themes/{slug}/css/inside.scss or dealer-themes/{slug}/css/styles.scss

Destination: dealer-themes/{slug}/css/sb-inside.scss

Copy custom template styles for internal pages.

support-requests.scss

If present, audit and move any relevant styles to the appropriate sb-\*.scss file.

3.2.2. Adapt and Refactor Styles
Update file paths for images and assets:

Change relative paths like ../images/image.jpg to absolute WordPress paths:

/wp-content/themes/DealerInspireDealerTheme/images/image.jpg
Convert SCSS variables and mixins to CSS custom properties:

$primary → var(--primary)

$secondary → var(--secondary)

$cta → var(--cta)

$primaryhover → var(--primaryhover)

$secondaryhover → var(--secondaryhover)

$ctahover → var(--ctahover)

Replace SCSS functions and mixins:

@include flexbox(); → display: flex;

Replace darken($color, 10%) with the actual hex value (use a color tool to calculate).

Remove or replace font family variables with explicit values.

Remove unused or homepage-only styles unless specifically required.

3.2.3. Special Styles
Stellantis US:

Add required FCA styles to sb-inside.scss as documented
Site Builder Migrations - FE Audit Things.

Cookie Consent Banner:

If not already present, add banner styles to both sb-inside.scss and sb-home.scss.

3.3. Migrating Templates and Scripts
3.3.1. Custom Templates
Copy custom template files (if used for internal pages):

Source: dealer-themes/{slug}/templates/inside/

Destination: dealer-themes/{slug}/templates/sb-inside/

Ensure only templates still in use are migrated. For OEMs like Porsche, skip unused templates unless dealership still uses them.

3.3.2. JavaScript Migration
custom.js → ditm

Source: dealer-themes/{slug}/js/custom.js

Destination: dealer-themes/{slug}/js/ditm.js

Audit for scripts still needed on inventory or internal pages. Migrate only those scripts. Remove or refactor any scripts that are obsolete or homepage-only.

3.4. Migrating Functions and Shortcodes
3.4.1. Shortcodes (e.g., [full-map])
Check all functions files for shortcodes like [full-map]:

Look in dealer-themes/{slug}/functions.php and any included/shared function files.

If found, note the template part path (e.g., partials/dealer-groups/bmw-oem/map-row-1).

Recreate directory structure in DealerTheme:

Example:

If the shortcode references partials/dealer-groups/bmw-oem/map-row-1.php in CommonTheme, create the same path in DealerTheme:

dealer-themes/{slug}/partials/dealer-groups/bmw-oem/map-row-1.php
Copy the file contents from CommonTheme to the new location.

Migrate associated styles:

Check style.scss or CommonTheme for any related SCSS (e.g., \_map-row-1.scss).

Copy these styles into sb-inside.scss.

3.5. Quality Control and Best Practices
After each migration step:

Run git status to verify only your site’s files are modified.

Test locally using just start {slug} and verify all migrated pages render correctly.

Check for missing assets, broken styles, or JavaScript errors.

Commit changes:

git add .
git commit -m "{DealerName} SBM FE Audit"
git push origin {slug}-SBM{MMYY}
Create a Pull Request and fill out the PR template with details of what was migrated, why, and instructions for reviewers.

3.6. Edge Cases and OEM-Specific Notes
OEM-specific styles: Only migrate if the site is for that OEM.

Unused templates: Skip unless dealership still uses them (e.g., Porsche’s about, service, lightning inventory pages).

Translations: If .po files are used for translations, audit and migrate as needed.

Homepage/third-party rows: Only migrate if specifically required (e.g., Roadster).

3.7. Summary Table of File Migrations
Source File/Folder

Destination File/Folder

Notes

css/lvdp.scss

css/sb-vdp.scss

Inventory details styles

css/lvrp.scss

css/sb-vrp.scss

Inventory results styles

css/style.scss

css/sb-vrp.scss, sb-vdp.scss, sb-inside.scss

Audit and split as needed

css/inside.scss or css/styles.scss

css/sb-inside.scss

Internal/custom page styles

css/support-requests.scss

css/sb-\*.scss

Audit and move relevant styles

js/custom.js

js/ditm.js

Only scripts still needed

functions.php (shortcodes)

partials/... in DealerTheme

Recreate structure, migrate PHP and styles

CommonTheme SCSS (e.g., \_map-row-1.scss)

css/sb-inside.scss

For map/directions rows

Following this process ensures a clean, maintainable migration and minimizes the risk of breaking site functionality.
If you need this in a machine-readable format (e.g., JSON or YAML), let me know!
