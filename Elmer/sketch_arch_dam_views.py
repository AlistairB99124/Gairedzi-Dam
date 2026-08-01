from __future__ import annotations

from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


def read_gmsh_nodes(mesh_path: Path) -> list[tuple[float, float, float]]:
    lines = mesh_path.read_text().splitlines()
    start = lines.index("$Nodes")
    count = int(lines[start + 1])
    node_lines = lines[start + 2 : start + 2 + count]
    nodes: list[tuple[float, float, float]] = []
    for line in node_lines:
        parts = line.split()
        nodes.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return nodes


def read_mesh_metadata(mesh_path: Path) -> dict[str, int]:
    meta_path = mesh_path.with_name(f"{mesh_path.stem}_meta.json")
    if not meta_path.exists():
        return {"station_count": len(read_gmsh_nodes(mesh_path)) // 4, "vertical_layers": 1, "thickness_layers": 1}
    return json.loads(meta_path.read_text())


def split_stations(nodes: list[tuple[float, float, float]], vertical_layers: int = 1, thickness_layers: int = 1) -> list[dict[str, tuple[float, float, float]]]:
    nodes_per_level = thickness_layers + 1
    nodes_per_station = (vertical_layers + 1) * nodes_per_level
    if len(nodes) % nodes_per_station != 0:
        raise ValueError("Node count does not match structured station layout")

    stations: list[dict[str, tuple[float, float, float]]] = []
    for i in range(0, len(nodes), nodes_per_station):
        top_offset = vertical_layers * nodes_per_level
        stations.append(
            {
                "inner_base": nodes[i],
                "outer_base": nodes[i + thickness_layers],
                "inner_top": nodes[i + top_offset],
                "outer_top": nodes[i + top_offset + thickness_layers],
            }
        )
    return stations


def load_station_edges(mesh_path: Path) -> list[dict[str, tuple[float, float, float]]]:
    metadata = read_mesh_metadata(mesh_path)
    nodes = read_gmsh_nodes(mesh_path)
    return split_stations(
        nodes,
        int(metadata.get("vertical_layers", 1)),
        int(metadata.get("thickness_layers", 1)),
    )


def xyz(points: list[tuple[float, float, float]]) -> tuple[list[float], list[float], list[float]]:
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    z = [p[2] for p in points]
    return x, y, z


def plot_views(mesh_path: Path, out_path: Path) -> None:
    stations = load_station_edges(mesh_path)

    inner_base = [s["inner_base"] for s in stations]
    outer_base = [s["outer_base"] for s in stations]
    inner_top = [s["inner_top"] for s in stations]
    outer_top = [s["outer_top"] for s in stations]

    fig = plt.figure(figsize=(14, 10), dpi=180)
    fig.suptitle("Arch Dam Orientation Sketches", fontsize=16, fontweight="bold")

    ax1 = fig.add_subplot(2, 2, 1)
    x_ib, y_ib, _ = xyz(inner_base)
    x_ob, y_ob, _ = xyz(outer_base)
    ax1.plot(x_ib, y_ib, "k-", linewidth=1.8, label="Inner face")
    ax1.plot(x_ob, y_ob, "k-", linewidth=1.8, label="Outer face")
    for a, b in zip(inner_base[::5], outer_base[::5]):
        ax1.plot([a[0], b[0]], [a[1], b[1]], color="0.35", linewidth=0.9)
    ax1.set_title("Plan View (X-Y)")
    ax1.set_xlabel("X (m)")
    ax1.set_ylabel("Y (m)")
    ax1.axis("equal")
    ax1.grid(True, color="0.9", linewidth=0.6)
    ax1.legend(frameon=False)

    ax2 = fig.add_subplot(2, 2, 2)
    x_it, _, z_it = xyz(inner_top)
    x_ot, _, z_ot = xyz(outer_top)
    x_ib, _, z_ib = xyz(inner_base)
    x_ob, _, z_ob = xyz(outer_base)
    ax2.plot(x_ib, z_ib, "k-", linewidth=1.5)
    ax2.plot(x_ob, z_ob, "k-", linewidth=1.5)
    ax2.plot(x_it, z_it, "k--", linewidth=1.2)
    ax2.plot(x_ot, z_ot, "k--", linewidth=1.2)
    for ib, it, ob, ot in zip(inner_base[::5], inner_top[::5], outer_base[::5], outer_top[::5]):
        ax2.plot([ib[0], it[0]], [ib[2], it[2]], color="0.4", linewidth=0.8)
        ax2.plot([ob[0], ot[0]], [ob[2], ot[2]], color="0.4", linewidth=0.8)
    ax2.set_title("Elevation View (X-Z)")
    ax2.set_xlabel("X (m)")
    ax2.set_ylabel("Z (m)")
    ax2.grid(True, color="0.9", linewidth=0.6)

    ax3 = fig.add_subplot(2, 2, 3)
    _, y_it, z_it = xyz(inner_top)
    _, y_ot, z_ot = xyz(outer_top)
    _, y_ib, z_ib = xyz(inner_base)
    _, y_ob, z_ob = xyz(outer_base)
    ax3.plot(y_ib, z_ib, "k-", linewidth=1.5)
    ax3.plot(y_ob, z_ob, "k-", linewidth=1.5)
    ax3.plot(y_it, z_it, "k--", linewidth=1.2)
    ax3.plot(y_ot, z_ot, "k--", linewidth=1.2)
    for ib, it, ob, ot in zip(inner_base[::5], inner_top[::5], outer_base[::5], outer_top[::5]):
        ax3.plot([ib[1], it[1]], [ib[2], it[2]], color="0.4", linewidth=0.8)
        ax3.plot([ob[1], ot[1]], [ob[2], ot[2]], color="0.4", linewidth=0.8)
    ax3.set_title("Elevation View (Y-Z)")
    ax3.set_xlabel("Y (m)")
    ax3.set_ylabel("Z (m)")
    ax3.grid(True, color="0.9", linewidth=0.6)

    ax4 = fig.add_subplot(2, 2, 4, projection="3d")
    for edge in (inner_base, outer_base, inner_top, outer_top):
        x, y, z = xyz(edge)
        ax4.plot(x, y, z, color="k", linewidth=1.4)
    for ib, ob, it, ot in zip(inner_base[::5], outer_base[::5], inner_top[::5], outer_top[::5]):
        ax4.plot([ib[0], ob[0]], [ib[1], ob[1]], [ib[2], ob[2]], color="0.35", linewidth=0.8)
        ax4.plot([it[0], ot[0]], [it[1], ot[1]], [it[2], ot[2]], color="0.35", linewidth=0.8)
        ax4.plot([ib[0], it[0]], [ib[1], it[1]], [ib[2], it[2]], color="0.35", linewidth=0.8)
        ax4.plot([ob[0], ot[0]], [ob[1], ot[1]], [ob[2], ot[2]], color="0.35", linewidth=0.8)
    ax4.set_title("Isometric Sketch")
    ax4.set_xlabel("X (m)")
    ax4.set_ylabel("Y (m)")
    ax4.set_zlabel("Z (m)")
    ax4.view_init(elev=24, azim=-58)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)

    svg_path = out_path.with_suffix(".svg")
    fig.savefig(svg_path)
    plt.close(fig)

    print(f"Wrote {out_path}")
    print(f"Wrote {svg_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create architect-style orientation sketches for the arch dam mesh.")
    parser.add_argument(
        "--mesh",
        type=Path,
        default=Path(__file__).resolve().parent / "curved_dam_mesh.msh",
        help="Path to Gmsh mesh file",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "results" / "arch_dam_orientations.png",
        help="Output image path",
    )
    args = parser.parse_args()

    plot_views(args.mesh, args.out)


if __name__ == "__main__":
    main()
