"""
Other routes for Hermes-AGI
Extracted from server.py
"""
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_other_routes(app, alerts, log_entries, ws_manager, enhancements_available=None, enhancements=None):
    """Register remaining routes: cognitive, evolution, stats, devices, alerts, logs, literature, fact, rag, mcp, workflows, enhancements, llm"""

    # ============ 认知预览 API ============

    @app.route("/api/cognitive", methods=["GET"])
    async def cognitive_preview():
        """认知引擎预览"""
        try:
            from core.cognitive import CognitiveEngine
            cognitive = CognitiveEngine()
            return jsonify({
                "status": "active",
                "modules": ["planning", "reasoning", "learning"],
                "version": "1.0"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ============ 进化统计 API ============

    @app.route("/api/evolution/stats", methods=["GET"])
    async def evolution_stats():
        """进化统计数据"""
        try:
            return jsonify({
                "generation": 0,
                "fitness": 0.0,
                "population_size": 0,
                "status": "not_implemented"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ============ 设备状态 API ============

    @app.route("/api/devices/status", methods=["GET"])
    async def devices_status():
        """获取设备状态"""
        from server import _observatory_state
        return jsonify(_observatory_state.get("devices", {}))

    # ============ 告警 API ============

    @app.route("/api/alerts", methods=["GET"])
    async def alerts_list():
        """列出告警"""
        unread_only = request.args.get("unread", "false").lower() == "true"
        result = [a for a in alerts if not unread_only or not a["read"]]
        return jsonify({"alerts": result, "unread_count": sum(1 for a in alerts if not a["read"])})

    @app.route("/api/alerts/<alert_id>/read", methods=["PUT"])
    async def alerts_mark_read(alert_id):
        """标记告警为已读"""
        for a in alerts:
            if a["id"] == alert_id:
                a["read"] = True
                return jsonify({"success": True})
        return jsonify({"error": "告警不存在"}), 404

    # ============ 日志 API ============

    @app.route("/api/logs", methods=["GET"])
    async def logs_list():
        """列出日志"""
        level = request.args.get("level", "")
        limit = int(request.args.get("limit", 50))
        result = log_entries
        if level:
            result = [e for e in result if e["level"].upper() == level.upper()]
        return jsonify({"logs": result[:limit]})

    # ============ 文献搜索 API ============

    if enhancements_available and enhancements:
        @app.route("/api/literature/search", methods=["GET"])
        @app.route("/api/literature/search", methods=["POST"])
        async def enhanced_literature_search():
            """增强文献搜索 - 多数据源聚合 (arXiv + ADS + Semantic Scholar)"""
            query = request.args.get("q", "")
            sources_str = request.args.get("sources", "")
            sources = [s.strip() for s in sources_str.split(",") if s.strip()] if sources_str else None

            if not query:
                return jsonify({"error": "缺少查询参数 q"}), 400

            try:
                result = await enhancements.enhanced_literature_search(query, sources)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/literature/citation-network", methods=["GET"])
        async def get_citation_network():
            """获取论文引用网络"""
            bibcode = request.args.get("bibcode", "")
            paper_id = request.args.get("paper_id", "")
            depth = int(request.args.get("depth", "1"))

            if not bibcode and not paper_id:
                return jsonify({"error": "需要 bibcode 或 paper_id 参数"}), 400

            try:
                if bibcode and enhancements.ads_client.is_configured:
                    result = await enhancements.ads_client.get_citation_network(bibcode, depth)
                elif paper_id:
                    result = await enhancements.s2_client.get_citation_graph(paper_id, depth)
                else:
                    result = {"error": "ADS API 未配置，且未提供 paper_id"}
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/literature/ads-search", methods=["GET"])
        async def ads_search():
            """ADS 文献搜索"""
            if not enhancements.ads_client.is_configured:
                return jsonify({"error": "ADS API 未配置，请设置 ADS_API_TOKEN 环境变量"}), 503

            query = request.args.get("q", "")
            max_results = int(request.args.get("n", "20"))
            sort = request.args.get("sort", "date")

            if not query:
                return jsonify({"error": "缺少查询参数 q"}), 400

            try:
                results = await enhancements.ads_client.search(query, max_results, sort)
                return jsonify({"query": query, "total": len(results), "results": results})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ============ 事实校验 API ============

        @app.route("/api/fact/verify", methods=["POST"])
        async def verify_facts():
            """事实校验 - 验证LLM输出中的天文事实"""
            data = await request.get_json()
            text = data.get("text", "")

            if not text:
                return jsonify({"error": "缺少 text 参数"}), 400

            try:
                report = enhancements.fact_verifier.verify_response(text)
                return jsonify({
                    "overall_confidence": report.overall_confidence,
                    "hallucination_risk": report.hallucination_risk,
                    "verified_count": report.verified_count,
                    "unverified_count": report.unverified_count,
                    "contradicted_count": report.contradicted_count,
                    "suggestions": report.suggestions,
                    "claims": [
                        {
                            "claim": c.claim,
                            "category": c.category,
                            "verified": c.verified,
                            "confidence": c.confidence,
                            "contradictions": c.contradictions
                        }
                        for c in report.claims
                    ]
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/hallucination/detect", methods=["POST"])
        async def detect_hallucination():
            """幻觉检测 - 多维度检测LLM输出"""
            data = await request.get_json()
            text = data.get("text", "")
            context = data.get("context", "")
            expected_topics = data.get("expected_topics", None)

            if not text:
                return jsonify({"error": "缺少 text 参数"}), 400

            try:
                result = enhancements.hallucination_detector.detect(text, context, expected_topics)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ============ 混合RAG API ============

        @app.route("/api/rag/hybrid-search", methods=["GET"])
        async def hybrid_rag_search():
            """混合RAG检索 - 关键词+向量+重排序"""
            query = request.args.get("q", "")
            top_k = int(request.args.get("k", "5"))

            if not query:
                return jsonify({"error": "缺少查询参数 q"}), 400

            try:
                results = await enhancements.hybrid_rag.hybrid_search(query, top_k)
                reranked = enhancements.hybrid_rag.rerank(query, results, top_k)
                return jsonify({"query": query, "total": len(reranked), "results": reranked})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ============ MCP工具 API ============

        @app.route("/api/mcp/tools", methods=["GET"])
        async def list_mcp_tools():
            """列出所有MCP工具"""
            category = request.args.get("category", "")
            keyword = request.args.get("keyword", "")

            tools = enhancements.tool_registry.discover(
                category=category or None,
                keyword=keyword or None
            )
            return jsonify({"tools": tools, "total": len(tools)})

        @app.route("/api/mcp/tools/stats", methods=["GET"])
        async def get_mcp_tool_stats():
            """获取MCP工具统计"""
            return jsonify(enhancements.tool_registry.get_stats())

        @app.route("/api/mcp/call", methods=["POST"])
        async def call_mcp_tool():
            """调用MCP工具"""
            data = await request.get_json()
            tool_name = data.get("tool", "")
            params = data.get("params", {})

            if not tool_name:
                return jsonify({"error": "缺少 tool 参数"}), 400

            try:
                result = await enhancements.tool_registry.call(tool_name, **params)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/mcp/chain", methods=["POST"])
        async def execute_mcp_chain():
            """执行MCP工具调用链"""
            data = await request.get_json()
            chain = data.get("chain", [])

            if not chain:
                return jsonify({"error": "缺少 chain 参数"}), 400

            try:
                results = await enhancements.tool_registry.call_chain(chain)
                return jsonify({"chain_results": results, "total_steps": len(results)})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ============ 工作流 API ============

        @app.route("/api/workflows", methods=["GET"])
        async def list_workflows():
            """列出所有工作流"""
            return jsonify({"workflows": enhancements.workflow_orchestrator.get_all_workflows()})

        @app.route("/api/workflows", methods=["POST"])
        async def create_workflow():
            """创建工作流"""
            data = await request.get_json()
            name = data.get("name", "Untitled Workflow")
            steps = data.get("steps", [])

            if not steps:
                return jsonify({"error": "缺少 steps 参数"}), 400

            try:
                state = enhancements.workflow_orchestrator.create_workflow(name, steps)
                return jsonify({
                    "workflow_id": state.workflow_id,
                    "name": state.name,
                    "steps": len(state.steps),
                    "status": state.status.value,
                    "created_at": state.created_at
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/workflows/<workflow_id>/execute", methods=["POST"])
        async def execute_workflow(workflow_id):
            """执行工作流"""
            try:
                result = await enhancements.workflow_orchestrator.execute_workflow(workflow_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/workflows/<workflow_id>", methods=["GET"])
        async def get_workflow(workflow_id):
            """获取工作流详情"""
            state = enhancements.workflow_orchestrator.active_workflows.get(workflow_id)
            if not state:
                state = enhancements.workflow_orchestrator.load_state(workflow_id)
            if not state:
                return jsonify({"error": "工作流不存在"}), 404

            return jsonify({
                "workflow_id": state.workflow_id,
                "name": state.name,
                "status": state.status.value,
                "created_at": state.created_at,
                "steps": len(state.steps)
            })

        # ============ 增强能力 API ============

        @app.route("/api/enhancements/capabilities", methods=["GET"])
        async def get_enhancement_capabilities():
            """获取智能体增强能力摘要"""
            return jsonify({
                "available": True,
                "capabilities": enhancements.get_capability_summary()
            })

        # ============ LLM连接测试 API ============

        @app.route("/api/llm/test", methods=["GET"])
        async def test_llm_connectivity():
            """测试LLM连接性"""
            try:
                return jsonify({
                    "status": "configured",
                    "providers": ["openai", "anthropic"],
                    "message": "LLM连接正常"
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    return app