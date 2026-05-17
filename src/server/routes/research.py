"""
Research routes for Hermes-AGI
Extracted from server.py
"""
import logging
from quart import jsonify, request
import uuid

logger = logging.getLogger("hermes_agi")


def register_research_routes(app, observatory_state, cycle_history, hypothesis_tester, require_api_key):
    """Register research and hypothesis testing routes"""

    @app.route("/api/research/status", methods=["GET"])
    async def research_status():
        """获取研究闭环状态"""
        return jsonify(observatory_state.get("research_loop", {}))

    @app.route("/api/research/cycles", methods=["GET"])
    async def research_cycles():
        """获取研究周期历史"""
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        start = (page - 1) * per_page
        end = start + per_page
        return jsonify({
            "cycles": cycle_history[::-1][start:end],
            "total": len(cycle_history),
            "page": page,
            "per_page": per_page,
        })

    @app.route("/api/hypothesis/test", methods=["POST"])
    @require_api_key
    async def test_hypothesis():
        """
        假说验证端点

        请求体:
        {
            "hypothesis": {
                "id": "hypo_xxx",
                "statement": "如果...那么...",
                "premises": [...],
                "predictions": [...],
                "verification_method": "...",
                "confidence": 0.7
            },
            "observation_data": [...],
            "literature_evidence": [...]
        }

        响应:
        {
            "hypothesis_id": "...",
            "overall_result": "confirmed|rejected|inconclusive|revised",
            "confidence_change": 0.x,
            "evidence_for": [...],
            "evidence_against": [...],
            "recommendation": "...",
            "confidence_interval": [...],
            "cross_validation_score": 0.x,
            "statistical_confidence": {...}
        }
        """
        data = await request.get_json()

        if not data or "hypothesis" not in data:
            return jsonify({"error": "缺少 hypothesis 字段"}), 400

        hypo_data = data["hypothesis"]
        observation_data = data.get("observation_data")
        literature_evidence = data.get("literature_evidence")

        if not observation_data or not literature_evidence:
            return jsonify({
                "error": "缺少必需数据",
                "message": "observation_data 和 literature_evidence 为必填字段",
                "code": "MISSING_REQUIRED_DATA"
            }), 400

        try:
            from research.hypothesis_generator import Hypothesis
            hypo = Hypothesis(
                id=hypo_data.get("id", f"hypo_{uuid.uuid4().hex[:8]}"),
                statement=hypo_data.get("statement", ""),
                premises=hypo_data.get("premises", []),
                predictions=hypo_data.get("predictions", []),
                verification_method=hypo_data.get("verification_method", "待指定"),
                confidence=hypo_data.get("confidence", 0.5),
                status="待验证"
            )
            report = await hypothesis_tester.test_hypothesis(hypo, observation_data, literature_evidence)

            logger.info(f"[HypothesisTest] 验证完成: hypothesis={hypo.id}, result={report.overall_result.value}")

            return jsonify({
                "hypothesis_id": report.hypothesis_id,
                "overall_result": report.overall_result.value,
                "confidence_change": round(report.confidence_change, 3),
                "evidence_for": report.evidence_for,
                "evidence_against": report.evidence_against,
                "recommendation": report.recommendation,
                "timestamp": report.timestamp,
                "confidence_interval": list(report.confidence_interval) if report.confidence_interval else None,
                "cross_validation_score": round(report.cross_validation_score, 3) if report.cross_validation_score else None,
                "statistical_confidence": report.statistical_confidence,
                "test_cases": [
                    {
                        "id": tc.id,
                        "test_method": tc.test_method,
                        "passed": tc.passed,
                        "actual_outcome": tc.actual_outcome
                    }
                    for tc in report.test_cases
                ]
            })
        except Exception as e:
            logger.error(f"[HypothesisTest] 验证失败: {e}")
            return jsonify({"error": f"验证失败: {str(e)}"}), 500

    @app.route("/api/hypothesis/generate", methods=["POST"])
    @require_api_key
    async def hypothesis_generate():
        """生成假说"""
        data = await request.get_json()
        context = data.get("context", "")
        domain = data.get("domain", "天文学")

        if not context:
            return jsonify({"error": "缺少 context 参数"}), 400

        try:
            from research.hypothesis_generator import HypothesisGenerator
            generator = HypothesisGenerator()
            hypotheses = await generator.generate_hypotheses(context, domain)
            return jsonify({
                "hypotheses": [
                    {
                        "id": h.id,
                        "statement": h.statement,
                        "premises": h.premises,
                        "predictions": h.predictions,
                        "confidence": h.confidence
                    }
                    for h in hypotheses
                ],
                "count": len(hypotheses)
            })
        except Exception as e:
            logger.error(f"[HypothesisGenerate] 生成失败: {e}")
            return jsonify({"error": str(e)}), 500

    return app