## What

Added interior page styles to sb-inside.scss

- Migrated sitemap styles
- Added menu item styles
- Integrated map component styles
- Added cookie banner styles

Added VDP styles to sb-vdp.scss
Added VRP styles to sb-vrp.scss

## Why

Site Builder Migration

## Instructions for Reviewers

Within the di-websites-platform directory:

```bash
git checkout main
git pull
git checkout BRANCH_NAME
just start DEALER_SLUG prod
```

- Review all code found in "Files Changed"
- Open up a browser, go to localhost
- Verify that homepage and interior pages load properly
- Request changes as needed
