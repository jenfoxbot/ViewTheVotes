import importlib.util, pathlib, sys
p = pathlib.Path(__file__).parents[1] / 'examples' / 'deepagents' / 'web_tools_mcp.py'
print('path=', p)
spec = importlib.util.spec_from_file_location('examples.deepagents.web_tools_mcp', str(p))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('module loaded, attrs:')
for name in ('web_search','fetch_url','http_request','mcp'):
    if hasattr(mod, name):
        obj = getattr(mod, name)
        print(name, '->', type(obj), 'callable=', callable(obj))
        print('  dir sample:', [a for a in dir(obj) if not a.startswith('_')][:30])
    else:
        print(name, 'missing')
