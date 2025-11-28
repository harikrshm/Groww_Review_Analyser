# Theme Mapping Improvements

## Problem Identified

The clustering pipeline was mapping reviews to only 2 themes (`app_performance` and `customer_support`) instead of all 5 themes, even though reviews mentioned:
- **Orders/Execution** → Should map to `trading_execution`
- **UI/Interface** → Should map to `ui_usability`
- **Brokerage/Charges** → Should map to `fees_charges`

## Root Causes

1. **Large Mixed Clusters**: Cluster 0 had 82 reviews containing multiple themes
2. **Limited Keyword Matching**: Theme mapper only checked cluster label/summary, not actual review texts
3. **Generic LLM Summaries**: LLM-generated cluster labels were too generic ("App Performance and Feature Requests")

## Improvements Made

### 1. Enhanced Keyword Matching
- Theme mapper now checks **representative review texts** in addition to cluster labels
- More accurate keyword detection from actual review content

### 2. LLM Preference for Large Clusters
- Clusters with >20 reviews automatically use LLM mapping (more accurate)
- Small clusters (<20) still use fast deterministic matching

### 3. Improved LLM Prompt
- LLM prompt now includes representative review texts for better context
- Better theme detection from actual review content

### 4. Higher Confidence Threshold
- Raised from 0.6 to 0.7 for deterministic matching
- More clusters fall back to LLM for better accuracy

## Expected Results

After these improvements:
- **More accurate theme detection** from actual review texts
- **Better distribution** across all 5 themes
- **Large clusters** (>20 reviews) get LLM mapping for mixed themes

## Testing

Re-run clustering to see improved theme distribution:

```powershell
python cluster_reviews.py data/raw/reviews_2025-11-27.json 2025-W38
```

Expected improvements:
- Cluster 0 (82 reviews) should now map more accurately using LLM
- Reviews mentioning "orders", "execution" → `trading_execution`
- Reviews mentioning "UI", "interface" → `ui_usability`
- Reviews mentioning "brokerage", "charges" → `fees_charges`

