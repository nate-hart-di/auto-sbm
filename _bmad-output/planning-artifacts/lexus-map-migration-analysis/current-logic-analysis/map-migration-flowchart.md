# Map Migration Flowchart

```mermaid
flowchart TD
    Start([Start: migrate_map_components]) --> CheckStyle{style.scss exists?}
    CheckStyle -- No --> EndNoStyle([Exit: No style.scss])
    CheckStyle -- Yes --> ScanImports[Scan style.scss for Imports]

    ScanImports --> CheckOEM{Has OEM Handler?}
    CheckOEM -- Yes --> UseOEMPatterns[Use OEM Patterns]
    CheckOEM -- No --> UseGenericKeywords[Use Generic Keywords]

    UseOEMPatterns --> FindImports[Find CommonTheme Imports]
    UseGenericKeywords --> FindImports

    FindImports --> ScanFunctions[Scan functions.php & Includes]
    ScanFunctions --> FindShortcodes[Find 'full-map' Shortcodes]
    ScanFunctions --> FindPartials[Find get_template_part calls]

    FindShortcodes --> DeriveSCSS[Derive SCSS from Shortcode Partials]
    DeriveSCSS --> MergeImports[Merge & Dedupe Imports]

    MergeImports --> CheckFound{Components Found?}
    CheckFound -- No --> EndNone([Exit: none_found])
    CheckFound -- Yes --> SCSSMigration[Phase: SCSS Migration]

    SCSSMigration --> FilterSCSS{Source?}
    FilterSCSS -- "Explicit (in style.scss)" --> SkipExplicit[Skip (Handled by Inline)]
    FilterSCSS -- "Implicit (Derived)" --> CheckPresent{Already in sb-inside?}

    CheckPresent -- Yes --> LogSkipSCSS[Log: Already Present]
    CheckPresent -- No --> ReadContent[Read CommonTheme SCSS]
    ReadContent --> Transform[SCSSProcessor Transform]
    Transform --> AppendSCSS[Append to sb-inside.scss & sb-home.scss]

    SkipExplicit --> PartialMigration
    LogSkipSCSS --> PartialMigration
    AppendSCSS --> PartialMigration[Phase: Partial Migration]

    PartialMigration --> LoopPartials{For each Partial}
    LoopPartials --> CheckDest{Exists in Dealer Theme?}
    CheckDest -- Yes --> SkipPartialExists[Skip: Already Exists]
    CheckDest -- No --> CheckCommon{Exists in CommonTheme?}

    CheckCommon -- Yes --> SkipInheritance[Skip: Use Inheritance]
    CheckCommon -- No --> FuzzyMatch{Fuzzy Match?}

    FuzzyMatch -- Yes --> SkipInheritance
    FuzzyMatch -- No --> Interactive{Interactive Mode?}

    Interactive -- Yes --> AskUser[Prompt User]
    Interactive -- No --> SkipMissing[Skip: Missing]

    AskUser -- Skip --> SkipMissing
    AskUser -- Copy --> CopyFile[Copy File (Logic Fallback)]

    SkipPartialExists --> LoopPartials
    SkipInheritance --> LoopPartials
    SkipMissing --> LoopPartials
    CopyFile --> LoopPartials

    LoopPartials -- Done --> ReportGen[Generate Report]
    ReportGen --> End([End: Success])
```
