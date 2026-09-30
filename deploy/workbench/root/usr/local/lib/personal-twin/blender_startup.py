import bpy

_attempts = 0

def ensure_mcp_started():
    global _attempts
    _attempts += 1
    try:
        addon = bpy.context.preferences.addons.get("bl_ext.user_default.mcp")
        if addon is None:
            if _attempts < 10:
                return 1.0
            print("[personal-twin] Blender MCP extension is not enabled")
            return None
        result = bpy.ops.blmcp.server_start()
        print(f"[personal-twin] Blender MCP start result: {result}")
        return None
    except Exception as exc:
        print(f"[personal-twin] Blender MCP start attempt {_attempts} failed: {exc}")
        if _attempts < 10:
            return 1.0
        return None

bpy.app.timers.register(ensure_mcp_started, first_interval=2.0)
