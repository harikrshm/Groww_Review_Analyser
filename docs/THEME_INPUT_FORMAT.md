# Theme Input Format

This document describes the format and structure of theme JSON files used in the Groww Review Analyser.

## Overview

Themes define categories for analyzing user reviews. Each theme represents a specific aspect of the product that users might mention in their reviews (e.g., "App Performance", "Fees & Charges", "Customer Support").

The system supports **multi-theme insight extraction**, meaning each review can be classified into multiple themes with different sentiments.

## Theme JSON Structure

### Top-Level Structure

```json
{
  "version": "1.0.0",
  "themes": [
    {
      // Theme objects (see below)
    }
  ],
  "classification_rules": {
    // Optional classification rules
  }
}
```

### Theme Object Structure

Each theme object must have the following structure:

```json
{
  "id": "theme_identifier",
  "name": "Human-Readable Theme Name",
  "description": "Detailed description of what this theme represents (optional, can be auto-generated)",
  "keywords": [
    "keyword1",
    "keyword2",
    "keyword3"
  ],
  "example_quotes": [
    "Example user quote mentioning this theme",
    "Another example quote"
  ],
  "sentiment_indicators": {
    "negative": ["negative", "indicator", "words"],
    "positive": ["positive", "indicator", "words"]
  }
}
```

### Required Fields

- **`id`** (string): Unique identifier for the theme (lowercase, underscores allowed)
  - Examples: `"app_performance"`, `"fees_charges"`, `"customer_support"`
  - Must be unique across all themes
  - Used internally for matching and clustering

- **`name`** (string): Human-readable theme name
  - Examples: `"App Performance & Stability"`, `"Fees & Charges Transparency"`
  - Displayed in reports and summaries

- **`keywords`** (array of strings): List of keywords that indicate this theme
  - Used for initial theme matching during classification
  - Should include variations and synonyms
  - Examples: `["crash", "glitch", "slow", "lag", "freeze"]`

### Optional Fields

- **`description`** (string): Detailed description of the theme
  - If not provided, the system will auto-generate a description using LLM
  - Helps the LLM understand the theme better during classification
  - Example: `"Frequent app glitches and crashes undermine reliability..."`

- **`example_quotes`** (array of strings): Example review quotes that mention this theme
  - Helps guide the LLM in understanding the theme context
  - Used for training and validation

- **`sentiment_indicators`** (object): Keywords that indicate sentiment
  - **`negative`** (array): Words that suggest negative sentiment for this theme
  - **`positive`** (array): Words that suggest positive sentiment for this theme
  - Examples:
    ```json
    {
      "negative": ["crash", "glitch", "slow", "not working"],
      "positive": ["smooth", "fast", "reliable", "works well"]
    }
    ```

## Complete Example

```json
{
  "version": "1.0.0",
  "themes": [
    {
      "id": "app_performance",
      "name": "App Performance & Stability",
      "description": "Frequent app glitches and crashes undermine reliability. Slow loading and data errors frustrate users.",
      "keywords": [
        "crash", "glitch", "bug", "slow", "lag", "freeze", "hang",
        "loading", "refresh", "error", "not working", "stuck",
        "chart", "data", "price", "update", "sync", "network",
        "performance", "stability", "reliable", "smooth"
      ],
      "example_quotes": [
        "Too much glitch, option chain not open properly... sometimes working, sometimes not working.",
        "App crashes every time I try to view my portfolio"
      ],
      "sentiment_indicators": {
        "negative": ["crash", "glitch", "slow", "not working", "bug", "freeze"],
        "positive": ["smooth", "fast", "reliable", "works well", "no issues"]
      }
    },
    {
      "id": "fees_charges",
      "name": "Fees & Charges Transparency",
      "description": "Unexpected brokerage and hidden fees frustrate users by eating into profits.",
      "keywords": [
        "charge", "charges", "fee", "fees", "brokerage", "commission",
        "expensive", "costly", "deduct", "deduction", "hidden",
        "DP charge", "STT", "GST", "tax", "profit", "loss"
      ],
      "example_quotes": [
        "worst app ever... very high brokerage.. and hidden charges..",
        "brokerage is a nightmare for scalpers"
      ],
      "sentiment_indicators": {
        "negative": ["high charge", "hidden fees", "expensive", "deducted"],
        "positive": ["free", "low cost", "reasonable", "no charges"]
      }
    }
  ]
}
```

## Auto-Enrichment

If a theme is missing a `description`, the system will automatically generate one using an LLM based on:
- The theme's `id` and `name`
- The provided `keywords`
- The context of the application (e.g., "financial trading app")

This ensures all themes have complete information for accurate classification.

## Providing Themes

Themes can be provided in three ways:

### 1. Configuration File (Default)

Use `config/themes.json` for default themes used across all analyses:

```bash
# Uses themes from config/themes.json
python -m src.cli generate 2025-11-01 2025-11-30
```

### 2. CLI Parameter (File Path)

Specify a custom theme file via `--themes` flag:

```bash
# Use custom themes file
python -m src.cli generate 2025-11-01 2025-11-30 --themes examples/themes/custom_themes.json
```

### 3. CLI Parameter (Inline JSON)

Provide themes directly as a JSON string:

```bash
python -m src.cli generate 2025-11-01 2025-11-30 --themes '[{"id": "ui", "name": "UI/UX", "keywords": ["ui", "interface", "design"]}]'
```

### 4. Email Request

Themes can be extracted from natural language email requests:

```
Subject: [ANALYZE] Analyze with themes: UI, Performance, Fees

Please analyze reviews from the last 4 weeks focusing on UI, Performance, and Fees.
```

The system will automatically create theme objects from the mentioned theme names.

## Validation

Themes are validated before use. A theme is valid if:

1. ✅ Has required fields: `id`, `name`, `keywords`
2. ✅ `keywords` is a non-empty array
3. ✅ All keywords are strings
4. ✅ `id` is unique across all themes

If validation fails, the system will show detailed error messages indicating which fields are missing or invalid.

## Best Practices

### Keyword Selection

- **Be specific**: Use domain-specific terms (e.g., "brokerage", "stop loss", "GTT")
- **Include variations**: Add synonyms and common misspellings
- **Cover sentiment**: Include both positive and negative keywords
- **Think like users**: Use terms customers actually use in reviews

### Theme Naming

- **Be descriptive**: Use clear, specific names (e.g., "App Performance & Stability")
- **Avoid overlap**: Ensure themes don't overlap too much
- **Keep it simple**: Don't use overly technical jargon

### Example Quotes

- **Be realistic**: Use actual review quotes if possible
- **Show variety**: Include different phrasings and contexts
- **Cover edge cases**: Include borderline examples

## Examples

See the `examples/themes/` directory for complete example theme files:
- `example_themes.json` - Full example with all fields
- `example_themes_without_descriptions.json` - Minimal example (tests auto-enrichment)

