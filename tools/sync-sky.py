"""Refresh only the packed sky in the existing Blender project.

Run Blender in background with this script after exporting staticPanorama().
Mesh geometry, cameras, materials and the portable game payload are preserved.
"""
from pathlib import Path
import bpy
import json

root=Path(__file__).resolve().parents[1]
project=root/'scene/starry-village.blend'
panorama=root/'scene/textures/night-sky.png'
assert project.exists() and panorama.exists()
bpy.ops.wm.open_mainfile(filepath=str(project))
scene=bpy.context.scene
nodes=[node for node in scene.world.node_tree.nodes if node.type=='TEX_ENVIRONMENT']
assert nodes, 'The existing project has no environment texture node'
before={obj.name:(len(obj.data.vertices),len(obj.data.polygons)) for obj in scene.objects if obj.type=='MESH'}
sky=bpy.data.images.load(str(panorama),check_existing=False)
sky.name='Starry Night / connected cloud ribbons'
sky.pack()
sky.filepath='//textures/night-sky.png'
for node in nodes:node.image=sky
scene['Sky revision']='impasto-sky-v6-theme'
after={obj.name:(len(obj.data.vertices),len(obj.data.polygons)) for obj in scene.objects if obj.type=='MESH'}
assert before==after
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(project))
print(json.dumps(dict(status='complete',sky=scene['Sky revision'],meshes=len(after),geometryUnchanged=before==after,packed=bool(sky.packed_file))),flush=True)
