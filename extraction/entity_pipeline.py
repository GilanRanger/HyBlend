import os
import subprocess
import time
import yaml
import requests
import atexit
from pathlib import Path

config_path = Path(__file__).parent / "pipeline_configuration.yml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

ENTITY_ASSET_FOLDER = config['paths']['entity_asset_folder']
BLENDER_PATH = config['paths']['blender']
GLTF_EXPORT_FOLDER = config['paths']['gltf_export_folder']
BLEND_OUTPUT_FOLDER = config['paths']['blend_output_folder']
RIG_FORMAT_SCRIPT = config['paths']['rig_format_script']
BLOCKBENCH_SERVER = 'http://localhost:3002'


def find_blockymodel_files(folder):
    blockymodel_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.blockymodel'):
                blockymodel_files.append(os.path.join(root, file))
    return blockymodel_files


def get_entity_name_from_path(blockymodel_path, base_folder):
    rel_path = os.path.relpath(blockymodel_path, base_folder)
    name_without_ext = os.path.splitext(rel_path)[0]
    safe_name = name_without_ext.replace(os.sep, '_').replace('/', '_').replace('\\', '_')
    return safe_name


def export_gltf_blockbench(blockymodel_path, output_gltf_path):
    try:
        response = requests.post(
            f'{BLOCKBENCH_SERVER}/export',
            json={'input': blockymodel_path, 'output': output_gltf_path},
            timeout=30
        )
        return response.status_code == 200 and os.path.exists(output_gltf_path)
    except Exception as e:
        print(f"Export request failed: {e}")
        return False


def process_gltf_in_blender(gltf_path, blend_output_path):
    blender_script = f"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{gltf_path}")
exec(open(r"{RIG_FORMAT_SCRIPT}").read())
bpy.ops.wm.save_as_mainfile(filepath=r"{blend_output_path}")
"""
    temp_script = "temp_blender_import.py"
    with open(temp_script, 'w') as f:
        f.write(blender_script)

    subprocess.run([BLENDER_PATH, "--background", "--python", temp_script], check=True)
    os.remove(temp_script)


def start_blockbench_server():
    server_script = Path(__file__).parent / "blockbench_server.js"
    process = subprocess.Popen(
        ['node', str(server_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    for _ in range(60):
        try:
            if requests.get(f'{BLOCKBENCH_SERVER}/health', timeout=1).status_code == 200:
                return process
        except:
            time.sleep(1)

    raise Exception("Blockbench server failed to start")


def shutdown_blockbench_server():
    try:
        requests.get(f'{BLOCKBENCH_SERVER}/shutdown', timeout=2)
        time.sleep(1)
    except:
        pass

def process():
    os.makedirs(GLTF_EXPORT_FOLDER, exist_ok=True)
    os.makedirs(BLEND_OUTPUT_FOLDER, exist_ok=True)

    blockymodel_files = find_blockymodel_files(ENTITY_ASSET_FOLDER)
    print(f"Found {len(blockymodel_files)} .blockymodel files")

    server_process = start_blockbench_server()
    atexit.register(shutdown_blockbench_server)

    for blockymodel_path in blockymodel_files:
        entity_name = get_entity_name_from_path(blockymodel_path, ENTITY_ASSET_FOLDER)

        gltf_path = os.path.join(GLTF_EXPORT_FOLDER, f"{entity_name}.gltf")
        blend_path = os.path.join(BLEND_OUTPUT_FOLDER, f"{entity_name}.blend")

        print(f"\nExporting: {entity_name}")

        if export_gltf_blockbench(blockymodel_path, gltf_path):
            print(f"Successfully exported {entity_name}.gltf")
            process_gltf_in_blender(gltf_path, blend_path)
        else:
            print(f"Failed to export {entity_name}")

    shutdown_blockbench_server()


if __name__ == "__main__":
    process()