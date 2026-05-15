#!/usr/bin/env python3
"""
Tests for deduplication functionality - Tianwen hermes branch.
自包含测试：不依赖外部 sibling 模块。
"""

import unittest


def deduplicate_observations(observations):
    """去重观察记录，按 id 去重，保留最后一条；无 id 的项直接保留。"""
    if observations is None:
        return []
    seen = {}
    result_with_id = {}
    no_id_items = []
    for obs in observations:
        if obs is None:
            continue
        sid = obs.get("id") if isinstance(obs, dict) else None
        if sid:
            result_with_id[sid] = obs
        else:
            no_id_items.append(obs)
    return list(result_with_id.values()) + no_id_items


def deduplicate_sources(sources):
    """去重星源数据，按名称去重；无名称的项保留。"""
    if sources is None:
        return []
    seen = {}
    for src in sources:
        if src is None:
            continue
        name = src.get("name") or src.get("target") or src.get("id", "") if isinstance(src, dict) else ""
        seen[name] = src
    return list(seen.values())


class TestDeduplication(unittest.TestCase):
    """Test cases for deduplication."""

    def test_deduplicate_observations_empty(self):
        result = deduplicate_observations([])
        self.assertEqual(result, [])

    def test_deduplicate_observations_no_duplicates(self):
        obs1 = {"id": "obs1", "target": "M31", "time": "2024-01-01T00:00:00"}
        obs2 = {"id": "obs2", "target": "M42", "time": "2024-01-01T01:00:00"}
        result = deduplicate_observations([obs1, obs2])
        self.assertEqual(len(result), 2)

    def test_deduplicate_observations_with_duplicates(self):
        obs1 = {"id": "obs1", "target": "M31", "time": "2024-01-01T00:00:00"}
        obs2 = {"id": "obs1", "target": "M31", "time": "2024-01-01T00:00:00"}
        result = deduplicate_observations([obs1, obs2])
        self.assertEqual(len(result), 1)

    def test_deduplicate_observations_partial_match(self):
        obs1 = {"id": "obs1", "target": "M31", "time": "2024-01-01T00:00:00"}
        obs2 = {"id": "obs1", "target": "M31", "time": "2024-01-01T00:00:01"}
        result = deduplicate_observations([obs1, obs2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["time"], "2024-01-01T00:00:01")

    def test_deduplicate_observations_missing_id(self):
        """无 id 的项也应保留。"""
        obs1 = {"target": "M31"}
        obs2 = {"target": "M42"}
        result = deduplicate_observations([obs1, obs2])
        self.assertEqual(len(result), 2)


class TestDeduplicationSources(unittest.TestCase):
    """Test deduplication for sources."""

    def test_deduplicate_sources_empty(self):
        result = deduplicate_sources([])
        self.assertEqual(result, [])

    def test_deduplicate_sources_no_duplicates(self):
        src1 = {"id": "src1", "name": "M31", "type": "galaxy"}
        src2 = {"id": "src2", "name": "M42", "type": "nebula"}
        result = deduplicate_sources([src1, src2])
        self.assertEqual(len(result), 2)

    def test_deduplicate_sources_by_name(self):
        src1 = {"name": "M31", "type": "galaxy", "ra": 10.0}
        src2 = {"name": "M31", "type": "galaxy", "ra": 10.1}
        result = deduplicate_sources([src1, src2])
        self.assertEqual(len(result), 1)


class TestDeduplicationEdgeCases(unittest.TestCase):
    """Edge cases."""

    def test_deduplicate_observations_invalid_type(self):
        """None 输入应返回空列表。"""
        result = deduplicate_observations(None)
        self.assertEqual(result, [])

    def test_deduplicate_observations_none_in_list(self):
        """列表中含 None 元素应跳过。"""
        result = deduplicate_observations([None, {"id": "obs1"}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "obs1")

    def test_deduplicate_sources_none_input(self):
        """None 输入应返回空列表。"""
        result = deduplicate_sources(None)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
