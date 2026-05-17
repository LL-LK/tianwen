"""Routes package for Hermes-AGI
Phase 1 extraction: 2025-05-16
Architecture: server.py -> subpackage route registration
"""
import logging
import asyncio

logger = logging.getLogger("hermes_agi")

__all__ = [
    "register_all_routes",
    "get_loaded_routes",
]

# Track registered routes for diagnostics
_loaded_routes = []


def get_loaded_routes():
    """Return list of registered routes for diagnostics."""
    return list(_loaded_routes)


def register_all_routes(app):
    """Register all subpackage routes with the app.
    
    Architecture: called from server.py _register_subpackage_routes().
    Dependencies are lazy-fetched from server.py globals to avoid
    circular import issues.
    """
    from server.routes.stats import register_stats_routes
    from server.routes.skychart import register_skychart_routes
    from server.routes.data import register_data_routes
    from server.routes.observation import register_observation_routes
    from server.routes.observatory import register_observatory_routes
    from server.routes.other import register_other_routes
    from server.routes.research import register_research_routes
    from server.routes.sessions import register_sessions_routes
    from server.routes.session_route import register_session_routes
    from server.routes.health import register_health_routes
    from server.routes.chat import register_chat_routes
    from server.routes.system import register_system_routes
    from server.routes.telescope import register_telescope_routes
    from server.routes.websocket import register_websocket_routes
    from server.routes.workflow_engine import register_workflow_engine_routes

    # Fetch dependencies from server.py global scope (lazy to avoid circular imports)
    # These are only available after app creation, so we fetch them here at runtime
    import server as _server_module

    observatory_state = getattr(_server_module, "_observatory_state", None)
    lightcurve_data   = getattr(_server_module, "_lightcurve_data", None)
    session_store     = getattr(_server_module, "session_store", None)
    require_api_key  = getattr(_server_module, "require_api_key", None)
    ws_manager        = getattr(_server_module, "ws_manager", None)
    dashboard         = getattr(_server_module, "dashboard", None)
    cycle_history     = getattr(_server_module, "_cycle_history", None)
    hypothesis_tester = getattr(_server_module, "hypothesis_tester", None)
    alerts            = getattr(_server_module, "_alerts", None)
    log_entries       = getattr(_server_module, "_log_entries", None)
    enhancements_avail= getattr(_server_module, "_ENHANCEMENTS_AVAILABLE", False)
    enhancements      = getattr(_server_module, "_enhancements", None)
    state_bridge     = getattr(_server_module, "_state_bridge", None)
    conn_manager     = getattr(_server_module, "_conn_manager", None)
    telescope_client  = getattr(_server_module, "_telescope_client", None)
    connection_type  = getattr(_server_module, "_connection_type", None)
    discovered_devs  = getattr(_server_module, "_discovered_devices", None)
    serial_ports     = getattr(_server_module, "_serial_ports", None)
    skychart_avail  = getattr(_server_module, "_SKYCHART_AVAILABLE", False)
    sky_survey_cls  = getattr(_server_module, "SkySurvey", None)
    get_skychart_fn  = getattr(_server_module, "get_realtime_skychart", None)
    parse_coords_fn  = getattr(_server_module, "parse_coordinates", None)
    builtin_catalog  = getattr(_server_module, "BUILTIN_CATALOG", None)
    workflow_eng_avl = getattr(_server_module, "_WORKFLOW_ENGINE_AVAILABLE", False)
    workflow_engine  = getattr(_server_module, "_workflow_engine", None)

    # Register all route groups
    try:
        register_health_routes(app, session_store=session_store)
        _loaded_routes.append("/api/health")
        _loaded_routes.append("/api/ping")
    except Exception as e:
        logger.warning(f"health routes registration failed: {e}")

    try:
        register_data_routes(app, observatory_state=observatory_state, lightcurve_data=lightcurve_data)
        _loaded_routes.extend(["/api/data/lightcurve", "/api/data/search"])
    except Exception as e:
        logger.warning(f"data routes registration failed: {e}")

    try:
        register_observation_routes(app, observatory_state=observatory_state)
        _loaded_routes.append("/api/observation/sky")
    except Exception as e:
        logger.warning(f"observation routes registration failed: {e}")

    try:
        register_observatory_routes(
            app,
            observatory_state=observatory_state,
            ws_manager=ws_manager,
            log_entries=log_entries,
            state_bridge=state_bridge,
            conn_manager=conn_manager,
        )
        _loaded_routes.extend(["/api/observatory/status", "/api/observatory/connect"])
    except Exception as e:
        logger.warning(f"observatory routes registration failed: {e}")

    try:
        register_other_routes(
            app,
            alerts=alerts,
            log_entries=log_entries,
            ws_manager=ws_manager,
            enhancements_available=enhancements_avail,
            enhancements=enhancements,
        )
        _loaded_routes.extend(["/api/cognitive", "/api/alerts", "/api/logs"])
    except Exception as e:
        logger.warning(f"other routes registration failed: {e}")

    try:
        register_research_routes(
            app,
            observatory_state=observatory_state,
            cycle_history=cycle_history,
            hypothesis_tester=hypothesis_tester,
            require_api_key=require_api_key,
        )
        _loaded_routes.extend(["/api/research/query", "/api/cycle"])
    except Exception as e:
        logger.warning(f"research routes registration failed: {e}")

    try:
        register_stats_routes(
            app,
            ws_manager=ws_manager,
            observatory_state=observatory_state,
            dashboard_data=dashboard,  # dashboard object used as dashboard_data
            require_api_key=require_api_key,
        )
        _loaded_routes.extend(["/api/stats/dashboard", "/api/stats/json"])
    except Exception as e:
        logger.warning(f"stats routes registration failed: {e}")

    try:
        register_sessions_routes(app, session_store=session_store, require_api_key=require_api_key)
        _loaded_routes.extend(["/api/sessions", "/api/sessions/count"])
    except Exception as e:
        logger.warning(f"sessions routes registration failed: {e}")

    try:
        register_session_routes(
            app,
            session_store=session_store,
            require_api_key=require_api_key,
        )
        _loaded_routes.extend(["/api/sessions/session", "/api/sessions/history"])
    except Exception as e:
        logger.warning(f"session_route registration failed: {e}")

    try:
        register_skychart_routes(
            app,
            skychart_available=skychart_avail,
            sky_survey_class=sky_survey_cls,
            get_realtime_skychart_func=get_skychart_fn,
            parse_coordinates_func=parse_coords_fn,
            builtin_catalog=builtin_catalog,
        )
        _loaded_routes.extend(["/api/skychart", "/api/skychart/survey"])
    except Exception as e:
        logger.warning(f"skychart routes registration failed: {e}")

    try:
        register_chat_routes(app)
        _loaded_routes.extend(["/api/chat", "/api/chat/stream"])
    except Exception as e:
        logger.warning(f"chat routes registration failed: {e}")

    try:
        register_system_routes(app, store_type=getattr(_server_module, "_session_store_type", None))
        _loaded_routes.extend(["/api/system/config", "/api/system/debug"])
    except Exception as e:
        logger.warning(f"system routes registration failed: {e}")

    try:
        register_telescope_routes(
            app,
            telescope_client=telescope_client,
            connection_type=connection_type,
            discovered_devices=discovered_devs,
            serial_ports=serial_ports,
            get_telescope_client_func=getattr(_server_module, "_get_telescope_client", None),
            discover_lan_func=getattr(_server_module, "_discover_lan_devices", None),
            detect_serial_func=getattr(_server_module, "_detect_serial_ports", None),
        )
        _loaded_routes.extend(["/api/telescope/status", "/api/telescope/discover"])
    except Exception as e:
        logger.warning(f"telescope routes registration failed: {e}")

    try:
        register_workflow_engine_routes(
            app,
            workflow_engine=workflow_engine,
            available=workflow_eng_avl,
        )
        _loaded_routes.extend(["/api/workflow/execute", "/api/workflow/cancel"])
    except Exception as e:
        logger.warning(f"workflow_engine routes registration failed: {e}")

    try:
        register_websocket_routes(app)
        _loaded_routes.extend(["/ws/realtime", "/ws/agent"])
    except Exception as e:
        logger.warning(f"websocket routes registration failed: {e}")

    logger.info(f"Registered {len(_loaded_routes)} subpackage routes")
    return app
