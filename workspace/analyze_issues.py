#!/usr/bin/env python3
import os
import re
import json
from pathlib import Path

OUTPUT_FILE = "/mnt/f/tianwen-agi/workspace/issues_analysis.txt"
DATA_DIR = Path("/mnt/f/tianwen-agi/workspace")

def extract_issue_info(content):
    """Extract issue metadata and comments"""
    lines = content.strip().split('\n')
    info = {
        'title': '',
        'state': '',
        'author': '',
        'labels': [],
        'comments': []
    }
    
    current_comment = None
    in_comment = False
    
    for line in lines:
        if line.startswith('title:'):
            info['title'] = line.replace('title:', '').strip()
        elif line.startswith('state:'):
            info['state'] = line.replace('state:', '').strip()
        elif line.startswith('author:'):
            info['author'] = line.replace('author:', '').strip()
        elif line.startswith('labels:'):
            info['labels'] = [l.strip() for l in line.replace('labels:', '').split(',') if l.strip()]
        elif line.startswith('## Comments'):
            in_comment = True
        elif in_comment and line.startswith('**@'):
            # Comment author line
            if current_comment:
                info['comments'].append(current_comment)
            match = re.match(r'\*\*@(.+?)\*\*', line)
            if match:
                current_comment = {'author': match.group(1), 'body': ''}
        elif in_comment and current_comment is not None:
            current_comment['body'] += line + '\n'
    
    if current_comment:
        info['comments'].append(current_comment)
    
    return info

def is_claude_message(author, body):
    """Identify if message is from Claude"""
    author_lower = author.lower()
    body_lower = body.lower()
    
    claude_indicators = [
        'claude', 'anthropic', 'opus', 'sonnet', 'haiku',
        'hermes', 'agi', 'ai assistant'
    ]
    
    # Check for Claude in author
    if 'claude' in author_lower:
        return True
    
    # Check for AI assistant patterns
    if '**@' in body_lower and 'claude' in body_lower:
        return True
        
    return False

def analyze_issues():
    results = []
    
    for i in range(1, 52):
        filepath = DATA_DIR / f"issue_{i}_comments.txt"
        if not filepath.exists():
            results.append({
                'issue': i,
                'error': 'File not found'
            })
            continue
        
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        
        # Check if issue exists
        if 'issue not found' in content.lower() or 'HTTP 404' in content:
            results.append({
                'issue': i,
                'error': 'Issue not found'
            })
            continue
        
        info = extract_issue_info(content)
        
        commenters = []
        claude_messages = []
        
        for c in info['comments']:
            author = c.get('author', 'unknown')
            commenters.append(author)
            
            # Check if Claude message
            if 'claude' in author.lower() or 'hermes' in author.lower():
                claude_messages.append({
                    'author': author,
                    'preview': c['body'][:200].replace('\n', ' ')
                })
        
        results.append({
            'issue': i,
            'title': info['title'][:80],
            'author': info['author'],
            'state': info['state'],
            'commenters': list(set(commenters)),
            'num_comments': len(info['comments']),
            'claude_messages': claude_messages
        })
    
    return results

def main():
    print("Analyzing issues...")
    results = analyze_issues()
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("TIANWEN-AGI ISSUES ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        total_with_comments = 0
        total_claude_comments = 0
        
        for r in results:
            if 'error' in r:
                continue
            
            f.write(f"\n{'='*60}\n")
            f.write(f"Issue #{r['issue']}: {r['title']}\n")
            f.write(f"Author: {r['author']} | State: {r['state']} | Comments: {r['num_comments']}\n")
            f.write(f"{'='*60}\n")
            
            f.write(f"Commenters ({len(r['commenters'])}): {', '.join(r['commenters'])}\n")
            
            if r['claude_messages']:
                f.write(f"\n*** CLAUDE MESSAGES ({len(r['claude_messages'])}):\n")
                for cm in r['claude_messages']:
                    f.write(f"  - @{cm['author']}: {cm['preview']}...\n")
                total_claude_comments += len(r['claude_messages'])
            
            total_with_comments += 1
        
        f.write(f"\n\n{'='*80}\n")
        f.write("SUMMARY\n")
        f.write(f"{'='*80}\n")
        f.write(f"Total issues analyzed: {len([r for r in results if 'error' not in r])}\n")
        f.write(f"Issues with comments: {total_with_comments}\n")
        f.write(f"Total Claude messages found: {total_claude_comments}\n")
    
    print(f"Analysis complete. Output: {OUTPUT_FILE}")
    
    # Also output to console
    for r in results:
        if 'error' not in r and r['claude_messages']:
            print(f"Issue #{r['issue']}: {len(r['claude_messages'])} Claude msg - Commenters: {r['commenters']}")

if __name__ == '__main__':
    main()
