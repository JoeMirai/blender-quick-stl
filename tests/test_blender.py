import sys, tempfile, struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
import quick_stl
quick_stl.register()

def bounds(path):
    data=Path(path).read_bytes()
    count=struct.unpack_from('<I',data,80)[0]
    assert len(data)==84+50*count
    vertices=[]
    for i in range(count):
        values=struct.unpack_from('<12fH',data,84+i*50)
        vertices.extend([values[3:6],values[6:9],values[9:12]])
    return [(min(v[k] for v in vertices),max(v[k] for v in vertices)) for k in range(3)]

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=0.01)
a=bpy.context.object;a.name='My Part'
s=bpy.context.scene.quick_stl_settings
assert s.filename=='My Part',s.filename
with tempfile.TemporaryDirectory() as tmp:
    s.folder=tmp
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    assert bpy.ops.quick_stl.export(kind='COMBINED')=={'FINISHED'}
    assert abs(bounds(Path(tmp)/'My Part.stl')[0][1]-5)<1e-5
    assert bpy.context.active_object==a and a.select_get()
    s.filename='Custom Name.stl'
    assert bpy.ops.quick_stl.export(kind='COMBINED')=={'FINISHED'}
    assert (Path(tmp)/'Custom Name.stl').exists()
    assert bpy.ops.quick_stl.export(kind='COMBINED')=={'FINISHED'}
    assert (Path(tmp)/'Custom Name_001.stl').exists()
    assert bpy.ops.quick_stl.reset_name()=={'FINISHED'}
    bpy.ops.mesh.primitive_cube_add(size=0.01,location=(0.02,0,0))
    b=bpy.context.object;b.name='Other Part';a.select_set(True)
    selected=set(bpy.context.selected_objects)
    s.prefix='Print_'
    assert bpy.ops.quick_stl.export(kind='SEPARATE')=={'FINISHED'}
    assert (Path(tmp)/'Print_My Part.stl').exists() and (Path(tmp)/'Print_Other Part.stl').exists()
    assert set(bpy.context.selected_objects)==selected and bpy.context.active_object==b
    s.filename='Both'
    assert bpy.ops.quick_stl.export(kind='COMBINED')=={'FINISHED'}
    assert abs(bounds(Path(tmp)/'Both.stl')[0][1]-25)<1e-4
    bpy.context.scene.unit_settings.scale_length=0.001
    s.filename='Scale Check'
    assert bpy.ops.quick_stl.export(kind='ACTIVE')=={'FINISHED'}
    assert abs(bounds(Path(tmp)/'Scale Check.stl')[0][1]-0.025)<1e-6
    s.sizing='RAW';s.filename='Raw Check'
    assert bpy.ops.quick_stl.export(kind='ACTIVE')=={'FINISHED'}
    assert abs(bounds(Path(tmp)/'Raw Check.stl')[0][1]-0.025)<1e-6
    bpy.context.scene.unit_settings.system='NONE';s.sizing='MM'
    assert quick_stl.export_scale(bpy.context.scene,s.sizing)==1
    s.ascii_format=True;s.filename='ASCII'
    assert bpy.ops.quick_stl.export(kind='ACTIVE')=={'FINISHED'}
    assert (Path(tmp)/'ASCII.stl').read_text().startswith('solid')
    s.ascii_format=False;s.filename='Edit Mode'
    bpy.ops.object.mode_set(mode='EDIT')
    assert bpy.ops.quick_stl.export(kind='COMBINED')=={'FINISHED'}
    assert bpy.context.mode=='EDIT_MESH'
    assert set(bpy.context.selected_objects)==selected
    bpy.ops.object.mode_set(mode='OBJECT')
    print('PASS filenames, multi-object exports, selection restore, mm sizing, collision handling, ASCII, Edit Mode')
quick_stl.unregister();quick_stl.register();quick_stl.unregister()
print('ALL TESTS PASSED')
