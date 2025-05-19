## What

- Migrated interior page styles from inside.scss and style.scss to sb-inside.scss
- Migrated LVRP, LVDP Styles to sb-lvrp.scss and sb-lvdp.scss
- Added FCA Direction Row Styles
- Added FCA Cookie Banner styles

## Why

Site Builder Migration

## Instructions for Reviewers

Within the di-websites-platform directory:

```bash
git checkout main
git pull
git checkout spitzermotorsofmansfieldcdjr-sbm0525
just start spitzermotorsofmansfieldcdjr prod
```

- Review all code found in "Files Changed"
- Open up a browser, go to localhost
- Verify that homepage and interior pages load properly
- Request changes as needed
