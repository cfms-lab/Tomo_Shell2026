import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfms_tomo.shell_test.tomoSh_Cpp import tomoSh_Cpp
from cfms_tomo.shell_test.tomoSh_io_trimesh import g_PixelEnums, g_PixelVarNames, toRadian


def export_mesh(mesh, out_dir, name):
    path = out_dir / f"{name}.stl"
    mesh.export(path)
    return path


def cut_with_plane(mesh, out_dir, name, normal, cap):
    normal = np.asarray(normal, dtype=np.float64)
    normal /= np.linalg.norm(normal)
    cut = mesh.slice_plane(plane_origin=(0, 0, 0), plane_normal=normal, cap=cap)
    cut.remove_unreferenced_vertices()
    return export_mesh(cut, out_dir, name), cut


def keep_positive_z_faces(mesh, out_dir, name, cap=False):
    return cut_with_plane(mesh, out_dir, name, (0, 0, 1), cap)


def keep_halfspace_faces(mesh, out_dir, name, normal, cap=False):
    return cut_with_plane(mesh, out_dir, name, normal, cap)


def run_tomo(path, shell_mesh, theta_deg, step_deg, shell_thickness, collect_pixels=False):
    yaw = np.linspace(
        0,
        2 * np.pi,
        int(360 / step_deg) + 1,
        endpoint=True,
        dtype=np.float32,
    )
    pitch = yaw.copy()
    roll = np.zeros(1, dtype=np.float32)

    tomo = tomoSh_Cpp(str(path), len(yaw), yaw, pitch, roll, collect_pixels)
    tomo.bShellMesh = shell_mesh
    tomo.ShellThickness = shell_thickness
    tomo.theta_c = toRadian(theta_deg)
    tomo.BedType = (0, 0.0, 0.0, 0.0)
    tomo.Run("TomoSh_INT3")
    return tomo.Mss3D.reshape(len(yaw), len(pitch)), tomo


def run_tomo_grid(path, shell_mesh, theta_deg, step_deg):
    grid, _ = run_tomo(path, shell_mesh, theta_deg, step_deg, shell_thickness=0.5, collect_pixels=False)
    return grid


def print_pixel_summary(tomo):
    print("pixel summary for rendered optimal orientation:")
    for enum_name, var_name in zip(g_PixelEnums, g_PixelVarNames):
        pxls = getattr(tomo, var_name, None)
        if pxls is None or pxls.size == 0 or (pxls.shape == (1, 6) and np.all(pxls == 0)):
            print(f"  {enum_name:7s} count=0 zsum=0")
            continue
        print(
            f"  {enum_name:7s} count={len(pxls):6d} "
            f"zsum={int(np.sum(pxls[:, 2])):8d} "
            f"nzmin={int(np.min(pxls[:, 5])):5d} nzmax={int(np.max(pxls[:, 5])):5d}"
        )


def nonempty_pixels(tomo, var_name):
    pxls = getattr(tomo, var_name, None)
    if pxls is None or pxls.size == 0:
        return np.empty((0, 6), dtype=np.int16)
    if pxls.shape == (1, 6) and np.all(pxls == 0):
        return np.empty((0, 6), dtype=np.int16)
    return pxls


def add_slot_terms(terms, pxls, name, sign):
    for pxl in pxls:
        key = (int(pxl[0]), int(pxl[1]))
        slot_terms = terms.setdefault(
            key,
            {"Al": 0, "Be": 0, "TC": 0, "NVB": 0, "NVA": 0, "Vss": 0},
        )
        z = int(pxl[2])
        slot_terms[name] += z
        slot_terms["Vss"] += sign * z


def boundary_slots(mesh, mat4x4=None):
    boundary_edge_ids = trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1)
    if len(boundary_edge_ids) == 0:
        return set()

    vertex_ids = np.unique(mesh.edges[boundary_edge_ids].reshape(-1))
    points = np.asarray(mesh.vertices[vertex_ids], dtype=np.float64)
    if mat4x4 is not None:
        points_h = np.column_stack((points, np.ones(len(points))))
        points = (points_h @ np.asarray(mat4x4, dtype=np.float64).T)[:, :3]
    points = points + 0.001

    slots = set()
    for point in points:
        x0 = int(np.floor(point[0])) - 1
        y0 = int(np.floor(point[1])) - 1
        for dx in range(3):
            for dy in range(3):
                slots.add((x0 + dx, y0 + dy))
    return slots


def print_slot_summary(tomo, limit, mesh=None):
    terms = {}
    add_slot_terms(terms, nonempty_pixels(tomo, "al_pxls"), "Al", -1)
    add_slot_terms(terms, nonempty_pixels(tomo, "be_pxls"), "Be", 1)
    add_slot_terms(terms, nonempty_pixels(tomo, "TC_pxls"), "TC", 1)
    add_slot_terms(terms, nonempty_pixels(tomo, "NVB_pxls"), "NVB", -1)
    add_slot_terms(terms, nonempty_pixels(tomo, "NVA_pxls"), "NVA", 1)

    rows = [(key, vals) for key, vals in terms.items() if vals["Vss"] != 0]
    rows.sort(key=lambda item: abs(item[1]["Vss"]), reverse=True)
    total = sum(vals["Vss"] for vals in terms.values())
    negative = sum(1 for vals in terms.values() if vals["Vss"] < 0)
    b_slots = boundary_slots(mesh, getattr(tomo, "mat4x4", None)) if mesh is not None else set()
    boundary_rows = sum(1 for key, _ in rows if key in b_slots)
    boundary_total = sum(vals["Vss"] for key, vals in rows if key in b_slots)
    print(
        f"slot Vss zsum total={total} nonzero={len(rows)} negative_slots={negative} "
        f"boundary_nonzero={boundary_rows} boundary_total={boundary_total}"
    )
    for (x, y), vals in rows[:limit]:
        marker = "B" if (x, y) in b_slots else "."
        print(
            f"  {marker} slot=({x:3d},{y:3d}) Vss={vals['Vss']:5d} "
            f"Al={vals['Al']:5d} Be={vals['Be']:5d} TC={vals['TC']:5d} "
            f"NVB={vals['NVB']:5d} NVA={vals['NVA']:5d}"
        )


def build_cases(out_dir):
    cube = trimesh.creation.box(extents=(20, 20, 20))
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=10)
    return [
        ("cube_closed", export_mesh(cube, out_dir, "cube_closed"), cube, False),
        ("cube_upper_open", *keep_positive_z_faces(cube, out_dir, "cube_upper_open"), True),
        ("cube_upper_capped", *keep_positive_z_faces(cube, out_dir, "cube_upper_capped", cap=True), False),
        (
            "cube_slant_open",
            *keep_halfspace_faces(cube, out_dir, "cube_slant_open", (1.0, 0.0, 0.7)),
            True,
        ),
        (
            "cube_slant_capped",
            *keep_halfspace_faces(cube, out_dir, "cube_slant_capped", (1.0, 0.0, 0.7), cap=True),
            False,
        ),
        ("sphere_closed", export_mesh(sphere, out_dir, "sphere_closed"), sphere, False),
        ("sphere_upper_open", *keep_positive_z_faces(sphere, out_dir, "sphere_upper_open"), True),
        ("sphere_upper_capped", *keep_positive_z_faces(sphere, out_dir, "sphere_upper_capped", cap=True), False),
        (
            "sphere_slant_open",
            *keep_halfspace_faces(sphere, out_dir, "sphere_slant_open", (1.0, 0.0, 0.7)),
            True,
        ),
        (
            "sphere_slant_capped",
            *keep_halfspace_faces(sphere, out_dir, "sphere_slant_capped", (1.0, 0.0, 0.7), cap=True),
            False,
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Run primitive closed/open-shell checks against Tomo_Shell2026.dll."
    )
    parser.add_argument("--out-dir", default="_tmp_validation_meshes")
    parser.add_argument("--step", type=int, default=90, help="Yaw/pitch sampling step in degrees.")
    parser.add_argument(
        "--theta",
        type=float,
        nargs="+",
        default=[60.0],
        help="Support critical angles in degrees.",
    )
    parser.add_argument(
        "--dump-pixels",
        action="store_true",
        help="Print type counts and z sums for the rendered optimal orientation.",
    )
    parser.add_argument(
        "--dump-slots",
        type=int,
        default=0,
        metavar="N",
        help="Print the N largest per-slot implicit Vss contributions.",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Only run cases whose names contain this text. Can be passed multiple times.",
    )
    parser.add_argument(
        "--compare-shell-off",
        action="store_true",
        help="For open/capped pairs, also compare the open mesh with bShellMesh disabled.",
    )
    parser.add_argument(
        "--shell-thickness",
        type=float,
        default=0.5,
        help="Shell-mode subsidiary surface thickness in mm. Use 0 to disable generated thickness.",
    )
    args = parser.parse_args()

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(exist_ok=True)
    results = {}

    for name, path, mesh, shell_mesh in build_cases(out_dir):
        if args.case and not any(pattern in name for pattern in args.case):
            continue
        print(
            f"\nCASE {name} watertight={mesh.is_watertight} "
            f"faces={len(mesh.faces)} shell={shell_mesh}"
        )
        for theta_deg in args.theta:
            collect_pixels = args.dump_pixels or args.dump_slots > 0
            grid, tomo = run_tomo(
                path,
                shell_mesh,
                theta_deg,
                args.step,
                args.shell_thickness,
                collect_pixels,
            )
            argmin = np.unravel_index(np.argmin(grid), grid.shape)
            print(
                f"theta={theta_deg:g} min={float(grid.min()):.9f} "
                f"max={float(grid.max()):.9f} argmin={argmin}"
            )
            if np.any(grid < -1e-7):
                print("WARNING negative Vss values detected")
            print(np.round(grid, 6))
            if args.dump_pixels:
                print_pixel_summary(tomo)
            if args.dump_slots > 0:
                print_slot_summary(tomo, args.dump_slots, mesh)
            results[(name, theta_deg)] = grid

    for base in ("cube_upper", "cube_slant", "sphere_upper", "sphere_slant"):
        for theta_deg in args.theta:
            open_grid = results.get((f"{base}_open", theta_deg))
            capped_grid = results.get((f"{base}_capped", theta_deg))
            if open_grid is None or capped_grid is None:
                continue
            diff = open_grid - capped_grid
            print(
                f"\nCOMPARE {base} theta={theta_deg:g} "
                f"open_min={float(open_grid.min()):.9f} "
                f"capped_min={float(capped_grid.min()):.9f} "
                f"diff_min={float(diff.min()):.9f} diff_max={float(diff.max()):.9f}"
            )
            if args.compare_shell_off:
                open_case = next(
                    (case for case in build_cases(out_dir) if case[0] == f"{base}_open"),
                    None,
                )
                if open_case is None:
                    continue
                shell_off = run_tomo_grid(open_case[1], False, theta_deg, args.step)
                print(
                    f"COMPARE {base} shell_off theta={theta_deg:g} "
                    f"open_min={float(shell_off.min()):.9f} "
                    f"capped_min={float(capped_grid.min()):.9f} "
                    f"mean_abs_on={float(np.mean(np.abs(open_grid - capped_grid))):.9f} "
                    f"mean_abs_off={float(np.mean(np.abs(shell_off - capped_grid))):.9f}"
                )


if __name__ == "__main__":
    main()
