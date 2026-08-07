from pathlib import Path
import csv
import json
import math


root = Path(__file__).resolve().parent.parent
input_path = root / "Data" / "Dam_Base_Contours.json"
grid_controls_path = root / "Data" / "Computational_Grid_Controls.json"
out_dir = Path(__file__).resolve().parent

with input_path.open() as fh:
    data = json.load(fh)

with grid_controls_path.open() as fh:
    grid_controls = json.load(fh)


def get_grid_control_value(control_name):
    for row in grid_controls:
        if row.get("Mesh Control") == control_name:
            return float(row["Client Value"])
    raise ValueError(f"Missing mesh control '{control_name}' in {grid_controls_path}")

radius = 80.0
wall_thickness = 4.0
dam_height = 30.0
mesh_size = get_grid_control_value("Global Element Size")
target_block_size = mesh_size
arch_subdivisions = 3
vertical_layers = 4
thickness_layers = max(1, int(round(wall_thickness / target_block_size)))
crest_detail_height = 2.0
crest_extra_thickness = 1.0
abutment_segment_count = 6


def interpolate_profile_points(profile_points, subdivisions):
    refined = []
    for index in range(len(profile_points) - 1):
        start = profile_points[index]
        end = profile_points[index + 1]
        for step in range(subdivisions):
            fraction = step / subdivisions
            refined.append(
                {
                    "station": start["station"] + fraction * (end["station"] - start["station"]),
                    "theta": start["theta"] + fraction * (end["theta"] - start["theta"]),
                    "x": start["x"] + fraction * (end["x"] - start["x"]),
                    "y": start["y"] + fraction * (end["y"] - start["y"]),
                    "base_z": start["base_z"] + fraction * (end["base_z"] - start["base_z"]),
                    "crest_z": start["crest_z"] + fraction * (end["crest_z"] - start["crest_z"]),
                }
            )
    refined.append(profile_points[-1].copy())
    return refined


def interpolate_profile_points_by_target_spacing(profile_points, target_spacing_m):
    if len(profile_points) < 2:
        return profile_points

    start_station = profile_points[0]["station"]
    end_station = profile_points[-1]["station"]
    if end_station <= start_station:
        return profile_points

    resampled_stations = [start_station]
    station = start_station + target_spacing_m
    while station < end_station:
        resampled_stations.append(station)
        station += target_spacing_m
    if resampled_stations[-1] != end_station:
        resampled_stations.append(end_station)

    refined = []
    segment_index = 0
    for sample_station in resampled_stations:
        while (
            segment_index < len(profile_points) - 2
            and sample_station > profile_points[segment_index + 1]["station"]
        ):
            segment_index += 1

        start = profile_points[segment_index]
        end = profile_points[segment_index + 1]
        delta_station = end["station"] - start["station"]
        if abs(delta_station) < 1.0e-12:
            fraction = 0.0
        else:
            fraction = (sample_station - start["station"]) / delta_station

        refined.append(
            {
                "station": sample_station,
                "theta": start["theta"] + fraction * (end["theta"] - start["theta"]),
                "x": start["x"] + fraction * (end["x"] - start["x"]),
                "y": start["y"] + fraction * (end["y"] - start["y"]),
                "base_z": start["base_z"] + fraction * (end["base_z"] - start["base_z"]),
                "crest_z": start["crest_z"] + fraction * (end["crest_z"] - start["crest_z"]),
            }
        )

    return refined


def assign_normals(profile_points):
    centerline = [(point["x"], point["y"]) for point in profile_points]
    for index, point in enumerate(profile_points):
        if index == 0:
            tx, ty = centerline[1][0] - centerline[0][0], centerline[1][1] - centerline[0][1]
        elif index == len(profile_points) - 1:
            tx, ty = centerline[-1][0] - centerline[-2][0], centerline[-1][1] - centerline[-2][1]
        else:
            tx, ty = centerline[index + 1][0] - centerline[index - 1][0], centerline[index + 1][1] - centerline[index - 1][1]
        length = math.hypot(tx, ty)
        if length < 1.0e-8:
            tx, ty = 1.0, 0.0
            length = 1.0
        point["nx"] = -ty / length
        point["ny"] = tx / length


def section_pair(point, vertical_fraction, thickness_fraction):
    z_value = point["base_z"] + vertical_fraction * (point["crest_z"] - point["base_z"])
    detail_start_z = point["crest_z"] - crest_detail_height
    detail_fraction = 0.0
    if z_value > detail_start_z:
        detail_fraction = min((z_value - detail_start_z) / crest_detail_height, 1.0)
    local_thickness = wall_thickness + crest_extra_thickness * detail_fraction
    half_thickness = local_thickness * 0.5
    thickness_offset = -half_thickness + thickness_fraction * local_thickness
    x_value = point["x"] + point["nx"] * thickness_offset
    y_value = point["y"] + point["ny"] * thickness_offset
    return (x_value, y_value, z_value)


rows = []
seen = set()
for row in data:
    station = float(row["chainage"])
    if station in seen:
        continue
    seen.add(station)
    rows.append(row)

rows.sort(key=lambda row: float(row["chainage"]))
if len(rows) < 3:
    raise ValueError("Need at least three unique contour points to build the dam geometry")

crest_elevation = dam_height
profile_points = []
for row in rows:
    station = float(row["chainage"])
    theta = station / radius
    base_z = crest_elevation - float(row["height"])
    profile_points.append(
        {
            "station": station,
            "theta": theta,
            "x": radius * math.sin(theta),
            "y": radius * math.cos(theta),
            "base_z": base_z,
            "crest_z": crest_elevation,
        }
    )

points = interpolate_profile_points_by_target_spacing(profile_points, target_block_size)
if len(points) <= len(profile_points):
    points = interpolate_profile_points(profile_points, arch_subdivisions)
assign_normals(points)

local_heights = [point["crest_z"] - point["base_z"] for point in points]
average_height = sum(local_heights) / len(local_heights)
vertical_layers = max(1, int(round(average_height / target_block_size)))

csv_path = out_dir / "curved_dam_centerline.csv"
with csv_path.open("w", newline="") as fh:
    writer = csv.writer(fh)
    writer.writerow(["station", "x", "y", "z_base", "z_crest"])
    for point in points:
        writer.writerow([point["station"], point["x"], point["y"], point["base_z"], point["crest_z"]])

geo_path = out_dir / "curved_dam_geometry.geo"
mesh_path = out_dir / "curved_dam_mesh.msh"
meta_path = out_dir / "curved_dam_mesh_meta.json"

with geo_path.open("w") as fh:
    fh.write("// Curved dam wall generated as a swept solid with a rectangular cross-section\n")
    fh.write('SetFactory("OpenCASCADE");\n')
    fh.write(f"meshSize = {mesh_size};\n")
    fh.write(f"wallThick = {wall_thickness};\n")
    fh.write(f"damHeight = {dam_height};\n")
    fh.write(f"archSubdivisions = {arch_subdivisions};\n")
    fh.write(f"verticalLayers = {vertical_layers};\n")
    fh.write(f"thicknessLayers = {thickness_layers};\n")
    fh.write(f"crestDetailHeight = {crest_detail_height};\n")
    fh.write(f"crestExtraThickness = {crest_extra_thickness};\n")
    fh.write(f"abutmentSegmentCount = {abutment_segment_count};\n")
    fh.write(f"crestZ = {crest_elevation:.6f};\n")

    point_counter = 0
    for point in points:
        for vertical_fraction in (0.0, 1.0):
            for thickness_fraction in (0.0, 1.0):
                node = section_pair(point, vertical_fraction, thickness_fraction)
                point_counter += 1
                fh.write(f"Point({point_counter}) = {{{node[0]:.6f}, {node[1]:.6f}, {node[2]:.6f}, meshSize}};\n")

node_list = []
station_node_ids = []
for point in points:
    level_pairs = []
    for layer_index in range(vertical_layers + 1):
        vertical_fraction = layer_index / vertical_layers
        thickness_ids = []
        for thickness_index in range(thickness_layers + 1):
            thickness_fraction = thickness_index / thickness_layers
            node = section_pair(point, vertical_fraction, thickness_fraction)
            node_list.append(node)
            thickness_ids.append(len(node_list))
        level_pairs.append(thickness_ids)
    station_node_ids.append(level_pairs)

with mesh_path.open("w") as mesh_file:
    mesh_file.write("$MeshFormat\n")
    mesh_file.write("2.2 0 8\n")
    mesh_file.write("$EndMeshFormat\n")
    mesh_file.write("$Nodes\n")
    mesh_file.write(f"{len(node_list)}\n")
    for index, (x, y, z) in enumerate(node_list, start=1):
        mesh_file.write(f"{index} {x:.6f} {y:.6f} {z:.6f}\n")
    mesh_file.write("$EndNodes\n")
    mesh_file.write("$Elements\n")

    segment_count = len(points) - 1
    volume_count = segment_count * vertical_layers * thickness_layers
    boundary_count = 2 * segment_count * thickness_layers + 2 * segment_count * vertical_layers
    mesh_file.write(f"{volume_count + boundary_count}\n")

    element_index = 1
    for segment_index in range(segment_count):
        for layer_index in range(vertical_layers):
            for thickness_index in range(thickness_layers):
                a0 = station_node_ids[segment_index][layer_index][thickness_index]
                a1 = station_node_ids[segment_index][layer_index][thickness_index + 1]
                b0 = station_node_ids[segment_index + 1][layer_index][thickness_index]
                b1 = station_node_ids[segment_index + 1][layer_index][thickness_index + 1]
                a0_top = station_node_ids[segment_index][layer_index + 1][thickness_index]
                a1_top = station_node_ids[segment_index][layer_index + 1][thickness_index + 1]
                b0_top = station_node_ids[segment_index + 1][layer_index + 1][thickness_index]
                b1_top = station_node_ids[segment_index + 1][layer_index + 1][thickness_index + 1]

                hex_nodes = [a0, a1, b1, b0, a0_top, a1_top, b1_top, b0_top]
                mesh_file.write(f"{element_index} 5 2 1 1")
                for node_id in hex_nodes:
                    mesh_file.write(f" {node_id}")
                mesh_file.write("\n")
                element_index += 1

                upstream_bc = 2
                downstream_bc = 3
                if segment_index < abutment_segment_count:
                    upstream_bc = 5
                    downstream_bc = 5
                elif segment_index >= segment_count - abutment_segment_count:
                    upstream_bc = 6
                    downstream_bc = 6

                if thickness_index == 0:
                    mesh_file.write(f"{element_index} 3 2 {upstream_bc} {upstream_bc} {a0} {b0} {b0_top} {a0_top}\n")
                    element_index += 1
                if thickness_index == thickness_layers - 1:
                    mesh_file.write(f"{element_index} 3 2 {downstream_bc} {downstream_bc} {a1} {a1_top} {b1_top} {b1}\n")
                    element_index += 1

                if layer_index == 0:
                    mesh_file.write(f"{element_index} 3 2 1 1 {a0} {a1} {b1} {b0}\n")
                    element_index += 1
                if layer_index == vertical_layers - 1:
                    mesh_file.write(f"{element_index} 3 2 4 4 {a0_top} {b0_top} {b1_top} {a1_top}\n")
                    element_index += 1

    mesh_file.write("$EndElements\n")

meta_path.write_text(
    json.dumps(
        {
            "station_count": len(points),
            "vertical_layers": vertical_layers,
            "arch_subdivisions": arch_subdivisions,
            "wall_thickness_m": wall_thickness,
            "dam_height_m": dam_height,
            "mesh_size_m": mesh_size,
            "target_block_size_m": target_block_size,
            "thickness_layers": thickness_layers,
            "crest_detail_height_m": crest_detail_height,
            "crest_extra_thickness_m": crest_extra_thickness,
            "abutment_segment_count": abutment_segment_count,
        },
        indent=2,
    )
)

print(f"Wrote {csv_path}")
print(f"Wrote {geo_path}")
print(f"Wrote {mesh_path}")
print(f"Wrote {meta_path}")
print(f"Generated {len(points)} stations, {volume_count} hex elements, and {boundary_count} boundary faces")
