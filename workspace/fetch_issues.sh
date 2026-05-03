#!/bin/bash
REPO="LL-LK/tianwen-agi"
OUTPUT_DIR="/mnt/f/tianwen-agi/workspace"

for i in {1..51}; do
  echo "=== Issue $i ===" >> "$OUTPUT_DIR/issue_${i}_comments.txt"
  gh issue view $i --repo $REPO --comments 2>/dev/null >> "$OUTPUT_DIR/issue_${i}_comments.txt"
  echo "" >> "$OUTPUT_DIR/issue_${i}_comments.txt"
  echo "---END---" >> "$OUTPUT_DIR/issue_${i}_comments.txt"
  echo "Done issue $i"
done
