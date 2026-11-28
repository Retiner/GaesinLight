"""Match the MainManu button typeface and render ending glyphs sharply."""
import unreal as u,json,traceback,shutil
from pathlib import Path
r=Path(u.Paths.project_saved_dir())/'CodexBackups/EndingFont-20261128';r.mkdir(parents=True,exist_ok=True);d={}
try:
 root=Path(u.Paths.project_dir());src=(root/'Tools/Create-EndingLevels.py').read_text(encoding='utf-8')
 # Reuse the standalone graph construction helpers without running map creation.
 exec(src[:src.index("r=Path(u.Paths.project_saved_dir())")],globals())
 lib=u.BlueprintEditorLibrary;GE=u.BlueprintGraphEditor;M='/Script/Engine.KismetMathLibrary.'
 backup=root/'Content/UI/BP_EndingHUD.uasset'
 if not (r/'BP_EndingHUD.before.uasset').exists():shutil.copy2(backup,r/'BP_EndingHUD.before.uasset')
 menu=u.load_asset('/Game/UI/WBP_MainMenu')
 menu_texts=[t for t in u.ObjectIterator(u.TextBlock) if t.get_path_name().startswith('/Game/UI/WBP_MainMenu.') and t.get_name() in ['Text_NewGame','Text_Continue']]
 assert menu_texts,'Menu text widgets not found'
 info=menu_texts[0].get_editor_property('font');sourcefont=info.get_editor_property('font_object');typeface=info.get_editor_property('typeface_font_name')
 assert all(t.get_editor_property('font').get_editor_property('font_object')==sourcefont for t in menu_texts)
 path='/Game/UI/Fonts/F_Ending_MainMenu';font=u.load_asset(path)
 if not font:font=u.EditorAssetLibrary.duplicate_asset(sourcefont.get_path_name(),path)
 assert font and font.get_editor_property('font_cache_type')==u.FontCacheType.RUNTIME
 font.set_editor_property('legacy_font_size',256);font.set_editor_property('legacy_font_name',typeface);assert u.EditorAssetLibrary.save_loaded_asset(font,False)
 base_font_size=u.load_asset('/Engine/EngineFonts/Roboto').get_editor_property('legacy_font_size')
 bp=u.load_asset('/Game/UI/BP_EndingHUD');e=GE.get_graph_editor_by_name(bp,'EventGraph');e.remove_nodes(list(e.list_all_nodes()))
 draw=lib.add_event_override(bp,'ReceiveDrawHUD',u.IntPoint());lib.compile_blueprint(bp)
 segment=src[src.index(" g=G('EventGraph',True);w="):src.index(' compile_save(bp)')]
 exec('\n'.join(line[1:] for line in segment.splitlines()),globals())
 lib.compile_blueprint(bp);errors=[n.error_msg for gr in lib.list_graphs(bp) for n in GE.get_graph_editor(gr).list_nodes_with_errors()];assert not errors,errors;assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
 d.update(success=True,source_font=sourcefont.get_path_name(),ending_font=font.get_path_name(),typeface=str(typeface),glyph_size=256,previous_glyph_size=base_font_size,errors=errors)
except:d['error']=traceback.format_exc();u.log_error(d['error'])
(r/'result.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
