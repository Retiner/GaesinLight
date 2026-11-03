"""Unreal Python commandlet check for the saved environment-light conversion."""
import hashlib
import json
import unreal

EXPECTED = {
    'Tutorial+Red': (156, 6222, 'f0cf091926a11ab71a992a57648dcc7d77ce5e105c6ddc51c60f39db4aa78630'),
    'Green': (108, 5998, '278e82cbc493bf1e80837f8084fe781a9e5b197a3fea7595bb1bbc20611e8c06'),
}
EXPECTED_TYPES = {'Tutorial+Red': (128, 12, 0, 16), 'Green': (100, 8, 0, 0)}
FIXTURES = {
    '/Game/BluePrint/BP_Floor_Plain_Light.BP_Floor_Plain_Light_C': 1,
    '/Game/BluePrint/BP_Wall_Light.BP_Wall_Light_C': 2,
    '/Game/BluePrint/BP_Ceiling_Light_High.BP_Ceiling_Light_High_C': 1,
    '/Game/BluePrint/BP_Ceiling_Wall_Light_High.BP_Ceiling_Wall_Light_High_C': 1,
}
TARGET_MESHES = {'SM_Floor_Plain_Light', 'SM_Wall_Light'}
subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for level, (expected_count, total, signature) in EXPECTED.items():
    world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Code/Levels/' + level)
    assert world, level
    actors = subsystem.get_all_level_actors()
    assert len(actors) == total, (level, len(actors))
    preserved = {}
    light_count = 0
    types = [0, 0, 0, 0]
    for actor in actors:
        class_path = actor.get_class().get_path_name()
        if class_path not in FIXTURES:
            if actor.get_class() == unreal.StaticMeshActor.static_class():
                component = actor.get_component_by_class(unreal.StaticMeshComponent)
                mesh = component.get_editor_property('static_mesh')
                assert not mesh or mesh.get_name() not in TARGET_MESHES, actor.get_actor_label()
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        shaft = 'Ceiling_Wall_Light_High' in class_path
        high = 'Ceiling_Light_High' in class_path
        normal = 'Floor_Plain' in class_path
        types[3 if shaft else 0 if high else 1 if normal else 2] += 1
        lights = actor.get_components_by_class(unreal.SpotLightComponent if high or shaft else unreal.RectLightComponent)
        if high or shaft:
            assert not actor.get_components_by_class(unreal.RectLightComponent)
        assert len(lights) == FIXTURES[class_path], actor.get_actor_label()
        light_count += len(lights)
        for light in lights:
            assert light.get_editor_property('intensity') > 0
            assert light.get_editor_property('intensity_units') == unreal.LightUnits.LUMENS
            color = light.get_editor_property('light_color')
            assert (color.r, color.g, color.b, color.a) == (225, 240, 245, 255)
            direction = light.get_editor_property('relative_rotation').get_forward_vector()
            if shaft:
                assert direction.x < -0.99, direction
                assert light.get_forward_vector().z < -0.99, actor.get_actor_label()
                assert light.get_editor_property('intensity') == 600
                assert light.get_editor_property('attenuation_radius') == 10000
                assert light.get_editor_property('inner_cone_angle') == 5
                assert light.get_editor_property('outer_cone_angle') == 10
                assert light.get_editor_property('use_inverse_squared_falloff')
            elif high:
                assert direction.z > 0.99, direction
                assert light.get_forward_vector().z < -0.99, actor.get_actor_label()
                assert 150 <= light.get_editor_property('intensity') <= 600
                assert 1000 <= light.get_editor_property('attenuation_radius') <= 2000
                assert light.get_editor_property('inner_cone_angle') == 30
                assert light.get_editor_property('outer_cone_angle') == 60
                assert light.get_editor_property('use_inverse_squared_falloff')
            elif normal:
                assert direction.z > 0.99, direction
                assert light.get_editor_property('intensity') == 80
                assert light.get_editor_property('attenuation_radius') == 600
            elif 'Back' in light.get_name():
                assert direction.x < -0.99, direction
            else:
                assert direction.x > 0.99, direction
            if not high and not normal and not shaft:
                assert light.get_editor_property('intensity') == 100
                assert light.get_editor_property('attenuation_radius') == 800
            assert light.get_editor_property('mobility') == unreal.ComponentMobility.MOVABLE
            assert not light.get_editor_property('cast_shadows')
            assert light.get_editor_property('max_draw_distance') == 0.0
            assert light.get_editor_property('max_distance_fade_range') == 0.0
            assert light.get_attach_parent() == component
        preserved[actor.get_actor_label()] = {
            'label': actor.get_actor_label(),
            'transform': actor.get_actor_transform().export_text(),
            'component_transform': component.get_world_transform().export_text(),
            'mesh': component.get_editor_property('static_mesh').get_path_name(),
            'materials': [component.get_material(i).get_path_name() if component.get_material(i) else None for i in range(component.get_num_materials())],
            'collision': str(component.get_collision_profile_name()),
            'collision_enabled': str(component.get_collision_enabled()),
            'mobility': str(component.get_editor_property('mobility')),
            'folder': str(actor.get_folder_path()),
            'tags': [str(tag) for tag in actor.tags],
            'parent': actor.get_attach_parent_actor().get_actor_label() if actor.get_attach_parent_actor() else None,
            'hidden': actor.get_editor_property('hidden'),
        }
    assert len(preserved) == expected_count, (level, len(preserved))
    assert tuple(types) == EXPECTED_TYPES[level], (level, types)
    digest = hashlib.sha256(json.dumps(preserved, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert digest == signature, 'Original instance settings changed in ' + level
    unreal.log('ENVIRONMENT_LIGHTS_PASS ' + level + ': ' + str(expected_count) + ' fixtures, ' + str(light_count) + ' lights')
for path in FIXTURES:
    blueprint = unreal.load_asset(path.split('.')[0])
    assert blueprint.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE, path
unreal.log('ENVIRONMENT_LIGHTS_VERIFICATION_COMPLETE')
