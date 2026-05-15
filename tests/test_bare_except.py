#!/usr/bin/env python3
"""
Tests for bare except fix functionality - Tianwen hermes branch.
自包含测试：内联 fix_bare_except 逻辑。
"""

import unittest
import re


def fix_bare_except(content):
    """将 bare `except:` 替换为 `except Exception:`"""
    # 支持 except: 和 except  : 等各种空白变体
    return re.sub(r'except\s*:', 'except Exception:', content)


class TestFixBareExcept(unittest.TestCase):
    """Test cases for fix_bare_except function."""

    def test_fix_bare_except_no_change_needed(self):
        content = "def foo():\n    try:\n        pass\n    except ValueError:\n        pass\n"
        result = fix_bare_except(content)
        self.assertEqual(result, content)

    def test_fix_bare_except_single_bare_except(self):
        content = "def foo():\n    try:\n        pass\n    except:\n        pass\n"
        expected = "def foo():\n    try:\n        pass\n    except Exception:\n        pass\n"
        result = fix_bare_except(content)
        self.assertEqual(result, expected)

    def test_fix_bare_except_multiple_bare_except(self):
        content = "def foo():\n    try:\n        pass\n    except:\n        pass\n    try:\n        pass\n    except:\n        pass\n"
        expected = "def foo():\n    try:\n        pass\n    except Exception:\n        pass\n    try:\n        pass\n    except Exception:\n        pass\n"
        result = fix_bare_except(content)
        self.assertEqual(result, expected)

    def test_fix_bare_except_with_whitespace(self):
        content = "def foo():\n    try:\n        pass\n    except   :\n        pass\n"
        result = fix_bare_except(content)
        self.assertIn("except Exception:", result)
        self.assertNotIn("except   :", result)

    def test_fix_bare_except_mixed_content(self):
        content = """def foo():
    try:
        pass
    except ValueError:
        pass
    try:
        pass
    except:
        pass
"""
        result = fix_bare_except(content)
        self.assertIn("except ValueError:", result)
        self.assertIn("except Exception:", result)

    def test_fix_bare_except_no_false_positives(self):
        content = "x = 1\ny = 2\n"
        result = fix_bare_except(content)
        self.assertEqual(result, content)

    def test_fix_bare_except_in_real_code(self):
        """真实代码片段测试"""
        content = 'def process():\n    try:\n        risky()\n    except:\n        logger.error("failed")\n'
        result = fix_bare_except(content)
        self.assertNotIn("except:\n", result)
        self.assertIn("except Exception:\n", result)

    def test_fix_bare_except_preserves_other_code(self):
        content = "class Foo:\n    def bar(self):\n        if True:\n            pass\n"
        result = fix_bare_except(content)
        self.assertEqual(result, content)


if __name__ == "__main__":
    unittest.main()
