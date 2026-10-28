"""Build an isolated catalogue before applying the house / wall kit to the map.

Run in Blender. Uses the actual authoring helpers and mesh exporter; the normal
scene files are not overwritten. Outputs a small .blend and offline preview data.
"""
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'tools/build-village.py').read_text(encoding='utf-8')
# Execute only the material/geometry setup, plus the two shared declarations.
exec(compile(source[:source.index("print('Building the painted valley...'")],str(ROOT/'tools/build-village.py'),'exec'),globals())
tree=ast.parse(source)
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('arch','collider'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<sample helpers>','exec'),globals())
for filename in ['village-organic.py','village-houses.py']:
    exec(compile((ROOT/'tools'/filename).read_text(encoding='utf-8'),filename,'exec'),globals())
height=lambda x,z:0
colliders=[];house_records=[];light_pools=[];occupied=[]
samples=[]
for style in range(12):
    x=(style%4)*25;z=-(style//4)*26
    rec=house(x,z,6.5,7.1,5.8,0,style,'samples')
    samples.append(dict(style=style,label=HOUSE_LABELS[style%6]+f' · {style//6+1}',record=rec))
build_drywall([(110,2),(110,-8)],1,True)
build_drywall([(110,2),(110,-8)],-1,True)
for x,z in [(style%4*25,-(style//4)*26) for style in range(12)]+[(110,-3)]:
    batch('earth',x,z,'terrain').face([(x-12,0,z-12),(x-12,0,z+12),(x+12,0,z+12),(x+12,0,z-12)],color('#9b9b84'))
start=source.index("print('Writing Blender meshes and portable geometry...'")
end=source.index('# Useful named cameras',start)
exec(compile(source[start:end],'<shared mesh exporter>','exec'),globals())
sample_out=ROOT/'场景对照分析'
metadata=dict(version=1,title='住宅与入口石墙样板',materials=material_specs,meshes=geometry_records,
              colliders=colliders,houses=house_records,streets=[[(0,0),(0,-10)]],
              views=[dict(id='lane',position=[12,12,19],target=[0,3,0])],lightPools=light_pools,
              terrain=dict(n=3,span=672,heights=pack_array([0]*9,'f',1)),
              stats=dict(meshes=len(geometry_records),houses=12,distantHouses=0,colliders=len(colliders)))
texture_names={spec[key] for spec in material_specs.values() for key in ('texture','normal') if key in spec}
payload=dict(metadata=metadata,binary=base64.b64encode(gzip.compress(b''.join(blobs),6)).decode(),
             textures={name:base64.b64encode((OUT/'textures'/f'{name}.png').read_bytes()).decode() for name in texture_names})
(sample_out/'住宅与石墙样板.js').write_text('window.STARRY_VILLAGE='+json.dumps(payload,separators=(',',':'))+';',encoding='utf-8')
(sample_out/'住宅样板索引.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
world=bpy.data.worlds.new('Sample night');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(*color('#8495b0'),1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45;bpy.context.scene.world=world
sun_data=bpy.data.lights.new('Sample moonlight','SUN');sun_data.energy=1.8;sun_data.angle=.18
sun=bpy.data.objects.new('Sample moonlight',sun_data);bpy.context.scene.collection.objects.link(sun);sun.rotation_euler=(.65,-.35,-.5)
camera=bpy.data.cameras.new('住宅样板总览');camera.type='ORTHO';camera.ortho_scale=110
ob=bpy.data.objects.new('住宅样板总览',camera);bpy.context.scene.collection.objects.link(ob)
ob.location=(84,-72,78);ob.rotation_euler=(Vector((40,22,0))-ob.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=ob
bpy.ops.wm.save_as_mainfile(filepath=str(sample_out/'住宅与石墙样板.blend'))
print('Samples ready:',len(samples),flush=True)
