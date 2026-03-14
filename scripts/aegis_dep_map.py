import ast
import os
from pathlib import Path
import networkx as nx
from graphviz import Digraph

ROOT = Path("packages/aegis")
OUT = Path("docs/aegis_deps")

OUT.mkdir(parents=True, exist_ok=True)

edges = set()

def module_name(file):
    rel = file.relative_to(ROOT)
    return ".".join(rel.with_suffix("").parts)

def top_package(mod):
    parts = mod.split(".")
    return parts[0]

print("Scanning Python files...")

for py in ROOT.rglob("*.py"):
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

    for a, b in sorted(edges):
        f.write(f'"{a}" --> "{b}"\n')

    f.write("```\n")

print("Mermaid diagram saved:", mermaid_file)

# -------------------------
# Graphviz graph
# -------------------------

dot = Digraph(comment="Aegis Imports")

for a, b in edges:
    dot.edge(a, b)

svg_file = OUT / "imports_graph"

dot.render(svg_file, format="svg", cleanup=True)

print("Graphviz graph saved:", svg_file.with_suffix(".svg"))

# -------------------------
# Package-level architecture
# -------------------------

pkg_edges = set()

for a, b in edges:

    a_pkg = top_package(a)
    b_pkg = top_package(b)

    if a_pkg != b_pkg:
        pkg_edges.add((a_pkg, b_pkg))

pkg_dot = Digraph(comment="Aegis Package Architecture")

for a, b in pkg_edges:
    pkg_dot.edge(a, b)

pkg_file = OUT / "architecture"

pkg_dot.render(pkg_file, format="svg", cleanup=True)

print("Architecture graph saved:", pkg_file.with_suffix(".svg"))

print("\nDone.")