# K8 Site Builder Migration (SBM) Guide

## Overview

This comprehensive guide covers the complete Front-End Development (FED) process for migrating dealer websites to Site Builder, including detailed styling standards, automation integration, and best practices.

---

## 1. Initial Setup & Branching

### Create a Staging Branch

```bash
# Create branch using standard naming convention
git checkout -b dealerslug-sbMMYY
# Example: bmwseattle-sb1024, chryslerportland-sb1124

# Required empty commit before pushing
git commit --allow-empty -m 'Starting sitebuilder work'

# Push to remote
git push origin your-branch-name
```

### Start the Migration

```bash
# Initialize the branch (required step)
just start your-branch-name
```

---

## 2. Theme & Asset Migration

### Core Style Migration Pattern

**Primary File Migration:**

- **lvdp.scss** → **sb-vdp.scss** (Vehicle Detail Page styles)
- **lvrp.scss** → **sb-vrp.scss** (Vehicle Results Page styles)
- **inside.scss** → **sb-inside.scss** (Custom/internal page styles)
- **style.scss** → Audit and distribute to appropriate SB files

### Site Builder File Structure

```
dealer-themes/dealername/
├── sb-inside.scss    # General site styles + map components
├── sb-vdp.scss       # Vehicle Detail Page styles
├── sb-vrp.scss       # Vehicle Results Page styles
├── sb-home.scss      # Homepage specific styles (if needed)
└── css/
    ├── _variables.scss  # All variables
    ├── home.scss       # Legacy homepage styles
    ├── inside.scss     # Legacy inner page styles
    ├── lvdp.scss       # Legacy VDP
    ├── lvrp.scss       # Legacy VRP
    └── style.scss      # Global styles
```

### Brand-Specific Requirements

**Stellantis Dealers (Chrysler, Dodge, Jeep, RAM):**

- ✅ **Map Components**: Add directions row and map styles to `sb-inside.scss`
- ✅ **Cookie Consent Banner**: Use provided CSS/SCSS snippets for `sb-inside.scss` and `sb-home.scss`

**Other Brands:**

- Check for brand-specific style requirements
- Document any unique "gotchas" in PR description

### Scripts & Templates Migration

**JavaScript:**

- Check `custom.js` for scripts that need to be moved to DITM
- Audit and migrate any `support-requests.scss` styles as needed

**Templates & Partials:**

- Migrate partials (e.g., Shop By Price) and custom templates
- Adapt templates as necessary for SiteBuilder compatibility
- Ensure all custom functionality is preserved

---

## 3. Site Builder Styling Standards

### Variables & CSS Custom Properties

**Always use CSS variables for colors and key properties:**

```scss
// In _variables.scss
$primary: var(--primary, #093382) !default;
$secondary: var(--secondary, #e74c3c) !default;
$cta: var(--cta, #00bcd4) !default;
$primaryhover: var(--primaryhover, #002266) !default;

// Usage in components
.button {
  background-color: $primary;
  color: $white;
  &:hover {
    background-color: $primaryhover;
  }
}
```

**Override for specific OEM or site:**

```scss
:root {
  --primary: #ff0000;
}
```

### Mixin Replacement

**Replace all mixins with CSS equivalents:**

| Old Mixin                                  | Site Builder CSS                  |
| ------------------------------------------ | --------------------------------- |
| `@include flexbox();`                      | `display: flex;`                  |
| `@include flex-direction(row);`            | `flex-direction: row;`            |
| `@include align-items(center);`            | `align-items: center;`            |
| `@include justify-content(space-between);` | `justify-content: space-between;` |
| `@include transition(all 0.3s);`           | `transition: all 0.3s;`           |
| `@include border-radius(4px);`             | `border-radius: 4px;`             |

#### Complete CommonTheme Mixin Reference

**1. Positioning Mixins**

```scss
// Old
.item {
  @include absolute(
    (
      top: 0,
      left: 0,
    )
  );
}
.center {
  @include centering(both);
}

// Site Builder
.item {
  position: absolute;
  top: 0;
  left: 0;
}
.center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
```

**2. Flexbox Mixins**

```scss
// Old
.container {
  @include flexbox;
  @include flex-direction(row);
  @include flex-wrap(wrap);
  @include align-items(center);
  @include justify-content(space-between);
}

// Site Builder
.container {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
}
```

**3. Gradients**

```scss
// Old
.bg {
  @include gradient(#fff, #000);
}
.bg-lr {
  @include gradient-left-right(#fff, #000);
}

// Site Builder
.bg {
  background: linear-gradient(to bottom, #fff, #000);
}
.bg-lr {
  background: linear-gradient(to right, #fff, #000);
}
```

**4. Font & Responsive Typography**

```scss
// Old
h2 {
  @include responsive-font(4vw, 30px, 100px);
}
.text {
  @include font_size(18);
}

// Site Builder
h2 {
  font-size: clamp(30px, 4vw, 100px);
}
.text {
  font-size: 18px;
}
```

**5. Placeholder Styling**

```scss
// Old
input {
  @include placeholder-color;
}

// Site Builder
input::placeholder {
  color: $placeholder-color;
}
input::-webkit-input-placeholder {
  color: $placeholder-color;
}
input::-moz-placeholder {
  color: $placeholder-color;
}
```

**6. Z-Index**

```scss
// Old
.modal {
  @include z-index('modal');
}
.overlay {
  @include z-index('overlay', -200);
}

// Site Builder
.modal {
  z-index: 1000; /* Use specific values */
}
.overlay {
  z-index: 800;
}
```

**7. Transform & Transition**

```scss
// Old
.spin {
  @include rotate(45deg);
}
.fade {
  @include transition(all 0.3s);
}
.move {
  @include transform(translateX(10px));
}

// Site Builder
.spin {
  transform: rotate(45deg);
}
.fade {
  transition: all 0.3s;
}
.move {
  transform: translateX(10px);
}
```

**8. List Padding**

```scss
// Old
ul {
  @include list-padding(left, 20px);
}

// Site Builder
ul {
  padding-left: 20px;
}
```

**9. Appearance**

```scss
// Old
select {
  @include appearance(none);
}

// Site Builder
select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}
```

**10. Box Model & Border**

```scss
// Old
.card {
  @include border-radius(8px);
  @include box-shadow(0 2px 4px #0002);
  @include box-sizing(border-box);
}

// Site Builder
.card {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  box-sizing: border-box;
}
```

**11. Breakpoints (Media Queries)**

```scss
// Old
@include breakpoint('md') {
  .element {
    font-size: 1.2rem;
  }
}

// Site Builder
@media (min-width: 768px) {
  .element {
    font-size: 1.2rem;
  }
}
```

**12. Utility & Animation**

```scss
// Old
.clearfix {
  @include clearfix;
}
.animate {
  @include animation('fade-in 1s');
}
.filtered {
  @include filter(blur(5px));
}

// Site Builder
.clearfix::after {
  content: '';
  display: table;
  clear: both;
}
.animate {
  animation: fade-in 1s;
}
.filtered {
  filter: blur(5px);
}
```

**13. Functions**

```scss
// Old
.text {
  font-size: em(22);
}
.mobile {
  width: get-mobile-size(300px);
}

// Site Builder
.text {
  font-size: 1.375rem; /* 22px / 16px */
}
.mobile {
  width: 300px; /* Use specific values or CSS calc() */
}
```

**14. Visually Hidden (Screen Reader Only)**

```scss
// Old
.sr-only {
  @include visually-hidden();
}

// Site Builder
.sr-only {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  border: 0 !important;
}
```

### Responsive Breakpoints

**Use standard breakpoints:**

```scss
// Mobile first approach
.element {
  font-size: 1rem;
}

// Tablet
@media (min-width: 768px) {
  .element {
    font-size: 1.2rem;
  }
}

// Desktop
@media (min-width: 1024px) {
  .element {
    font-size: 1.4rem;
  }
}
```

### File Paths & URLs

**Always update image paths:**

```scss
// Old
background-image: url('../images/bg.jpg');

// Site Builder
background-image: url('/wp-content/themes/DealerInspireDealerTheme/images/bg.jpg');
```

### Styling Best Practices

- ✅ **Never use hardcoded hex values** - always use variables
- ✅ **Replace all mixins** with CSS equivalents
- ✅ **Use standard breakpoints** (768px, 1024px)
- ✅ **Update all file paths** to start with `/wp-content/`
- ✅ **Import variables** at the top of SCSS files
- ❌ **Never use Font Awesome** for SVGs
- ❌ **Never start custom styles with `@`** in Site Builder's STYLES tab

---

## 4. Plugin & Content Migration

### Plugin Management

```bash
# Copy plugins from live site to dev site
# Audit plugin versions - ensure correct versioning
# Example: DI Jumpto Plugin should be "_" not "1._"

# Save changes to composer.json
git add composer.json
git commit -m "Update plugin versions for SiteBuilder compatibility"
```

### Content & Assets

- ✅ Copy all images and assets to `Dealer Theme/images/` folder
- ✅ Audit for missing or broken images after migration
- ✅ Verify all asset paths are correct in SiteBuilder context
- ✅ Update image URLs to use `/wp-content/` paths

---

## 5. Testing & Quality Assurance

### Local Testing Checklist

- [ ] **Homepage** loads without errors
- [ ] **VRP** (Vehicle Results Page) functions correctly
- [ ] **VDP** (Vehicle Detail Page) displays properly
- [ ] **Inner pages** load and display correctly
- [ ] **Map functionality** works (especially for Stellantis)
- [ ] **Mobile responsiveness** at 768px and 1024px breakpoints
- [ ] **CSS variables** compile correctly
- [ ] **Image paths** resolve properly

### Automated Testing Tools

```bash
# Use Screaming Frog for broken link checks
# Use SSL Auditor for comprehensive link audits
```

### Create Pull Request

**PR Requirements:**

- [ ] Use the standard PR template
- [ ] Clearly describe what was changed
- [ ] Note if map partials, styles, or non-standard items were migrated
- [ ] Add `carsdotcom-fe-dev` as reviewers
- [ ] Label as `fe-dev`
- [ ] Link PR in Salesforce
- [ ] Update Website Record status: Queue → Doing → Done

**PR Title Format:**

```
[Dealer Name] SBM FE Audit
```

---

## 6. Staging & Handoff

### Deploy to Staging

```bash
# Use GitHub Actions → Deploy Branch workflow
# This creates a staging link for testing
```

### Style Regeneration

```bash
# Regenerate styles on staging if needed
just regen-sb-css-staging
```

### Timeline Requirements

- ✅ **Sign off on staging testing by 4pm CST on Day 2**
- ✅ Notify ProdDev when FE migration is complete

---

## 7. Automation Integration

### SBM Tool V2 Integration

For supported dealers (especially Stellantis), use the SBM automation tool:

```bash
# Check if dealer is supported
python -m sbm validate dealerslug

# Run automated migration (dry run first)
python -m sbm migrate dealerslug --dry-run

# Run actual migration
python -m sbm migrate dealerslug
```

**Automation Benefits:**

- Automatically creates the 3 core SB files (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)
- Uses correct responsive breakpoints (768px, 1024px)
- Applies proper CSS variable patterns
- Adds standard map components for Stellantis dealers
- Follows Site Builder styling standards
- Saves 15-30 minutes per migration

**What the Automation Handles:**

- ✅ File structure creation
- ✅ Standard map components with correct breakpoints
- ✅ CSS variable usage
- ✅ Proper file headers
- ✅ Brand detection (Stellantis)
- ✅ Legacy style extraction patterns

---

## 8. Troubleshooting & Hotfixes

### Discard Uncommitted Changes

```bash
git add .
git status
git stash
```

### Merge Main to Staging for Hotfixes

```bash
git checkout main
git pull origin main
git checkout <your-sb-branch>
git rebase main
git push origin <your-sb-branch>
# Then redeploy via GitHub Actions
```

---

## 9. Pre-Launch & Post-Launch

### Pre-Launch QC Checklist

- [ ] Homepage QC complete
- [ ] VRP QC complete
- [ ] VDP QC complete
- [ ] Inner pages QC complete
- [ ] Screaming Frog audit passed
- [ ] SSL Auditor check passed
- [ ] Mobile responsiveness verified at standard breakpoints
- [ ] Map functionality tested (Stellantis)
- [ ] CSS variables compiling correctly
- [ ] Image paths working properly

### Handoff Process

1. Move site to **Done** in Dev View board
2. Notify ProdDev that FE migration is complete
3. Provide any special notes or requirements

### Post-Launch

- Follow up with additional steps per post-launch workflow
- Monitor for any issues in first 24-48 hours
- Document any lessons learned

---

## 10. Advanced Styling Examples

### Button Styling with Variables

```scss
.button {
  background-color: $primary;
  color: $white;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  border: none;
  transition: background 0.2s;

  &:hover {
    background-color: $primaryhover;
  }
}
```

### Responsive Map Components (Stellantis)

```scss
/* MAP ROW */
#mapRow {
  position: relative;

  .mapwrap {
    height: 600px;
  }
}

#map-canvas {
  height: 100%;
}

/* DIRECTIONS BOX */
#directionsBox {
  padding: 50px 0;
  text-align: left;
  width: 400px;
  position: absolute;
  top: 200px;
  left: 50px;
  background: $white;
  color: $black;
  font-family: 'Lato', sans-serif;
}

// Standard responsive breakpoints
@media (min-width: 768px) {
  #mapRow .mapwrap {
    height: 400px;
  }
}

@media (min-width: 1024px) {
  #mapRow .mapwrap {
    height: 600px;
  }

  #directionsBox {
    max-width: 45%;
  }
}
```

### Custom Variables for Brands

```scss
:root {
  --subaru-blue: #0033a0;
  --subaru-light-blue: #6ec1e4;
  --subaru-dark-blue: #002244;
}

.subaru-banner {
  background: var(--subaru-blue);
  color: var(--white);
}
```

---

## 11. Special FED Considerations

### Always Check For:

- ✅ **Cookie consent** styles migration
- ✅ **Map components** with correct breakpoints (768px, 1024px)
- ✅ **CSS variable usage** instead of hardcoded values
- ✅ **Mixin replacement** with CSS equivalents
- ✅ **Image path updates** to `/wp-content/` format
- ✅ **Brand-specific requirements**

### Documentation Requirements:

- Document any brand-specific "gotchas"
- Note any non-standard migrations in PR
- Ensure all custom scripts, templates, and partials are adapted for SiteBuilder
- List any custom variables created

---

## 12. Success Criteria

A successful SBM migration includes:

- ✅ All styles properly migrated to SiteBuilder files
- ✅ CSS variables used throughout (no hardcoded values)
- ✅ All mixins replaced with CSS equivalents
- ✅ Standard responsive breakpoints implemented (768px, 1024px)
- ✅ Image paths updated to `/wp-content/` format
- ✅ No broken functionality on any page type
- ✅ Brand-specific requirements implemented
- ✅ Clean, well-documented PR
- ✅ Successful staging deployment and testing
- ✅ Smooth handoff to ProdDev

---

## 13. Reference Links

- [Site Builder Variable Overrides (full list)](https://dealerinspire.atlassian.net/wiki/spaces/PLAT/pages/1611924179/Variable+Overrides#Colors)
- [Styling Site Builder Websites](https://carscommerce.atlassian.net/wiki/spaces/DGP/pages/2945483314/Always+leverage+Sass+variables+and+CSS+variables+for+colors)
- [Site Builder Theme Style Guide Template](https://dealerinspire.atlassian.net/wiki/spaces/PLAT/pages/1611924179/Variable+Overrides#Colors)
- [Site Builder Cheat Sheet](https://carscommerce.atlassian.net/wiki/spaces/POMT/pages/3408036048/Site+Builder+Cheat+Sheet)

---

_This comprehensive guide covers all major FED responsibilities and best practices for a Site Builder migration, ensuring a smooth handoff and successful launch while following proper Site Builder styling standards._
