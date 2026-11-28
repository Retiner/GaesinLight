"""Create static decorative elevator steel cables in Unreal Editor, in centimeters."""
import unreal as u, math, json, traceback
from pathlib import Path

# Reuse the tested OBJ writer from the matching machinery prop.
source=Path(u.Paths.project_dir())/'Tools/Create-ElevatorMachine.py'
exec(source.read_text(encoding='utf-8').split("r=Path(u.Paths.project_saved_dir())")[0],globals())

def unit(v):
    length=math.sqrt(sum(x*x for x in v));assert length>1e-8
    return tuple(x/length for x in v)
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sweep(mesh,points,radius,sides=8):
    verts=[]
    for k,c in enumerate(points):
        before=points[max(0,k-1)];after=points[min(len(points)-1,k+1)];t=unit(tuple(after[i]-before[i] for i in range(3)))
        ref=(1,0,0) if abs(t[0])<.85 else (0,1,0);n=unit(cross(ref,t));b=cross(t,n)
        for j in range(sides):
            ang=j*math.tau/sides;verts.append(tuple(c[i]+radius*(math.cos(ang)*n[i]+math.sin(ang)*b[i]) for i in range(3)))
    faces=[tuple(reversed(range(sides))),tuple(range((len(points)-1)*sides,len(points)*sides))]
    for k in range(len(points)-1):
        for j in range(sides):jj=(j+1)%sides;faces.append((k*sides+j,k*sides+jj,(k+1)*sides+jj,(k+1)*sides+j))
    mesh.add(verts,faces)
def cable(mesh,points,radius=1):
    sweep(mesh,points,radius*.76,10)
    # Three shallow helical strands catch the metal highlights without dense detail.
    distance=0;paths=[[] for _ in range(3)]
    for k,c in enumerate(points):
        if k:distance+=math.sqrt(sum((c[i]-points[k-1][i])**2 for i in range(3)))
        before=points[max(0,k-1)];after=points[min(len(points)-1,k+1)];t=unit(tuple(after[i]-before[i] for i in range(3)));n=(1,0,0);b=unit(cross(t,n))
        for s in range(3):
            angle=distance/24*math.tau+s*math.tau/3
            paths[s].append(tuple(c[i]+radius*.69*(math.cos(angle)*n[i]+math.sin(angle)*b[i]) for i in range(3)))
    for path in paths:sweep(mesh,path,radius*.31,5)
def line(x,y=0,length=500,steps=100):return [(x,y,-length*k/steps) for k in range(steps+1)]
def arch(x,length=600,radius=53,cz=94):
    # Aligned to SM_ElevatorMachine's traction sheave, with the same origin.
    # Legs move outside the base before descending, so they don't pierce the base plate.
    pts=[]
    for k in range(81):pts.append((x,-90,cz-length+(length-65)*k/80))
    for k in range(1,17):
        t=k/16;pts.append((x,-90+(90-radius)*(t*t*(3-2*t)),cz-65+65*t))
    for k in range(1,49):
        t=math.pi-math.pi*k/48;pts.append((x,radius*math.cos(t),cz+radius*math.sin(t)))
    for k in range(1,17):
        t=k/16;pts.append((x,radius+(90-radius)*(t*t*(3-2*t)),cz-65*t))
    for k in range(1,81):pts.append((x,90,cz-65-(length-65)*k/80))
    return pts

r=Path(u.Paths.project_saved_dir())/'CodexBackups/ElevatorCables-20261128';r.mkdir(parents=True,exist_ok=True);d={}
try:
    folder='/Game/Assets/StaticMeshes/ElevatorMachine';mat=u.load_asset('/Game/Assets/Materials/M_Metal_Gunmetal');assert mat
    single=Mesh();cable(single,line(0));bundle=Mesh();over=Mesh()
    for x in [-7.5,-2.5,2.5,7.5]:cable(bundle,line(x));cable(over,arch(99+x))
    outputs={'SM_ElevatorCable_5m':single,'SM_ElevatorCableBundle_5m':bundle,'SM_ElevatorCables_OverPulley':over}
    tasks=[]
    for name,mesh in outputs.items():
        assert not u.EditorAssetLibrary.does_asset_exist(folder+'/'+name),name
        src=r/(name+'.obj');mesh.obj(src)
        task=u.AssetImportTask();task.set_editor_property('filename',str(src));task.set_editor_property('destination_path',folder);task.set_editor_property('destination_name',name);task.set_editor_property('automated',True);task.set_editor_property('save',False);task.set_editor_property('factory',u.FbxFactory())
        opts=u.FbxImportUI();opts.set_editor_property('import_mesh',True);opts.set_editor_property('import_as_skeletal',False);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False);opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
        data=opts.get_editor_property('static_mesh_import_data');data.set_editor_property('combine_meshes',True);data.set_editor_property('auto_generate_collision',False);data.set_editor_property('convert_scene',False);data.set_editor_property('generate_lightmap_u_vs',True);data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task.set_editor_property('options',opts);tasks.append(task)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks);d['assets']=[]
    for name in outputs:
        mesh=u.load_asset(folder+'/'+name);assert isinstance(mesh,u.StaticMesh);mesh.set_material(0,mat)
        assert mesh.get_num_triangles(0)>0;assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
        d['assets'].append({'asset':mesh.get_path_name(),'triangles':mesh.get_num_triangles(0),'bounds':str(mesh.get_bounds()),'material':mesh.get_material(0).get_path_name()})
    d['success']=True
    u.EditorAssetLibrary.sync_browser_to_objects([folder+'/SM_ElevatorCables_OverPulley']);u.get_editor_subsystem(u.AssetEditorSubsystem).open_editor_for_assets([u.load_asset(folder+'/SM_ElevatorCables_OverPulley')])
except:d['error']=traceback.format_exc();u.log_error(d['error'])
(r/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
