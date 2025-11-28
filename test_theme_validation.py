"""Test theme validation with DeepSeek R1 Distilled via Groq."""

import os
import sys
from pathlib import Path

# Check for API key
if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY not found in environment variables!")
    print("\nPlease set your Groq API key:")
    print("  Windows PowerShell: $env:GROQ_API_KEY='your_api_key_here'")
    print("  Windows CMD: set GROQ_API_KEY=your_api_key_here")
    print("  Linux/Mac: export GROQ_API_KEY='your_api_key_here'")
    print("\nGet your API key from: https://console.groq.com/keys")
    sys.exit(1)

from src.phase2_classification.theme_validator import ThemeValidator

print("=" * 70)
print("THEME VALIDATION TEST")
print("=" * 70)
print(f"LLM: DeepSeek R1 Distilled via Groq")
print(f"Themes config: config/themes.json")
print()

try:
    validator = ThemeValidator()
    print("Running theme validation...")
    print()
    
    result = validator.validate_themes()
    
    # Print formatted report
    report = validator.format_validation_report(result)
    print(report)
    
    # Save to file
    output_path = Path("data/theme_validation_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nFull validation results saved to: {output_path}")
    print("\n✅ Theme validation completed successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

