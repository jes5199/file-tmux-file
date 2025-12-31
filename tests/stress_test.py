#!/usr/bin/env python3
"""
Stress tests for file-tmux-file input queue handling.

Usage:
    python stress_test.py <input_file_path> <test_name>

Tests:
    rapid_fire    - Send 100 messages in quick succession
    large_block   - Send a 10KB text block
    special_chars - Send messages with special/unicode characters
    all           - Run all tests
"""

import sys
import time
from pathlib import Path


def write_to_input(input_path: Path, content: str):
    """Append content to input file with newline."""
    with open(input_path, 'a') as f:
        f.write(content + '\n')


def test_rapid_fire(input_path: Path):
    """Send 100 messages as fast as possible."""
    print("=== RAPID FIRE TEST ===")
    print("Sending 100 messages in quick succession...")

    start = time.time()
    for i in range(100):
        write_to_input(input_path, f"Rapid fire message {i+1:03d}")
    elapsed = time.time() - start

    print(f"Sent 100 messages in {elapsed:.3f}s")
    print("Check target pane - all 100 messages should appear in order.")


def test_large_block(input_path: Path):
    """Send a 10KB text block."""
    print("=== LARGE BLOCK TEST ===")

    # Generate 10KB of text
    line = "ABCDEFGHIJ" * 10  # 100 chars per line
    lines = [f"Line {i:04d}: {line}" for i in range(85)]  # ~10KB
    large_text = '\n'.join(lines)

    print(f"Sending {len(large_text)} bytes ({len(lines)} lines)...")
    write_to_input(input_path, large_text)

    print("Check target pane - large block should appear intact.")


def test_special_chars(input_path: Path):
    """Send messages with special and unicode characters."""
    print("=== SPECIAL CHARS TEST ===")

    test_strings = [
        # Basic special chars
        "Quotes: 'single' \"double\" `backtick`",
        "Slashes: / \\ // \\\\",
        "Brackets: () [] {} <>",
        "Symbols: !@#$%^&*-_=+|;:,.",

        # Shell special chars
        "Shell: $HOME $(echo hi) `echo hi`",
        "Ampersand: foo && bar & baz",
        "Pipes: foo | bar || baz",
        "Redirects: > >> < << 2>&1",

        # Whitespace
        "Tabs:\there\tare\ttabs",
        "  Leading and trailing spaces  ",

        # Unicode
        "Emoji: 🚀 🎉 🔥 💡 ✨",
        "Unicode: café naïve résumé",
        "CJK: 你好世界 こんにちは 한국어",
        "Symbols: → ← ↑ ↓ • ◦ ● ○ ■ □",
        "Math: ∑ ∏ ∫ ∂ ∇ ∞ ≈ ≠ ≤ ≥",

        # Edge cases
        "Empty quotes: '' \"\"",
        "Newline literal: \\n \\r \\t",
        "Null-ish: \\0 \\x00",
    ]

    print(f"Sending {len(test_strings)} special char test messages...")
    for msg in test_strings:
        write_to_input(input_path, f"SPECIAL: {msg}")
        time.sleep(0.05)  # Small delay to not overwhelm

    print("Check target pane - all messages should render correctly.")


def test_long_lines(input_path: Path):
    """Send very long lines (1K, 5K, 10K chars)."""
    print("=== LONG LINES TEST ===")

    for length in [1000, 5000, 10000]:
        line = "X" * length
        write_to_input(input_path, f"LINE_{length}: {line}")
        print(f"Sent {length} char line")
        time.sleep(0.1)

    print("Check target pane - long lines should appear (may wrap).")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    test_name = sys.argv[2]

    if not input_path.parent.exists():
        print(f"Error: Directory {input_path.parent} does not exist")
        sys.exit(1)

    tests = {
        'rapid_fire': test_rapid_fire,
        'large_block': test_large_block,
        'special_chars': test_special_chars,
        'long_lines': test_long_lines,
    }

    if test_name == 'all':
        for name, test_func in tests.items():
            print()
            test_func(input_path)
            time.sleep(1)  # Pause between tests
    elif test_name in tests:
        tests[test_name](input_path)
    else:
        print(f"Unknown test: {test_name}")
        print(f"Available: {', '.join(tests.keys())}, all")
        sys.exit(1)


if __name__ == '__main__':
    main()
