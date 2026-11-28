"""Generate a simple elevator traction-machine prop in Unreal Editor (centimeters)."""
import unreal as u
import math, json, traceback
from pathlib import Path

class Mesh:
    def __init__(self): self.v=[]; self.f=[]
    def add(self, verts, faces):
        start=len(self.v); self.v.extend(verts)
        for face in faces:
            for k in range(1,len(face)-1): self.f.append((start+face[0],start+face[k],start+face[k+1]))
    def merge(self, other): self.add(other.v,other.f)
    def box(self, c, size, bevel=1.5, rx=0):
        hx,hy,hz=[s/2 for s in size]; b=min(bevel,hx*.3,hy*.3,hz*.3)
        def outline(x,y,ch): return [(-x+ch,-y),(x-ch,-y),(x,-y+ch),(x,y-ch),(x-ch,y),(-x+ch,y),(-x,y-ch),(-x,-y+ch)]
        verts=[]
        for z,inset in [(-hz,b),(-hz+b,0),(hz-b,0),(hz,b)]:
            for x,y in outline(hx-inset,hy-inset,max(.05,b-inset*.5)):
                yy=y*math.cos(rx)-z*math.sin(rx);zz=y*math.sin(rx)+z*math.cos(rx)
                verts.append((c[0]+x,c[1]+yy,c[2]+zz))
        faces=[tuple(reversed(range(8))),tuple(range(24,32))]
        for ring in range(3):
            for i in range(8):j=(i+1)%8;faces.append((ring*8+i,ring*8+j,(ring+1)*8+j,(ring+1)*8+i))
        self.add(verts,faces)
    def tube(self,c,radius,length,inner=0,sides=48):
        # Axis X; annular faces preserve the open spaces around the spokes.
        verts=[]
        radii=[radius,inner] if inner>0 else [radius]
        for x in [-length/2,length/2]:
            for rad in radii:
                for i in range(sides):
                    t=2*math.pi*i/sides;verts.append((c[0]+x,c[1]+rad*math.cos(t),c[2]+rad*math.sin(t)))
        stride=sides*len(radii);faces=[]
        for i in range(sides):
            j=(i+1)%sides;faces.append((i,j,stride+j,stride+i))
            if inner>0:
                faces.extend([(sides+j,sides+i,stride+sides+i,stride+sides+j),(stride+i,stride+j,stride+sides+j,stride+sides+i),(j,i,sides+i,sides+j)])
        if not inner:faces.extend([tuple(reversed(range(sides))),tuple(range(stride,stride+sides))])
        self.add(verts,faces)
    def obj(self,path):
        lines=['# GaesinLight elevator machine; coordinates in cm','o ElevatorMachine','s off']
        lines += ['v %.6f %.6f %.6f'%v for v in self.v]
        # Planar face UVs and explicit normals keep flat panels and bevels crisp.
        for f in self.f:
            a,b,c=[self.v[i] for i in f];ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
            n=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]);ln=math.sqrt(sum(t*t for t in n));assert ln>1e-8
            lines.append('vn %.7f %.7f %.7f'%tuple(t/ln for t in n))
            axis=max(range(3),key=lambda i:abs(n[i]));uvaxes=[i for i in range(3) if i!=axis]
            for v in [a,b,c]:lines.append('vt %.6f %.6f'%(v[uvaxes[0]]/100,v[uvaxes[1]]/100))
        for k,f in enumerate(self.f):lines.append('f '+' '.join('%d/%d/%d'%(v+1,k*3+i+1,k+1) for i,v in enumerate(f)))
        path.write_text('\n'.join(lines),encoding='utf-8')

def pulley(m,c,r,width,spokes=6):
    x,y,z=c
    m.tube(c,r*.86,width*.75,r*.67)
    for dx in [-width*.5,width*.5]:m.tube((x+dx,y,z),r,width*.14,r*.69)
    m.tube(c,r*.23,width*1.65,sides=32)
    m.tube((x+width*.92,y,z),r*.12,width*.22,sides=12)
    for i in range(spokes):
        t=i*math.tau/spokes;rr=r*.46
        m.box((x,y+rr*math.cos(t),z+rr*math.sin(t)),(width*.50,r*.55,r*.105),.7,t)
    for i in range(6):
        t=i*math.tau/6;m.tube((x+width*.86,y+r*.16*math.cos(t),z+r*.16*math.sin(t)),r*.035,width*.12,sides=6)

def generate():
    parts={name:Mesh() for name in ['Base','Motor','Gearbox','Pulley','AuxPulley']}
    b=parts['Base'];b.box((0,0,5),(270,150,10),2)
    for y in [-57,57]:
        b.box((0,y,17),(254,13,14),1)
        for x in [-116,116]:b.box((x,y,26),(25,27,6),.8);b.tube((x,y,31),4,7,sides=6)
    for y in [-26,26]: b.box((-62,y,29),(104,17,12),1.5)
    b.box((24,0,28),(83,93,12),2)
    mo=parts['Motor'];mo.tube((-66,0,67),30,83,sides=48)
    mo.tube((-112,0,67),33,9,sides=48);mo.tube((-20,0,67),33,9,sides=48)
    mo.tube((-120,0,67),25,7,sides=32)
    for i in range(14):
        t=i*math.tau/14;mo.box((-66,32*math.cos(t),67+32*math.sin(t)),(74,4,4),.45,t)
    mo.box((-64,0,108),(31,30,17),2)
    for x in [-93,-36]:
        for y in [-24,24]:mo.box((x,y,40),(18,20,16),1)
    g=parts['Gearbox'];g.box((25,0,69),(71,79,77),5)
    g.box((27,-42,70),(53,6,52),3);g.box((23,0,111),(45,54,9),2)
    g.tube((68,0,94),11,28,sides=32)
    for y in [-30,30]:
        for z in [45,91]:g.tube((64,y,z),3.5,4,sides=6)
    # Brake/caliper silhouette beside the large traction sheave.
    g.box((95,0,146),(49,39,13),2);g.box((71,0,127),(12,40,35),2)
    p=parts['Pulley'];pulley(p,(99,0,94),58,24,6)
    a=parts['AuxPulley'];pulley(a,(83,-67,58),25,15,5)
    a.box((70,-67,41),(16,20,32),2)
    return parts

r=Path(u.Paths.project_saved_dir())/'CodexBackups/ElevatorMachine-20261128';r.mkdir(parents=True,exist_ok=True);d={}
try:
    folder='/Game/Assets/StaticMeshes/ElevatorMachine';material=u.load_asset('/Game/Assets/Materials/M_Metal_Gunmetal');assert material
    parts=generate();whole=Mesh()
    for m in parts.values():whole.merge(m)
    outputs={'SM_ElevatorMachine':whole}
    # Individual pieces get their own bottom-center pivot for reuse.
    for name,m in parts.items():
        lo=[min(v[i] for v in m.v) for i in range(3)];hi=[max(v[i] for v in m.v) for i in range(3)]
        pivot=((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]);local=Mesh();local.add([tuple(v[i]-pivot[i] for i in range(3)) for v in m.v],m.f);outputs['SM_Elevator'+name]=local
    tasks=[]
    for name,m in outputs.items():
        assert not u.EditorAssetLibrary.does_asset_exist(folder+'/'+name),'Asset exists: '+name
        source=r/(name+'.obj');m.obj(source)
        task=u.AssetImportTask();task.set_editor_property('filename',str(source));task.set_editor_property('destination_path',folder);task.set_editor_property('destination_name',name);task.set_editor_property('automated',True);task.set_editor_property('save',False);task.set_editor_property('factory',u.FbxFactory())
        opts=u.FbxImportUI();opts.set_editor_property('import_mesh',True);opts.set_editor_property('import_as_skeletal',False);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False);opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
        data=opts.get_editor_property('static_mesh_import_data');data.set_editor_property('combine_meshes',True);data.set_editor_property('auto_generate_collision',False);data.set_editor_property('convert_scene',False);data.set_editor_property('generate_lightmap_u_vs',True);data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task.set_editor_property('options',opts);tasks.append(task)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);d['assets']=[]
    for name,m in outputs.items():
        asset=u.load_asset(folder+'/'+name);assert isinstance(asset,u.StaticMesh),name
        asset.set_material(0,material)
        # Simple convex collision for decorative stationary machinery; no physics by default.
        subsystem.add_simple_collisions(asset,u.ScriptingCollisionShapeType.BOX)
        assert u.EditorAssetLibrary.save_loaded_asset(asset,False)
        bounds=asset.get_bounds();tris=asset.get_num_triangles(0)
        assert tris>0
        d['assets'].append({'asset':asset.get_path_name(),'triangles':tris,'bounds':str(bounds),'material':asset.get_material(0).get_path_name()})
    d['success']=True
    u.EditorAssetLibrary.sync_browser_to_objects([folder+'/SM_ElevatorMachine']);u.get_editor_subsystem(u.AssetEditorSubsystem).open_editor_for_assets([u.load_asset(folder+'/SM_ElevatorMachine')])
except:d['error']=traceback.format_exc();u.log_error(d['error'])
(r/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
