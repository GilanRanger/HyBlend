import bpy
import mathutils

# Remove glTF_not_exported collection
removed_collection_name = "glTF_not_exported"
removed_collection = bpy.data.collections.get(removed_collection_name)
if removed_collection:
    bpy.data.collections.remove(removed_collection)
    
def get_vertex_group_bounds_in_bone_space(mesh_obj, armature_obj, bone_name, vgroup_index):
    """
    Calculate bounding box of a vertex group in the bone's local space.
    """
    mesh = mesh_obj.data
    bone = armature_obj.data.bones[bone_name]
    
    bone_matrix_world = armature_obj.matrix_world @ bone.matrix_local
    bone_matrix_world_inv = bone_matrix_world.inverted()
    
    verts_in_bone_space = []
    for vert in mesh.vertices:
        for g in vert.groups:
            if g.group == vgroup_index and g.weight > 0.0:
                # Transform to world space
                world_co = mesh_obj.matrix_world @ vert.co
                # Transform to bone local space
                bone_local_co = bone_matrix_world_inv @ world_co
                verts_in_bone_space.append(bone_local_co)
                break
    
    if not verts_in_bone_space:
        return None
    
    # Calculate bounds in bone space
    min_co = mathutils.Vector(verts_in_bone_space[0])
    max_co = mathutils.Vector(verts_in_bone_space[0])
    
    for v_co in verts_in_bone_space:
        min_co.x = min(min_co.x, v_co.x)
        min_co.y = min(min_co.y, v_co.y)
        min_co.z = min(min_co.z, v_co.z)
        max_co.x = max(max_co.x, v_co.x)
        max_co.y = max(max_co.y, v_co.y)
        max_co.z = max(max_co.z, v_co.z)
    
    center = (min_co + max_co) / 2.0
    dimensions = max_co - min_co
    
    return {
        'center': center,
        'dimensions': dimensions,
        'min': min_co,
        'max': max_co
    }

def create_bone_widget_from_vgroup(armature_obj, mesh_obj, bone_name, widget_collection):
    """
    Creates a cube widget for a bone based on vertex group bounding box.
    """
    vgroup = mesh_obj.vertex_groups.get(bone_name)
    if not vgroup:
        print(f"No vertex group for {bone_name}")
        return None
    
    bounds = get_vertex_group_bounds_in_bone_space(mesh_obj, armature_obj, bone_name, vgroup.index)
    if not bounds:
        print(f"No vertices in vertex group for {bone_name}")
        return None
    
    bone = armature_obj.data.bones[bone_name]
    
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    widget = bpy.context.active_object
    widget.name = f"WGT-{bone_name}"
    
    # Scale and position the cube in bone local space
    mesh = widget.data
    for vert in mesh.vertices:
        vert.co.x *= bounds['dimensions'].x / 2.0
        vert.co.y *= bounds['dimensions'].y / 2.0
        vert.co.z *= bounds['dimensions'].z / 2.0
        
        vert.co += bounds['center']
    
    # Move to widget collection
    for coll in widget.users_collection:
        coll.objects.unlink(widget)
    widget_collection.objects.link(widget)
    
    widget.hide_set(True)
    widget.hide_render = True
    
    # Assign to bone as custom shape
    pose_bone = armature_obj.pose.bones.get(bone_name)
    if pose_bone:
        pose_bone.custom_shape = widget
        pose_bone.use_custom_shape_bone_size = False
        pose_bone.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
        pose_bone.custom_shape_wire_width = 2.0
        
    # Make wireframe
    bone = armature_obj.data.bones.get(bone_name)
    if bone:
        bone.show_wire = True

    return widget

# Create or get widgets collection
widget_collection_name = "Widgets"
widget_collection = bpy.data.collections.get(widget_collection_name)
if not widget_collection:
    widget_collection = bpy.data.collections.new(widget_collection_name)
    bpy.context.scene.collection.children.link(widget_collection)

widget_collection.hide_viewport = True

# Find the armature and mesh objects
mesh_obj = None
armature_obj = None

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh_obj = obj
    elif obj.type == 'ARMATURE':
        armature_obj = obj

if mesh_obj and armature_obj:
    for bone in armature_obj.data.bones:
        create_bone_widget_from_vgroup(armature_obj, mesh_obj, bone.name, widget_collection)
else:
    if not armature_obj:
        print("No armature found")
    if not mesh_obj:
        print("No mesh found")