"""
Observation routes for Hermes-AGI
Extracted from server.py
"""
import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")


def register_observation_routes(app, observatory_state):
    """Register observation data routes"""

    @app.route("/api/observation/data", methods=["GET"])
    async def observation_data():
        """获取观测数据"""
        target = request.args.get("target", "")
        instrument = request.args.get("instrument", "all")
        limit = int(request.args.get("limit", 100))

        observations = observatory_state.get("observations", [])

        if target:
            observations = [o for o in observations if o.get("target") == target]

        if instrument != "all":
            observations = [o for o in observations if o.get("instrument") == instrument]

        return jsonify({
            "observations": observations[:limit],
            "total": len(observations),
            "target": target or "all"
        })

    return app