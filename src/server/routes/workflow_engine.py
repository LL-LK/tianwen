# workflow_engine.py - Workflow engine routes extracted from server.py
# All /api/workflow-engine/* routes

import logging
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")

# Global reference
_workflow_engine = None
_WORKFLOW_ENGINE_AVAILABLE = False


def init_workflow_engine_routes(wfe, available):
    """Initialize global references from parent module"""
    global _workflow_engine, _WORKFLOW_ENGINE_AVAILABLE
    _workflow_engine = wfe
    _WORKFLOW_ENGINE_AVAILABLE = available


# Import require_api_key from parent context
require_api_key = None


def init_auth(require_api_key_fn):
    """Initialize auth decorator from parent module"""
    global require_api_key
    require_api_key = require_api_key_fn


async def get_node_types():
    """获取所有可用节点类型"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503
    return jsonify({"node_types": _workflow_engine.get_node_types()})


async def get_workflow_templates():
    """获取预置工作流模板"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503
    return jsonify({"templates": _workflow_engine.get_templates()})


async def instantiate_template(template_name):
    """从模板实例化工作流"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    data = await request.get_json() or {}
    custom_name = data.get("name", None)

    try:
        result = _workflow_engine.instantiate_template(template_name, custom_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


async def list_workflow_definitions():
    """列出所有工作流定义"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503
    return jsonify({"workflows": _workflow_engine.list_workflows()})


async def save_workflow_definition():
    """创建/更新工作流定义（无代码配置）"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    data = await request.get_json()
    if not data:
        return jsonify({"error": "缺少工作流定义数据"}), 400

    try:
        result = _workflow_engine.create_workflow(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


async def get_workflow_definition(wf_id):
    """获取工作流定义详情"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    wf = _workflow_engine.get_workflow(wf_id)
    if not wf:
        return jsonify({"error": "工作流不存在"}), 404
    return jsonify(wf)


async def delete_workflow_definition(wf_id):
    """删除工作流定义"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    ok = _workflow_engine.delete_workflow(wf_id)
    return jsonify({"deleted": ok})


async def execute_workflow_engine(wf_id):
    """执行工作流"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    data = await request.get_json() or {}
    initial_vars = data.get("variables", {})

    try:
        result = await _workflow_engine.execute_workflow(wf_id, initial_vars)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


async def get_workflow_execution_status(wf_id):
    """获取工作流执行状态（实时）"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    status = _workflow_engine.get_execution_status(wf_id)
    if not status:
        return jsonify({"error": "工作流不存在"}), 404
    return jsonify(status)


async def get_execution_history():
    """获取执行历史"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    limit = int(request.args.get("limit", "20"))
    return jsonify({"history": _workflow_engine.get_execution_history(limit)})


async def get_workflow_statistics():
    """获取工作流引擎统计信息"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503
    return jsonify(_workflow_engine.get_statistics())


async def export_workflow(wf_id):
    """导出工作流为JSON"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    data = _workflow_engine.export_workflow(wf_id)
    if not data:
        return jsonify({"error": "工作流不存在"}), 404
    return jsonify(data)


async def import_workflow():
    """导入工作流"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    data = await request.get_json()
    if not data:
        return jsonify({"error": "缺少工作流数据"}), 400

    try:
        result = _workflow_engine.import_workflow(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


async def cancel_workflow_execution(wf_id):
    """取消正在执行的工作流"""
    if not _WORKFLOW_ENGINE_AVAILABLE:
        return jsonify({"error": "工作流引擎不可用"}), 503

    ok = _workflow_engine.cancel_execution(wf_id)
    return jsonify({"cancelled": ok})


def register_workflow_engine_routes(app, workflow_engine=None, available=False):
    """注册所有工作流引擎路由到app"""
    # Initialize globals
    init_workflow_engine_routes(workflow_engine, available)
    # Node types
    app.add_url_rule("/api/workflow-engine/node-types", "get_node_types", get_node_types, methods=["GET"])

    # Templates
    app.add_url_rule("/api/workflow-engine/templates", "get_workflow_templates", get_workflow_templates, methods=["GET"])
    app.add_url_rule("/api/workflow-engine/templates/<template_name>", "instantiate_template", instantiate_template, methods=["POST"])

    # Workflow definitions
    app.add_url_rule("/api/workflow-engine/workflows", "list_workflow_definitions", list_workflow_definitions, methods=["GET"])
    app.add_url_rule("/api/workflow-engine/workflows", "save_workflow_definition", save_workflow_definition, methods=["POST"])
    app.add_url_rule("/api/workflow-engine/workflows/<wf_id>", "get_workflow_definition", get_workflow_definition, methods=["GET"])
    app.add_url_rule("/api/workflow-engine/workflows/<wf_id>", "delete_workflow_definition", delete_workflow_definition, methods=["DELETE"])

    # Workflow execution
    app.add_url_rule("/api/workflow-engine/workflows/<wf_id>/execute", "execute_workflow_engine", execute_workflow_engine, methods=["POST"])
    app.add_url_rule("/api/workflow-engine/workflows/<wf_id>/status", "get_workflow_execution_status", get_workflow_execution_status, methods=["GET"])

    # Execution history
    app.add_url_rule("/api/workflow-engine/executions/history", "get_execution_history", get_execution_history, methods=["GET"])

    # Statistics
    app.add_url_rule("/api/workflow-engine/statistics", "get_workflow_statistics", get_workflow_statistics, methods=["GET"])

    # Import/Export
    app.add_url_rule("/api/workflow-engine/workflows/<wf_id>/export", "export_workflow", export_workflow, methods=["GET"])
    app.add_url_rule("/api/workflow-engine/import", "import_workflow", import_workflow, methods=["POST"])

    # Cancel execution
    app.add_url_rule("/api/workflow-engine/workflows/<wf_id>/cancel", "cancel_workflow_execution", cancel_workflow_execution, methods=["POST"])