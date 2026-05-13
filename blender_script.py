"""在 Blender 内运行：导入单个 3D 资产并渲染为 PNG 缩略图。

该脚本由 Blender 通过 `--python` 启动，使用 Blender 自带的 Python 运行时，
因此**不依赖**仓库内其他 Python 模块；通过命令行参数（在 `--` 之后）传入配置。
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

import bpy
from mathutils import Vector


RENDERABLE_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit("缺少 '--' 分隔符；脚本参数应在 '--' 之后。")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--min-height", required=True, type=int)
    parser.add_argument("--max-height", required=True, type=int)
    parser.add_argument("--padding", required=True, type=float)
    parser.add_argument("--bg-color", required=True)
    parser.add_argument("--hdr", type=Path)
    parser.add_argument("--hdr-strength", required=True, type=float)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--samples", required=True, type=int)
    return parser.parse_args(argv[argv.index("--") + 1:])


def hex_to_rgba(value: str) -> tuple[float, float, float, float]:
    s = value.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"无效的颜色: {value}")
    return (int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255, 1.0)


def resolve_engine(requested: str) -> str:
    """选择当前 Blender 构建实际支持的渲染引擎（跨版本兼容）。"""
    try:
        prop = bpy.types.RenderSettings.bl_rna.properties["engine"]
        allowed = {it.identifier for it in prop.enum_items}
    except Exception:
        allowed = set()
    if requested in allowed:
        return requested
    for alt in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"):
        if alt in allowed and alt != requested:
            print(f"[info] engine fallback: {requested} -> {alt}", flush=True)
            return alt
    return requested


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)


def import_asset(asset_path: Path) -> None:
    suf = asset_path.suffix.lower()
    if suf == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(asset_path))
        return
    clear_scene()
    if suf == ".fbx":
        # FBX 内嵌图片路径常为相对路径，需切到资产目录以便 use_image_search 找到贴图。
        prev = os.getcwd()
        try:
            os.chdir(str(asset_path.parent))
            bpy.ops.import_scene.fbx(
                filepath=str(asset_path.resolve()),
                use_image_search=True,
                use_anim=False,
            )
        finally:
            os.chdir(prev)
    elif suf in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(asset_path))
    elif suf == ".obj":
        bpy.ops.wm.obj_import(filepath=str(asset_path))
    else:
        raise ValueError(f"不支持的资产类型: {asset_path.suffix}")


def remove_helpers() -> None:
    for obj in list(bpy.data.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)


def ensure_default_material(objects: list[bpy.types.Object]) -> None:
    mat = bpy.data.materials.get("AutoNeutralMaterial")
    if mat is None:
        mat = bpy.data.materials.new(name="AutoNeutralMaterial")
        mat.use_nodes = True
        principled = mat.node_tree.nodes.get("Principled BSDF")
        if principled is not None:
            if (bc := principled.inputs.get("Base Color")) is not None:
                bc.default_value = (0.72, 0.72, 0.72, 1.0)
            if (rough := principled.inputs.get("Roughness")) is not None:
                rough.default_value = 0.45
            for key in ("Specular IOR Level", "Specular IOR", "Specular"):
                spec = principled.inputs.get(key)
                if spec is None:
                    continue
                try:
                    spec.default_value = 0.35
                except (TypeError, AttributeError, ValueError):
                    pass
                break

    for obj in objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        if hasattr(mesh, "use_auto_smooth"):
            mesh.use_auto_smooth = True
        if not obj.material_slots:
            mesh.materials.append(mat)


def get_renderable_objects() -> list[bpy.types.Object]:
    return [
        obj
        for obj in bpy.context.scene.objects
        if obj.type in RENDERABLE_TYPES and not obj.hide_render
        and not (obj.type == "MESH" and not hasattr(obj.data, "vertices"))
    ]


def unique_roots(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    roots: list[bpy.types.Object] = []
    seen: set[str] = set()
    for obj in objects:
        root = obj
        while root.parent is not None:
            root = root.parent
        if root.name_full not in seen:
            seen.add(root.name_full)
            roots.append(root)
    return roots


def evaluated_bbox_corners(objects: list[bpy.types.Object]) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners: list[Vector] = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        try:
            bound_box = evaluated.bound_box
        except AttributeError:
            continue
        matrix = evaluated.matrix_world
        for c in bound_box:
            corners.append(matrix @ Vector(c))
    return corners


def combined_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = evaluated_bbox_corners(objects)
    if not corners:
        raise ValueError("导入后未找到可渲染的几何体。")
    min_c = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    max_c = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return min_c, max_c


def normalize_asset(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    """将资产水平居中、底部贴 Z=0。"""
    mn, mx = combined_bounds(objects)
    offset = Vector((-(mn.x + mx.x) * 0.5, -(mn.y + mx.y) * 0.5, -mn.z))
    for root in unique_roots(objects):
        root.location += offset
    bpy.context.view_layer.update()
    return combined_bounds(objects)


def create_camera(bounds: tuple[Vector, Vector]) -> bpy.types.Object:
    mn, mx = bounds
    diagonal = max((mx - mn).length, 1.0)
    target = Vector(((mn.x + mx.x) * 0.5, (mn.y + mx.y) * 0.5, (mn.z + mx.z) * 0.5))

    cam_data = bpy.data.cameras.new("RenderCamera")
    cam = bpy.data.objects.new("RenderCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam_data.type = "PERSP"
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.angle = math.radians(36.0)
    cam_data.clip_start = 0.01
    cam_data.clip_end = diagonal * 20.0

    view_dir = Vector((1.0, -1.0, 0.8)).normalized()
    cam.location = target + view_dir * diagonal * 3.0
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    return cam


def perspective_local_points(
    camera: bpy.types.Object,
    target: Vector,
    objects: list[bpy.types.Object],
    distance: float,
) -> list[Vector]:
    rotation = camera.matrix_world.to_quaternion().inverted()
    cam_location = target + (camera.location - target).normalized() * distance
    return [rotation @ (corner - cam_location) for corner in evaluated_bbox_corners(objects)]


def screen_bounds(local_points: list[Vector]) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for p in local_points:
        depth = max(-p.z, 1e-5)
        xs.append(p.x / depth)
        ys.append(p.y / depth)
    return min(xs), max(xs), min(ys), max(ys)


def center_camera(
    camera: bpy.types.Object,
    target: Vector,
    objects: list[bpy.types.Object],
    distance: float,
    iterations: int = 6,
) -> Vector:
    """通过迭代将投影中心对齐到画面中心。"""
    for _ in range(iterations):
        points = perspective_local_points(camera, target, objects, distance)
        xs, ys, depths = [], [], []
        for p in points:
            d = max(-p.z, 1e-5)
            xs.append(p.x / d)
            ys.append(p.y / d)
            depths.append(d)
        cx = (min(xs) + max(xs)) * 0.5
        cy = (min(ys) + max(ys)) * 0.5
        if abs(cx) < 1e-4 and abs(cy) < 1e-4:
            break
        depths.sort()
        ref = depths[len(depths) // 2]
        local_shift = Vector((cx * ref, cy * ref, 0.0))
        world_shift = camera.matrix_world.to_quaternion() @ local_shift
        camera.location += world_shift
        target += world_shift
        bpy.context.view_layer.update()
    return target


def solve_distance(
    camera: bpy.types.Object,
    target: Vector,
    objects: list[bpy.types.Object],
    width: int,
    height: int,
    padding: float,
) -> float:
    rotation = camera.matrix_world.to_quaternion().inverted()
    scale = 1.0 + padding * 2.0
    tan_x = math.tan(camera.data.angle * 0.5) / scale
    tan_y = tan_x * (height / float(width))
    local = [rotation @ (corner - target) for corner in evaluated_bbox_corners(objects)]
    required = 0.0
    for p in local:
        required = max(required, p.z + (abs(p.x) / max(tan_x, 1e-5)))
        required = max(required, p.z + (abs(p.y) / max(tan_y, 1e-5)))
    return max(required, 0.1)


def fit_camera(
    camera: bpy.types.Object,
    bounds: tuple[Vector, Vector],
    objects: list[bpy.types.Object],
    width: int,
    min_h: int,
    max_h: int,
    padding: float,
) -> int:
    mn, mx = bounds
    target = Vector(((mn.x + mx.x) * 0.5, (mn.y + mx.y) * 0.5, (mn.z + mx.z) * 0.5))
    span_x = max(mx.x - mn.x, 1e-4)
    height = max(min_h, min(max_h, int(round(width * ((mx.z - mn.z) / span_x)))))
    distance = 1.0

    for _ in range(4):
        distance = solve_distance(camera, target, objects, width, height, padding)
        view_dir = (camera.location - target).normalized()
        camera.location = target + view_dir * distance
        bpy.context.view_layer.update()
        target = center_camera(camera, target, objects, distance)
        bounds_local = perspective_local_points(camera, target, objects, distance)
        min_x, max_x, min_y, max_y = screen_bounds(bounds_local)
        span_screen_x = max(max_x - min_x, 1e-5)
        span_screen_y = max(max_y - min_y, 1e-5)
        height = max(min_h, min(max_h, int(round(width * (span_screen_y / span_screen_x)))))

    camera.location = target + (camera.location - target).normalized() * distance
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return height


def configure_scene(
    output_path: Path,
    bg_color: tuple[float, float, float, float],
    width: int,
    height: int,
    hdr_path: Optional[Path],
    hdr_strength: float,
    engine: str,
    samples: int,
    camera: bpy.types.Object,
) -> None:
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.filepath = str(output_path)
    scene.render.engine = engine
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.use_file_extension = False
    try:
        scene.view_settings.view_transform = "Standard"
        scene.display_settings.display_device = "sRGB"
    except Exception:
        pass

    world = scene.world or bpy.data.worlds.new("RenderWorld")
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    out = nodes.new(type="ShaderNodeOutputWorld")
    out.location = (500, 0)
    bg = nodes.new(type="ShaderNodeBackground")
    bg.location = (220, 80)
    bg.inputs["Strength"].default_value = hdr_strength if hdr_path else 0.75
    if hdr_path:
        env = nodes.new(type="ShaderNodeTexEnvironment")
        env.location = (-420, 120)
        image = bpy.data.images.load(str(hdr_path), check_existing=True)
        _force_linear_colorspace(image)
        env.image = image
        links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        bg.inputs["Color"].default_value = bg_color
    links.new(bg.outputs["Background"], out.inputs["Surface"])

    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        try:
            scene.cycles.device = "CPU"
        except (TypeError, AttributeError):
            pass
    else:
        eevee = getattr(scene, "eevee", None)
        if eevee is not None:
            for attr in ("taa_render_samples", "taa_samples", "temporal_samples"):
                if hasattr(eevee, attr):
                    try:
                        setattr(eevee, attr, samples)
                        break
                    except (TypeError, AttributeError):
                        continue
            if hasattr(eevee, "use_raytracing"):
                try:
                    eevee.use_raytracing = True
                except (TypeError, AttributeError):
                    pass


def _force_linear_colorspace(image: bpy.types.Image) -> None:
    """把 HDR/EXR 环境贴图固定到线性色彩空间，防止被当 sRGB 二次反伽马。"""
    try:
        prop = type(image.colorspace_settings).bl_rna.properties["name"]
        allowed = [it.identifier for it in prop.enum_items]
    except Exception:
        allowed = []
    for cand in ("Linear Rec.709", "Linear", "Non-Color", "Linear BT.709", "Raw"):
        if allowed and cand not in allowed:
            continue
        try:
            image.colorspace_settings.name = cand
            return
        except (TypeError, AttributeError, ValueError):
            continue


def main() -> int:
    try:
        args = parse_args()
        input_path = args.input.expanduser().resolve()
        output_path = args.output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        import_asset(input_path)
        remove_helpers()
        objects = get_renderable_objects()
        if not objects:
            raise SystemExit("资产中没有可渲染对象。")

        ensure_default_material(objects)
        bounds = normalize_asset(objects)
        camera = create_camera(bounds)
        bpy.context.view_layer.update()

        height = fit_camera(
            camera=camera, bounds=bounds, objects=objects,
            width=args.width, min_h=args.min_height, max_h=args.max_height,
            padding=args.padding,
        )
        engine = resolve_engine(args.engine)
        configure_scene(
            output_path=output_path,
            bg_color=hex_to_rgba(args.bg_color),
            width=args.width, height=height,
            hdr_path=args.hdr.expanduser().resolve() if args.hdr else None,
            hdr_strength=args.hdr_strength,
            engine=engine, samples=args.samples,
            camera=camera,
        )
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {input_path} -> {output_path} ({args.width}x{height})")
        return 0
    except SystemExit as e:
        if str(e):
            print(str(e), file=sys.stderr)
        raise
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
