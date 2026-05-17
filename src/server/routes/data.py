"""
Data routes for Hermes-AGI
Extracted from server.py
"""
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_data_routes(app, observatory_state, lightcurve_data):
    """Register data retrieval routes"""

    @app.route("/api/data/detections/latest", methods=["GET"])
    async def data_detections_latest():
        """获取最新检测数据"""
        return jsonify(observatory_state.get("detections", []))

    @app.route("/api/data/images/latest", methods=["GET"])
    async def data_images_latest():
        """获取最新图像"""
        return jsonify(observatory_state.get("latest_image", {}))

    @app.route("/api/data/lightcurve", methods=["GET"])
    async def data_lightcurve():
        """获取光变曲线数据"""
        target = request.args.get("target", "M31")
        return jsonify({"target": target, "data": lightcurve_data})

    @app.route("/api/data/miner", methods=["GET"])
    async def data_miner():
        """数据挖掘分析"""
        target = request.args.get("target", "")
        analysis_type = request.args.get("type", "basic")

        if not target:
            return jsonify({"error": "缺少 target 参数"}), 400

        # Placeholder for data mining functionality
        return jsonify({
            "target": target,
            "type": analysis_type,
            "status": "not_implemented",
            "message": "数据挖掘功能待实现"
        })

    return app