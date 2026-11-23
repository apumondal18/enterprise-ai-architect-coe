import inspect
import importlib.util
import importlib

spec = importlib.util.spec_from_file_location(
    "mcp_factory",
    r"C:\Python\python312\Lib\site-packages\mcp\shared\_httpx_utils.py"
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

print(inspect.getsource(module.create_mcp_http_client))

print("++++++++++++++++++++++++++++++++++")
print(inspect.getsourcefile(module.create_mcp_http_client))


print("Module:", module)
print("Default timeout:", getattr(module, "MCP_DEFAULT_TIMEOUT", "Not found"))
print("Default SSE read timeout:",
      getattr(module, "MCP_DEFAULT_SSE_READ_TIMEOUT", "Not found"))

#print("MCP_DEFAULT_TIMEOUT:", MCP_DEFAULT_TIMEOUT)

#print("MCP_DEFAULT_SSE_READ_TIMEOUT:", MCP_DEFAULT_SSE_READ_TIMEOUT)