#!/bin/bash
# Test script with improved prompts and image resizing

cd "/Users/awaisrafeeq/Documents/python/Automated Electrical Label Extraction/MVP"
source venv/bin/activate

echo "================================"
echo "Testing Improved Label Extraction"
echo "================================"
echo ""

echo "Test 1: MEDIUM VOLTAGE.pdf (page 1 only)"
echo "------------------------------------"
python main.py pdf "MEDIUM VOLTAGE.pdf" --page 1 -o test_improved_page1.xlsx
echo ""

echo "Test 2: MEDIUM VOLTAGE.pdf (full PDF)"
echo "------------------------------------"
python main.py pdf "MEDIUM VOLTAGE.pdf" -o test_improved_full.xlsx
echo ""

echo "================================"
echo "Comparing Results"
echo "================================"

python -c "
import pandas as pd

print('\n=== ORIGINAL RESULTS ===')
df1 = pd.read_excel('output/MEDIUM VOLTAGE_labels.xlsx', sheet_name='Labels')
print(f'Total labels: {len(df1)}')
print('\nSample Line 2 values (checking for duplicates):')
print(df1[['Equipment Type', 'Line 2']].head(5).to_string())

print('\n=== IMPROVED RESULTS ===')
df2 = pd.read_excel('test_improved_full.xlsx', sheet_name='Labels')
print(f'Total labels: {len(df2)}')
print('\nSample Line 2 values (should be clean):')
print(df2[['Equipment Type', 'Line 2']].head(5).to_string())

print('\n=== IMPROVEMENTS ===')
# Check for 'FED FROM' duplicates
original_dupes = df1['Line 2'].str.contains('FED FROM.*FROM', na=False).sum()
improved_dupes = df2['Line 2'].str.contains('FED FROM.*FROM', na=False).sum()
print(f'Original duplicate FED FROM: {original_dupes}')
print(f'Improved duplicate FED FROM: {improved_dupes}')
print(f'Improvement: {original_dupes - improved_dupes} issues fixed')
"

echo ""
echo "================================"
echo "Tests Complete!"
echo "================================"
echo "Check these files:"
echo "- test_improved_page1.xlsx"
echo "- test_improved_full.xlsx"
echo ""
