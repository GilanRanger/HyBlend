import os
import subprocess
import time
import pyautogui
import pyperclip

# Configuration
ENTITY_ASSET_FOLDER = r"C:\Users\brend\Desktop\Hytale\templates\Hytale Model Examples"
BLOCKBENCH_PATH = r"C:\Users\brend\AppData\Local\Programs\Blockbench\Blockbench.exe"
BLENDER_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
GLTF_EXPORT_FOLDER = r"C:\Users\brend\Desktop\Hytale\external_tools\HyBlend\assets\gltf"
BLEND_OUTPUT_FOLDER = r"C:\Users\brend\Desktop\Hytale\external_tools\HyBlend\assets\rawBlend"

GLFT_EXPORT_SETTINGS = {
    "binary_encoding": False,
    "export_armature": True,
    "embed_textures": True,
    "export_animations": True,
}

pyautogui.PAUSE = 0.1

def find_blockymodel_files(folder):
    blockymodel_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith('.blockymodel'):
                blockymodel_files.append(os.path.join(root, file))
    return blockymodel_files


def get_entity_name_from_path(blockymodel_path, used_names):
    """Extract entity name from path structure: Entity_Folder/Models/model.blockymodel"""
    path_parts = os.path.normpath(blockymodel_path).split(os.sep)

    # Find "Models" folder and get parent
    for i, part in enumerate(path_parts):
        if part.lower() == 'models' and i > 0:
            return path_parts[i - 1]

    # Fallback: use filename with integer suffix
    base_name = os.path.splitext(os.path.basename(blockymodel_path))[0]
    counter = 0
    entity_name = f"{base_name}_{counter}"

    while entity_name in used_names:
        counter += 1
        entity_name = f"{base_name}_{counter}"

    return entity_name


def export_gltf_blockbench(blockymodel_path, output_gltf_path):
    # File > Open
    pyautogui.hotkey('ctrl', 'o')
    time.sleep(1)

    # Enter file path
    pyperclip.copy(blockymodel_path)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(2)

    # Check for "Import Textures" dialog
    # If dialog appears, "Select Folder" button should be focusable
    model_folder = os.path.dirname(blockymodel_path)

    # Try to handle texture dialog (won't affect anything if dialog isn't present)
    pyautogui.press('tab')
    pyautogui.press('tab')
    time.sleep(0.3)
    pyautogui.press('space')
    time.sleep(0.5)

    # If dialog was present, file picker is now open
    # Enter the Model folder path
    pyperclip.copy(model_folder)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('tab')
    pyautogui.press('enter')
    time.sleep(1)

    # Open export glTF Model menu (My hotkey is set as alt+F)
    pyautogui.hotkey('alt', 'f')
    time.sleep(0.5)

    # Enable "Export Groups as Armature"
    pyautogui.press('tab')
    pyautogui.press('tab')
    pyautogui.press('space')
    time.sleep(0.3)

    # Start export
    pyautogui.press('enter')
    time.sleep(1)

    # Enter output path
    pyperclip.copy(output_gltf_path)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(1)

    # Another Enter to overwrite existing files if necessary
    pyautogui.press('tab')
    pyautogui.press('enter')
    time.sleep(1)

    # Close project
    pyautogui.hotkey('ctrl', 'w')
    time.sleep(0.5)

    return os.path.exists(output_gltf_path)


def process_gltf_in_blender(gltf_path, blend_output_path):
    rig_format_script = r"C:\Users\brend\Desktop\Hytale\external_tools\HyBlend\extraction\blender_rig_format.py"

    blender_script = f"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{gltf_path}")

exec(open(r"{rig_format_script}").read())

bpy.ops.wm.save_as_mainfile(filepath=r"{blend_output_path}")
print(r"Saved: {blend_output_path}")
"""

    temp_script = "temp_blender_import.py"
    with open(temp_script, 'w') as f:
        f.write(blender_script)

    cmd = [BLENDER_PATH, "--background", "--python", temp_script]
    subprocess.run(cmd, check=True)
    os.remove(temp_script)


def process():
    os.makedirs(GLTF_EXPORT_FOLDER, exist_ok=True)
    os.makedirs(BLEND_OUTPUT_FOLDER, exist_ok=True)

    blockymodel_files = find_blockymodel_files(ENTITY_ASSET_FOLDER)
    print(f"Found {len(blockymodel_files)} .blockymodel files")

    used_names = set()

    subprocess.Popen([BLOCKBENCH_PATH])
    time.sleep(8)

    for blockymodel_path in blockymodel_files:
        entity_name = get_entity_name_from_path(blockymodel_path, used_names)
        used_names.add(entity_name)

        gltf_path = os.path.join(GLTF_EXPORT_FOLDER, f"{entity_name}.gltf")
        blend_path = os.path.join(BLEND_OUTPUT_FOLDER, f"{entity_name}.blend")

        print(f"\nExporting: {entity_name}")
        time.sleep(2)

        if export_gltf_blockbench(blockymodel_path, gltf_path):
            print(f"Successfully exported {entity_name}.gltf")
            process_gltf_in_blender(gltf_path, blend_path)
        else:
            print(f"Failed to export {entity_name}")


if __name__ == "__main__":
    process()