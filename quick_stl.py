bl_info = {
    'name': 'Quick STL Export', 'author': 'JoeMirai',
    'version': (1, 0, 0), 'blender': (4, 2, 0),
    'location': '3D View > Sidebar > Quick STL',
    'description': 'Export selected meshes to Downloads with millimeter sizing and editable names',
    'category': 'Import-Export',
}

import re
from pathlib import Path
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, PointerProperty


def default_folder():
    return str(Path.home() / 'Downloads')


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    if name.lower().endswith('.stl'):
        name = name[:-4].rstrip(' .')
    return name or 'export'


def mesh_selection(context, active_only=False):
    if active_only:
        return [context.active_object] if context.active_object and context.active_object.type == 'MESH' else []
    return sorted([obj for obj in context.selected_objects if obj.type == 'MESH'], key=lambda obj: obj.name)


def automatic_name(context, objects=None):
    objects = objects if objects is not None else mesh_selection(context)
    if len(objects) == 1:
        return safe_name(objects[0].name)
    if context.active_object in objects:
        return safe_name(context.active_object.name)
    return safe_name(objects[0].name) if objects else 'selection'


def filename_get(settings):
    # No override means the name follows the current object selection automatically.
    return settings.get('filename_override', '') or automatic_name(bpy.context)


def filename_set(settings, value):
    settings['filename_override'] = value.strip()


def export_scale(scene, sizing):
    if sizing == 'RAW':
        return 1.0
    # STL has no units. Slicers generally interpret its numbers as millimeters.
    return scene.unit_settings.scale_length * 1000.0 if scene.unit_settings.system != 'NONE' else 1.0


def output_path(folder, name, overwrite):
    base = folder / (safe_name(name) + '.stl')
    if overwrite == 'OVERWRITE' or not base.exists():
        return base
    number = 1
    while True:
        candidate = folder / f'{base.stem}_{number:03d}.stl'
        if not candidate.exists():
            return candidate
        number += 1


class QUICK_STL_Settings(bpy.types.PropertyGroup):
    folder: StringProperty(name='Folder', subtype='DIR_PATH', default=default_folder())
    filename: StringProperty(name='STL name', get=filename_get, set=filename_set,
        description='Default follows the selected object. Edit to override; reset with the arrow button')
    prefix: StringProperty(name='Separate-file prefix', default='',
        description='Optional prefix; each separate STL otherwise uses its object name')
    apply_modifiers: BoolProperty(name='Include modifiers', default=True,
        description='Export evaluated geometry, including Boolean and Displace modifiers, without applying them to your objects')
    sizing: EnumProperty(name='Sizing', items=[
        ('MM', 'Millimeters', 'Convert scene units into mm. For Unit System None, treat one Blender unit as one mm'),
        ('RAW', 'Raw Blender units', 'Export coordinate values without unit conversion')], default='MM')
    overwrite: EnumProperty(name='Existing files', items=[
        ('UNIQUE', 'Add number', 'Keep existing files and use _001, _002, etc.'),
        ('OVERWRITE', 'Overwrite', 'Replace files with matching names')], default='UNIQUE')
    ascii_format: BoolProperty(name='ASCII STL', default=False,
        description='Use readable ASCII instead of compact binary STL')
    last_export: StringProperty(name='Last export', default='')


class QUICK_STL_OT_reset_name(bpy.types.Operator):
    bl_idname = 'quick_stl.reset_name'
    bl_label = 'Use Object Name'
    bl_description = 'Reset the STL name to follow the selected object automatically'
    bl_options = {'UNDO'}

    def execute(self, context):
        context.scene.quick_stl_settings['filename_override'] = ''
        return {'FINISHED'}


class QUICK_STL_OT_export(bpy.types.Operator):
    bl_idname = 'quick_stl.export'
    bl_label = 'Export STL'
    bl_description = 'Export meshes without changing their geometry or modifiers'
    kind: EnumProperty(items=[('COMBINED', 'Selected to one STL', ''),
        ('SEPARATE', 'One STL per object', ''), ('ACTIVE', 'Active object only', '')])

    @classmethod
    def poll(cls, context):
        return context.mode in {'OBJECT', 'EDIT_MESH'} and bool(mesh_selection(context))

    def execute(self, context):
        settings = context.scene.quick_stl_settings
        objects = mesh_selection(context, self.kind == 'ACTIVE')
        if not objects:
            self.report({'ERROR'}, 'Select at least one mesh object.')
            return {'CANCELLED'}
        folder_text = settings.folder.strip()
        if not folder_text:
            self.report({'ERROR'}, 'Choose an export folder.')
            return {'CANCELLED'}
        folder = Path(bpy.path.abspath(folder_text)).expanduser().resolve()
        original_selected = list(context.selected_objects)
        original_active = context.view_layer.objects.active
        original_mode = context.mode
        paths = []
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')
            if self.kind == 'SEPARATE':
                batches = [([obj], settings.prefix + obj.name) for obj in objects]
            else:
                # Active-only naming uses active object unless the user set a custom override.
                name = settings.get('filename_override', '') or automatic_name(context, objects)
                batches = [(objects, name)]
            for batch, name in batches:
                for obj in list(context.selected_objects):
                    obj.select_set(False)
                for obj in batch:
                    obj.select_set(True)
                context.view_layer.objects.active = batch[0]
                destination = output_path(folder, name, settings.overwrite)
                result = bpy.ops.wm.stl_export(
                    filepath=str(destination), check_existing=False,
                    export_selected_objects=True, use_batch=False,
                    apply_modifiers=settings.apply_modifiers,
                    global_scale=export_scale(context.scene, settings.sizing),
                    use_scene_unit=False, ascii_format=settings.ascii_format,
                    forward_axis='Y', up_axis='Z', evaluation_mode='DAG_EVAL_VIEWPORT',
                )
                if result != {'FINISHED'} or not destination.is_file():
                    raise RuntimeError('STL export did not finish: ' + str(destination))
                paths.append(str(destination))
            settings.last_export = '\n'.join(paths)
            self.report({'INFO'}, f'Exported {len(paths)} STL file(s) to {folder}')
            return {'FINISHED'}
        except Exception as exc:
            settings.last_export = '\n'.join(paths)
            self.report({'ERROR'}, f'{exc}' + (f' ({len(paths)} file(s) already exported)' if paths else ''))
            return {'CANCELLED'}
        finally:
            for obj in list(context.selected_objects):
                obj.select_set(False)
            for obj in original_selected:
                obj.select_set(True)
            context.view_layer.objects.active = original_active
            if original_mode == 'EDIT_MESH' and original_active:
                bpy.ops.object.mode_set(mode='EDIT')


class QUICK_STL_OT_open_folder(bpy.types.Operator):
    bl_idname = 'quick_stl.open_folder'
    bl_label = 'Open Export Folder'

    def execute(self, context):
        folder = Path(bpy.path.abspath(context.scene.quick_stl_settings.folder)).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.path_open(filepath=str(folder.resolve()))
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class QUICK_STL_OT_copy_paths(bpy.types.Operator):
    bl_idname = 'quick_stl.copy_paths'
    bl_label = 'Copy Last Export Paths'

    def execute(self, context):
        context.window_manager.clipboard = context.scene.quick_stl_settings.last_export
        return {'FINISHED'}


class QUICK_STL_PT_panel(bpy.types.Panel):
    bl_label = 'Quick STL Export'
    bl_idname = 'QUICK_STL_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Quick STL'

    def draw(self, context):
        layout = self.layout
        s = context.scene.quick_stl_settings
        count = len(mesh_selection(context))
        layout.label(text=f'{count} selected mesh object(s)')
        layout.prop(s, 'folder')
        row = layout.row(align=True)
        row.prop(s, 'filename')
        row.operator('quick_stl.reset_name', text='', icon='LOOP_BACK')
        op = layout.operator('quick_stl.export', text='Export Selected → One STL', icon='EXPORT')
        op.kind = 'COMBINED'
        op = layout.operator('quick_stl.export', text='Export Active Only', icon='MESH_DATA')
        op.kind = 'ACTIVE'
        layout.separator()
        layout.prop(s, 'prefix')
        op = layout.operator('quick_stl.export', text='Export Each → Separate STLs', icon='DOCUMENTS')
        op.kind = 'SEPARATE'
        layout.separator()
        layout.prop(s, 'apply_modifiers')
        layout.prop(s, 'sizing')
        if context.scene.unit_settings.system == 'NONE' and s.sizing == 'MM':
            layout.label(text='No scene units: 1 Blender unit = 1 mm', icon='INFO')
        layout.prop(s, 'overwrite')
        layout.prop(s, 'ascii_format')
        layout.operator('quick_stl.open_folder', icon='FILE_FOLDER')
        if s.last_export:
            layout.label(text=Path(s.last_export.splitlines()[-1]).name, icon='CHECKMARK')
            layout.operator('quick_stl.copy_paths', icon='COPYDOWN')


CLASSES = (QUICK_STL_Settings, QUICK_STL_OT_reset_name, QUICK_STL_OT_export,
           QUICK_STL_OT_open_folder, QUICK_STL_OT_copy_paths, QUICK_STL_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.quick_stl_settings = PointerProperty(type=QUICK_STL_Settings)


def unregister():
    if hasattr(bpy.types.Scene, 'quick_stl_settings'):
        del bpy.types.Scene.quick_stl_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
