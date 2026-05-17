"""
SkyChart routes for Hermes-AGI
Extracted from server.py
"""
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_skychart_routes(app, skychart_available, sky_survey_class, get_realtime_skychart_func, parse_coordinates_func, builtin_catalog):
    """Register skychart routes"""

    @app.route("/api/skychart/realtime", methods=["GET"])
    async def skychart_realtime():
        """
        获取目标真实星图 (NASA SkyView)

        Query Params:
            target: 目标名称 (如 M31, NGC224)
            survey: 巡天调查 (默认 DSS2/color)
            size: 视场大小角分 (默认 15)
            pixels: 图像像素 (默认 600)
        """
        if not skychart_available:
            return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503

        target = request.args.get("target", "M31")
        survey_name = request.args.get("survey", "DSS2/color")
        size = float(request.args.get("size", 15))
        pixels = int(request.args.get("pixels", 600))

        try:
            sky_survey = sky_survey_class(survey_name)
        except ValueError:
            sky_survey = sky_survey_class.DSS2_COLOR

        try:
            result = await get_realtime_skychart_func(
                target=target,
                survey=sky_survey,
                size=size,
                pixels=pixels,
                use_cache=True
            )

            output = {
                "success": True,
                "target": result.target,
                "survey": result.survey,
                "ra": result.ra,
                "dec": result.dec,
                "width": result.width,
                "height": result.height,
                "fov_deg": result.fov,
                "image_base64": result.image_base64,
                "sources_count": len(result.catalog_sources),
                "sources": result.catalog_sources[:20],
                "cached": result.cached,
                "timestamp": result.timestamp,
            }

            return jsonify(output)
        except Exception as e:
            logger.error(f"SkyChart error: {e}")
            return jsonify({"error": str(e), "code": "SKYCHART_ERROR"}), 500

    @app.route("/api/skychart/batch", methods=["GET"])
    async def skychart_batch():
        """
        批量获取多个目标星图

        Query Params:
            targets: 逗号分隔的目标列表
            survey: 巡天调查
            size: 视场大小角分
        """
        if not skychart_available:
            return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503

        targets_str = request.args.get("targets", "M31,M42,M51")
        survey_name = request.args.get("survey", "DSS2/color")
        size = float(request.args.get("size", 15))

        targets = [t.strip() for t in targets_str.split(",") if t.strip()]

        try:
            sky_survey = sky_survey_class(survey_name)
        except ValueError:
            sky_survey = sky_survey_class.DSS2_COLOR

        output = {}
        for target in targets:
            try:
                result = await get_realtime_skychart_func(
                    target=target,
                    survey=sky_survey,
                    size=size,
                    pixels=600,
                    use_cache=True
                )
                output[target] = {
                    "success": True,
                    "ra": result.ra,
                    "dec": result.dec,
                    "fov_deg": result.fov,
                    "sources_count": len(result.catalog_sources),
                    "cached": result.cached,
                }
            except Exception as e:
                output[target] = {"success": False, "error": str(e)}

        return jsonify({
            "results": output,
            "requested": len(targets),
            "successful": sum(1 for v in output.values() if v.get("success"))
        })

    @app.route("/api/skychart/coordinates", methods=["GET"])
    async def skychart_coordinates():
        """查询目标坐标"""
        if not skychart_available:
            return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503

        target = request.args.get("target", "")
        if not target:
            return jsonify({"error": "未提供目标名称", "code": "NO_TARGET"}), 400

        coords = parse_coordinates_func(target)
        if coords is None:
            return jsonify({
                "error": f"无法解析目标: {target}",
                "code": "TARGET_NOT_FOUND",
                "hint": "请使用梅西耶编号(如M31)或NGC编号(如NGC224)"
            }), 404

        catalog_info = builtin_catalog.get(target.upper(), {})

        return jsonify({
            "target": target,
            "ra": coords[0],
            "dec": coords[1],
            "name": catalog_info.get("name", ""),
            "type": catalog_info.get("type", ""),
            "mag": catalog_info.get("mag", None)
        })

    @app.route("/api/skychart", methods=["GET"])
    async def skychart():
        """获取目标星图 (兼容前端 /api/skychart)"""
        target = request.args.get("target", "M31")

        try:
            if skychart_available:
                result = await get_realtime_skychart_func(target=target)
                return jsonify({
                    "success": True,
                    "target": result.target,
                    "survey": result.survey,
                    "ra": result.ra,
                    "dec": result.dec,
                    "image_url": result.image_url,
                    "cached": result.cached,
                    "timestamp": result.timestamp
                })
        except Exception as e:
            logger.warning(f"[SkyChart] NASA API 调用失败: {e}，返回坐标信息")

        # 降级：返回坐标信息
        coords = parse_coordinates_func(target)
        if coords:
            return jsonify({
                "success": False,
                "target": target,
                "ra": coords[0],
                "dec": coords[1],
                "message": "星图不可用，仅返回坐标"
            })

        return jsonify({"error": f"无法解析目标: {target}"}), 400

    return app