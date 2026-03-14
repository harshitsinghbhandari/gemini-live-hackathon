import ast
import os
import json
from pathlib import Path
import networkx as nx
from graphviz import Digraph

ROOT = Path("packages/aegis")
OUT = Path("docs/aegis_deps")

OUT.mkdir(parents=True, exist_ok=True)

edges = set()

def module_name(file):
    rel = file.relative_to(ROOT)
    parts = list(rel.with_suffix("").parts)
    return "aegis." + ".".join(parts)

def get_group(mod):
    if "agent" in mod: return "Agent"
    if "interfaces" in mod or "browser_manager" in mod or "computer_use" in mod: return "Interfaces"
    if "perception" in mod or "screen" in mod or "cursor" in mod: return "Perception"
    if "tools" in mod: return "Tools"
    return "Aegis Core"

print("Scanning Python files...")

for py in ROOT.rglob("*.py"):
    if py.name == "__init__.py":
        mod = "aegis." + ".".join(py.parent.relative_to(ROOT).parts)
    else:
        mod = module_name(py)

    try:
        with open(py) as f:
            tree = ast.parse(f.read())
    except Exception:
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name.startswith("aegis"):
                    edges.add((mod, name.name))

        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("aegis"):
                edges.add((mod, node.module))

print(f"Found {len(edges)} import edges")

# -------------------------
# Build graph
# -------------------------

G = nx.DiGraph()
G.add_edges_from(edges)

# -------------------------
# Detect cycles
# -------------------------

cycles = list(nx.simple_cycles(G))
cycle_file = OUT / "cycles.txt"

with open(cycle_file, "w") as f:
    if cycles:
        f.write("Circular dependencies:\n\n")
        for c in cycles:
            f.write(" -> ".join(c) + "\n")
    else:
        f.write("No circular imports detected\n")

print("Cycle report saved:", cycle_file)

# -------------------------
# Mermaid graph
# -------------------------

mermaid_file = OUT / "imports.md"
with open(mermaid_file, "w") as f:
    f.write("```mermaid\n")
    f.write("graph TD\n")
    
    groups = {}
    for node in G.nodes():
        grp = get_group(node)
        if grp not in groups: groups[grp] = []
        groups[grp].append(node)
    
    for grp, nodes in groups.items():
        f.write(f"  subgraph {grp.replace(' ', '_')}\n")
        for node in nodes:
            f.write(f'    {node.replace(".", "_")}["{node}"]\n')
        f.write("  end\n")

    for a, b in sorted(edges):
        f.write(f'  {a.replace(".", "_")} --> {b.replace(".", "_")}\n')

    f.write("```\n")

print("Mermaid diagram saved:", mermaid_file)

# -------------------------
# Interactive D3 Graph (index.html)
# -------------------------

d3_nodes = []
node_ids = set()
for node in G.nodes():
    d3_nodes.append({"id": node, "group": get_group(node)})
    node_ids.add(node)

d3_links = []
for a, b in edges:
    if a in node_ids and b in node_ids:
        d3_links.append({"source": a, "target": b})

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Aegis Interactive Dependency Graph</title>
    <style>
        body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #1a1a1a; color: white; overflow: hidden; }}
        svg {{ width: 100vw; height: 100vh; }}
        .link {{ stroke: #555; stroke-opacity: 0.6; stroke-width: 1.5px; marker-end: url(#arrowhead); transition: opacity 0.3s; }}
        .node circle {{ stroke: #fff; stroke-width: 1.5px; cursor: grab; transition: opacity 0.3s, r 0.3s; }}
        .node text {{ pointer-events: none; font-size: 10px; fill: #eee; transition: opacity 0.3s; }}
        
        .panel {{ position: absolute; background: rgba(0,0,0,0.85); padding: 15px; border-radius: 8px; border: 1px solid #444; backdrop-filter: blur(5px); display: flex; flex-direction: column; }}
        .legend {{ top: 20px; right: 20px; width: 150px; }}
        .wizard {{ top: 20px; left: 20px; width: 320px; max-height: 80vh; }}
        
        .legend-item {{ display: flex; align-items: center; margin-bottom: 5px; font-size: 12px; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 10px; }}
        
        h2 {{ margin: 0 0 10px 0; font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
        
        input[type="text"] {{ width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #444; background: #222; color: white; box-sizing: border-box; margin-bottom: 5px; }}
        .results {{ max-height: 200px; overflow-y: auto; list-style: none; padding: 0; margin: 0; border: 1px solid #333; display: none; background: #222; border-radius: 4px; z-index: 10; }}
        .results li {{ padding: 8px; cursor: pointer; font-size: 13px; border-bottom: 1px solid #333; }}
        .results li:hover {{ background: #333; }}
        
        .selection-area {{ margin-top: 15px; flex-grow: 1; overflow-y: auto; }}
        .tag-list {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }}
        .tag {{ background: #34495e; color: #ecf0f1; padding: 4px 8px; border-radius: 4px; font-size: 11px; display: flex; align-items: center; }}
        .tag .remove {{ margin-left: 8px; cursor: pointer; color: #bdc3c7; font-weight: bold; }}
        .tag .remove:hover {{ color: #e74c3c; }}

        .btn {{ padding: 8px 12px; background: #3498db; border: none; border-radius: 4px; color: white; cursor: pointer; font-size: 12px; width: 100%; margin-top: 5px; }}
        .btn:hover {{ background: #2980b9; }}
        .btn-reset {{ background: #e74c3c; }}
        .btn-reset:hover {{ background: #c0392b; }}
        
        .highlight circle {{ r: 12; stroke: #f1c40f; stroke-width: 3px; }}
    </style>
</head>
<body>
    <div class="panel wizard">
        <h2>Isolation Wizard</h2>
        <input type="text" id="node-search" placeholder="Search for nodes to isolate...">
        <ul id="search-results" class="results"></ul>
        
        <div class="selection-area">
            <h2 style="font-size: 11px;">Active Filters</h2>
            <div id="active-tags" class="tag-list">
                <!-- Tags added here -->
            </div>
            <div id="selection-info" style="font-size: 11px; color: #888; display: none;">
                Showing selected nodes and their combined direct neighbors.
            </div>
        </div>
        
        <button class="btn btn-reset" id="reset-btn" style="display: none;">Reset Full View</button>
    </div>

    <div class="panel legend">
        <h2>Layers</h2>
        <div id="legend-content"></div>
    </div>

    <svg>
        <defs>
            <marker id="arrowhead" viewBox="-0 -5 10 10" refX="25" refY="0" orient="auto" markerWidth="6" markerHeight="6" xoverflow="visible">
                <path d="M 0,-5 L 10 ,0 L 0,5" fill="#555" style="stroke: none;"></path>
            </marker>
        </defs>
    </svg>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const data = {{
            nodes: {nodes_json},
            links: {links_json}
        }};

        const svg = d3.select("svg");
        const width = window.innerWidth;
        const height = window.innerHeight;

        const color = d3.scaleOrdinal(d3.schemeCategory10);
        
        const groups = Array.from(new Set(data.nodes.map(d => d.group))).sort();
        const legend = d3.select("#legend-content");
        groups.forEach(g => {{
            const item = legend.append("div").attr("class", "legend-item");
            item.append("div").attr("class", "legend-color").style("background", color(g));
            item.append("div").text(g);
        }});

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(120))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide(50));

        const link = svg.append("g")
            .selectAll("line")
            .data(data.links)
            .join("line")
            .attr("class", "link");

        const node = svg.append("g")
            .selectAll("g")
            .data(data.nodes)
            .join("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended)
            );

        node.append("circle")
            .attr("r", 9)
            .attr("fill", d => color(d.group));

        node.append("text")
            .text(d => d.id.replace("aegis.", ""))
            .attr("x", 14)
            .attr("y", 4);

        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});

        // --- Multi-Node Isolation Logic ---
        
        const selectedNodes = new Set();
        const searchInput = document.getElementById('node-search');
        const searchResults = document.getElementById('search-results');
        const activeTags = document.getElementById('active-tags');
        const resetBtn = document.getElementById('reset-btn');
        const selectionInfo = document.getElementById('selection-info');

        searchInput.addEventListener('input', (e) => {{
            const val = e.target.value.toLowerCase();
            if (!val) {{
                searchResults.style.display = 'none';
                return;
            }}
            const filtered = data.nodes.filter(n => n.id.toLowerCase().includes(val) && !selectedNodes.has(n.id)).slice(0, 8);
            if (filtered.length > 0) {{
                searchResults.innerHTML = filtered.map(n => `<li data-id="${{n.id}}">${{n.id.replace('aegis.', '')}}</li>`).join('');
                searchResults.style.display = 'block';
                searchResults.querySelectorAll('li').forEach(li => {{
                    li.addEventListener('click', () => addNode(li.getAttribute('data-id')));
                }});
            }} else {{
                searchResults.style.display = 'none';
            }}
        }});

        function addNode(nodeId) {{
            selectedNodes.add(nodeId);
            searchInput.value = '';
            searchResults.style.display = 'none';
            renderTags();
            updateVisibility();
        }}

        function removeNode(nodeId) {{
            selectedNodes.delete(nodeId);
            renderTags();
            updateVisibility();
        }}

        function renderTags() {{
            activeTags.innerHTML = Array.from(selectedNodes).map(id => `
                <div class="tag">
                    ${{id.replace('aegis.', '')}}
                    <span class="remove" onclick="removeNode('${{id}}')">×</span>
                </div>
            `).join('');
            
            const hasSelection = selectedNodes.size > 0;
            resetBtn.style.display = hasSelection ? 'block' : 'none';
            selectionInfo.style.display = hasSelection ? 'block' : 'none';
        }}

        function updateVisibility() {{
            if (selectedNodes.size === 0) {{
                node.style("opacity", 1).classed("highlight", false);
                link.style("opacity", 1);
                return;
            }}

            // Find all nodes to show: selected + direct neighbors
            const visibleNodes = new Set(selectedNodes);
            data.links.forEach(l => {{
                const s = typeof l.source === 'string' ? l.source : l.source.id;
                const t = typeof l.target === 'string' ? l.target : l.target.id;
                if (selectedNodes.has(s)) visibleNodes.add(t);
                if (selectedNodes.has(t)) visibleNodes.add(s);
            }});

            node.style("opacity", d => visibleNodes.has(d.id) ? 1 : 0.08)
                .classed("highlight", d => selectedNodes.has(d.id));
                
            link.style("opacity", d => {{
                const s = typeof d.source === 'string' ? d.source : d.source.id;
                const t = typeof d.target === 'string' ? d.target : d.target.id;
                return (selectedNodes.has(s) || selectedNodes.has(t)) ? 1 : 0.05;
            }});
        }}

        resetBtn.addEventListener('click', () => {{
            selectedNodes.clear();
            renderTags();
            updateVisibility();
            searchInput.value = '';
        }});

        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        window.addEventListener("resize", () => {{
            const w = window.innerWidth;
            const h = window.innerHeight;
            svg.attr("width", w).attr("height", h);
            simulation.force("center", d3.forceCenter(w / 2, h / 2)).restart();
        }});
    </script>
</body>
</html>
"""

index_html = html_template.format(
    nodes_json=json.dumps(d3_nodes, indent=4),
    links_json=json.dumps(d3_links, indent=4)
)

with open(OUT / "index.html", "w") as f:
    f.write(index_html)

print("Interactive D3 graph saved:", OUT / "index.html")

print("\nDone.")