"""Create two character-free, black-screen ending maps and shared Blueprint logic."""
import unreal as u,json,traceback
from pathlib import Path

def wire(a,b):
 assert a.is_valid() and b.is_valid()
 assert a.try_create_connection(b)

def literal(p,v):
 assert p.is_valid() and p.set_pin_value(str(v))

class G:
 def __init__(self,name,existing=False):
  self.e=GE.get_graph_editor_by_name(bp,name) if existing else GE.create_and_edit_function_graph(bp,name)
  self.x=0;self.y=0
 def node(self,n):
  assert n
  n.set_node_pos(u.IntPoint(self.x,self.y));self.x+=270
  if self.x>2700:self.x=0;self.y+=500
  return n
 def feed(self,v,p):
  wire(v,p) if isinstance(v,u.BlueprintGraphPin) else literal(p,v)
 def call(self,f,**args):
  n=self.node(self.e.add_call_function_node(f))
  for k,v in sorted(args.items(),key=lambda item:not isinstance(item[1],u.BlueprintGraphPin)):self.feed(v,n.find_input_pin(k))
  return n
 def get(self,name):return self.node(self.e.add_get_member_variable_node(name)).find_output_pin(name)
 def set(self,name,v):
  n=self.node(self.e.add_set_member_variable_node(name));self.feed(v,n.find_input_pin(name));return n
 def op(self,n,a=None,b=None):
  args={}
  if a is not None:args['A']=a
  if b is not None:args['B']=b
  return self.call(M+n,**args).find_result_pin()
 def entry(self):return self.e.find_graph_entry_pin()
 def chain(self,p,*nodes):
  for n in nodes:wire(p,n.find_execute_pin());p=n.find_then_pin()
  return p
 def gate(self,p,c):
  n=self.node(self.e.add_branch_node());wire(c,n.find_input_pin('Condition'));wire(p,n.find_execute_pin());return n.find_then_pin()

r=Path(u.Paths.project_saved_dir())/'CodexBackups/EndingLevels-20261128';r.mkdir(parents=True,exist_ok=True);d={}
try:
 lib=u.BlueprintEditorLibrary;GE=u.BlueprintGraphEditor;assets=[]
 hudpath='/Game/UI/BP_EndingHUD';actorpath='/Game/BluePrint/BP_EndingSequence';gmpath='/Game/GameMode/BP_EndingGameMode'
 for path in [hudpath,actorpath,gmpath,'/Game/Code/Levels/Level_Ending_1','/Game/Code/Levels/Level_Ending_2']:assert not u.EditorAssetLibrary.does_asset_exist(path),path
 M='/Script/Engine.KismetMathLibrary.';S='/Script/Engine.KismetSystemLibrary.';ACT='/Script/Engine.Actor.'
 types={n:lib.get_basic_type_by_name(n) for n in ['bool','real','string','text','name']}
 def arg(g,n):return g.e.list_nodes_of_class(u.K2Node_FunctionEntry)[0].find_output_pin(n)
 def variable(g,n,t,default='',edit=False,cat='Ending Internal'):
  assert g.e.add_member_variable(n,t,default);lib.set_blueprint_variable_instance_editable(bp,n,edit);lib.set_blueprint_variable_category(bp,n,cat)
 def errors(a):return [(a.get_name(),gr.get_name(),n.error_msg) for gr in lib.list_graphs(a) for n in GE.get_graph_editor(gr).list_nodes_with_errors()]
 def compile_save(a):
  lib.compile_blueprint(a);assert not errors(a),errors(a);assert u.EditorAssetLibrary.save_loaded_asset(a,False)
 # Canvas caches glyphs at LegacyFontSize before applying Scale. Use large
 # glyphs from the menu's typeface so FontScale=10 stays sharp.
 fontpath='/Game/UI/Fonts/F_Ending_MainMenu'
 font=u.load_asset(fontpath)
 if not font:
  font=u.EditorAssetLibrary.duplicate_asset('/Game/Effect/Font/ChaiHwaljjak-Medium_Font',fontpath)
 assert font
 font.set_editor_property('legacy_font_size',256);font.set_editor_property('legacy_font_name','Default');u.EditorAssetLibrary.save_loaded_asset(font,False)
 base_font_size=u.load_asset('/Engine/EngineFonts/Roboto').get_editor_property('legacy_font_size')
 # Canvas HUD draws a solid black background, then white text with animated opacity.
 bp=lib.create_blueprint_asset_with_parent(hudpath,u.HUD);hudbp=bp;assets.append(bp)
 conf=G('ConfigureEndingText');alpha=G('SetEndingTextOpacity')
 for n,t,v in [('EndingDisplayText',types['string'],''),('EndingTextOpacity',types['real'],'0.0'),('EndingFontScale',types['real'],'3.0')]:variable(conf,n,t,v)
 conf.e.add_graph_input_parameter('Text',types['string']);conf.e.add_graph_input_parameter('FontScale',types['real']);alpha.e.add_graph_input_parameter('Opacity',types['real'])
 draw=lib.add_event_override(bp,'ReceiveDrawHUD',u.IntPoint());assert draw;lib.compile_blueprint(bp)
 g=conf;g.chain(g.entry(),g.set('EndingDisplayText',arg(g,'Text')),g.set('EndingFontScale',g.op('FMax',arg(g,'FontScale'),.1)),g.set('EndingTextOpacity',0))
 g=alpha;g.chain(g.entry(),g.set('EndingTextOpacity',g.call(M+'FClamp',Value=arg(g,'Opacity'),Min=0,Max=1).find_result_pin()))
 g=G('EventGraph',True);w=g.call(M+'Conv_IntToDouble',InInt=draw.find_output_pin('SizeX')).find_result_pin();h=g.call(M+'Conv_IntToDouble',InInt=draw.find_output_pin('SizeY')).find_result_pin()
 p=g.chain(draw.find_then_pin(),g.call('/Script/Engine.HUD.DrawRect',RectColor='(R=0,G=0,B=0,A=1)',ScreenX=0,ScreenY=0,ScreenW=w,ScreenH=h))
 scale=g.op('Multiply_DoubleDouble',g.op('Multiply_DoubleDouble',g.get('EndingFontScale'),g.op('Divide_DoubleDouble',h,1080)),base_font_size/256.0)
 measure=g.call('/Script/Engine.HUD.GetTextSize',Text=g.get('EndingDisplayText'),Font=font.get_path_name(),Scale=scale)
 if measure.find_execute_pin().is_valid():p=g.chain(p,measure)
 tw=measure.find_output_pin('OutWidth');th=measure.find_output_pin('OutHeight')
 fit=g.op('FMin',1,g.op('Divide_DoubleDouble',g.op('Multiply_DoubleDouble',w,.86),g.op('FMax',tw,1)))
 x=g.op('Multiply_DoubleDouble',g.op('Subtract_DoubleDouble',w,g.op('Multiply_DoubleDouble',tw,fit)),.5);y=g.op('Multiply_DoubleDouble',g.op('Subtract_DoubleDouble',h,g.op('Multiply_DoubleDouble',th,fit)),.5)
 white=g.call(M+'MakeColor',R=1,G=1,B=1,A=g.get('EndingTextOpacity')).find_result_pin()
 g.chain(p,g.call('/Script/Engine.HUD.DrawText',Text=g.get('EndingDisplayText'),TextColor=white,ScreenX=x,ScreenY=y,Font=font.get_path_name(),Scale=g.op('Multiply_DoubleDouble',scale,fit),bScalePosition='false'))
 compile_save(bp)
 # Per-map settings live on an editable actor. No pawn or character is spawned.
 bp=lib.create_blueprint_asset_with_parent(actorpath,u.Actor);sequencebp=bp;assets.append(bp)
 init=G('InitializeEnding');step=G('UpdateEnding');ret=G('ReturnToMainMenu')
 configs=[('EndingText',types['text'],''),('InitialBlackDelay',types['real'],'2.0'),('TextFadeInDuration',types['real'],'2.0'),('TextHoldDuration',types['real'],'4.0'),('TextFadeOutDuration',types['real'],'2.0'),('FinalBlackDelay',types['real'],'2.0'),('FontScale',types['real'],'3.0'),('ReturnLevel',types['name'],'/Game/Code/Levels/MainManu')]
 for n,t,v in configs:variable(init,n,t,v,True,'Ending Settings')
 for n,t,v in [('EndingInitialized',types['bool'],'false'),('EndingFinished',types['bool'],'false'),('EndingElapsed',types['real'],'0.0'),('CurrentTextOpacity',types['real'],'0.0'),('EndingHUD',lib.get_object_reference_type(lib.generated_class(hudbp)),'None')]:variable(init,n,t,v)
 step.e.add_graph_input_parameter('DeltaSeconds',types['real'])
 begin=lib.add_event_override(bp,'ReceiveBeginPlay',u.IntPoint());tick=lib.add_event_override(bp,'ReceiveTick',u.IntPoint(0,400));assert begin and tick
 lib.compile_blueprint(bp)
 g=init;p=g.gate(g.entry(),g.op('Not_PreBool',g.get('EndingInitialized')))
 pc=g.call('/Script/Engine.GameplayStatics.GetPlayerController',PlayerIndex=0).find_result_pin();p=g.gate(p,g.call(S+'IsValid',Object=pc).find_result_pin())
 cast=g.node(g.e.create_node_from_name('Utilities|Casting|CastToCharacter',u.Vector2D(),[]));assert g.e.retarget_node_class(cast,u.Character,lib.generated_class(hudbp));wire(g.call('/Script/Engine.PlayerController.GetHUD',self=pc).find_result_pin(),cast.find_input_pin('Object'));wire(p,cast.find_execute_pin());ref=next(q for q in cast.list_output_pins() if str(q.get_pin_name()).startswith('As'))
 txt=g.call('/Script/Engine.KismetTextLibrary.Conv_TextToString',InText=g.get('EndingText')).find_result_pin()
 p=g.chain(cast.find_then_pin(),g.set('EndingHUD',ref),g.call(hudpath+'.BP_EndingHUD_C.ConfigureEndingText',self=ref,Text=txt,FontScale=g.get('FontScale')),g.set('EndingInitialized','true'),g.call('/Script/Engine.Controller.SetIgnoreMoveInput',self=pc,bNewMoveInput='true'),g.call('/Script/Engine.Controller.SetIgnoreLookInput',self=pc,bNewLookInput='true'))
 camera=g.call('/Script/Engine.GameplayStatics.GetPlayerCameraManager',PlayerIndex=0).find_result_pin()
 g.chain(p,g.call('/Script/Engine.PlayerCameraManager.SetManualCameraFade',self=camera,InFadeAmount=1,Color='(R=0,G=0,B=0,A=1)',bInFadeAudio='false'))
 g=step;p=g.gate(g.entry(),g.op('Not_PreBool',g.get('EndingFinished')));p=g.chain(p,g.call('InitializeEnding'));p=g.gate(p,g.get('EndingInitialized'))
 p=g.chain(p,g.set('EndingElapsed',g.op('Add_DoubleDouble',g.get('EndingElapsed'),g.op('FMax',arg(g,'DeltaSeconds'),0))))
 dur=lambda n:g.op('FMax',g.get(n),0)
 start=dur('InitialBlackDelay');fadein=dur('TextFadeInDuration');hold=dur('TextHoldDuration');fadeout=dur('TextFadeOutDuration');end=dur('FinalBlackDelay')
 fadeout_start=g.op('Add_DoubleDouble',g.op('Add_DoubleDouble',start,fadein),hold);total=g.op('Add_DoubleDouble',g.op('Add_DoubleDouble',fadeout_start,fadeout),end)
 clamp=lambda x:g.call(M+'FClamp',Value=x,Min=0,Max=1).find_result_pin()
 a=clamp(g.op('Divide_DoubleDouble',g.op('Subtract_DoubleDouble',g.get('EndingElapsed'),start),g.op('FMax',fadein,.0001)))
 b=g.op('Subtract_DoubleDouble',1,clamp(g.op('Divide_DoubleDouble',g.op('Subtract_DoubleDouble',g.get('EndingElapsed'),fadeout_start),g.op('FMax',fadeout,.0001))))
 p=g.chain(p,g.set('CurrentTextOpacity',g.op('FMin',a,b)),g.call(hudpath+'.BP_EndingHUD_C.SetEndingTextOpacity',self=g.get('EndingHUD'),Opacity=g.get('CurrentTextOpacity')))
 p=g.gate(p,g.op('GreaterEqual_DoubleDouble',g.get('EndingElapsed'),total));g.chain(p,g.call('ReturnToMainMenu'))
 g=ret;p=g.gate(g.entry(),g.op('Not_PreBool',g.get('EndingFinished')));g.chain(p,g.set('EndingFinished','true'),g.call(ACT+'SetActorTickEnabled',bEnabled='false'),g.call('/Script/Engine.GameplayStatics.OpenLevel',LevelName=g.get('ReturnLevel'),bAbsolute='true'))
 g=G('EventGraph',True);g.chain(begin.find_then_pin(),g.call('InitializeEnding'));g.chain(tick.find_then_pin(),g.call('UpdateEnding',DeltaSeconds=tick.find_output_pin('DeltaSeconds')))
 compile_save(bp)
 bp=lib.create_blueprint_asset_with_parent(gmpath,u.GameModeBase);gmbp=bp;assets.append(bp);lib.compile_blueprint(bp)
 c=u.get_default_object(lib.generated_class(bp));c.set_editor_property('default_pawn_class',None);c.set_editor_property('spectator_class',None);c.set_editor_property('player_controller_class',u.PlayerController);c.set_editor_property('hud_class',lib.generated_class(hudbp));compile_save(bp)
 # Build inactive worlds without changing or saving the currently open user map.
 gs=u.get_default_object(u.GameplayStatics);d['maps']=[]
 for i in [1,2]:
  name='Level_Ending_'+str(i);path='/Game/Code/Levels/'+name
  world=u.AssetToolsHelpers.get_asset_tools().create_asset(name,'/Game/Code/Levels',u.World,u.WorldFactory());assert world
  world.get_world_settings().set_editor_property('default_game_mode',lib.generated_class(gmbp))
  t=u.Transform();actor=gs.call_method('BeginDeferredActorSpawnFromClass',args=(world,lib.generated_class(sequencebp),t,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT));assert actor
  actor.set_editor_property('EndingText',u.Text('엔딩 '+str(i)));actor=gs.call_method('FinishSpawningActor',args=(actor,t,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT));actor.set_actor_label('Ending_Settings_'+str(i))
  assert u.EditorLoadingAndSavingUtils.save_map(world,path)
  d['maps'].append({'map':path,'settings_actor':actor.get_actor_label(),'text':str(actor.get_editor_property('EndingText'))})
 d['errors']=[e for a in assets for e in errors(a)];assert not d['errors'];d['success']=True
except:d['error']=traceback.format_exc();u.log_error(d['error'])
(r/'build.json').write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
