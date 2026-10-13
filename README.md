# Blender Quick STL

A small Blender sidebar add-on for exporting selected mesh objects to STL with a few buttons. Defaults to your **Downloads** folder; choose any other folder in the panel.

## Install from Blender's Python Console

Press **Shift+F4**, paste this single command, and press Enter:

```python
exec("import bpy, urllib.request, pathlib, addon_utils, importlib, sys\np = pathlib.Path(bpy.utils.user_resource('SCRIPTS', path='addons', create=True)) / 'quick_stl.py'\np.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/JoeMirai/blender-quick-stl/main/quick_stl.py', timeout=30).read())\naddon_utils.disable('quick_stl', default_set=False)\nimportlib.invalidate_caches(); sys.modules.pop('quick_stl', None)\naddon_utils.enable('quick_stl', default_set=True, persistent=True)\nbpy.ops.wm.save_userpref()")
```

The command downloads the add-on, enables it, and saves preferences so it loads next time. Alternatively install `quick_stl.py` with Preferences > Add-ons > Install from Disk.

## Use

Return to the 3D View with **Shift+F5**, select your objects, press **N**, and open **Quick STL**.

- **Export Selected → One STL** exports all selected meshes into one STL, retaining their relative positions.
- **Export Active Only** exports just the active mesh.
- **Export Each → Separate STLs** exports one file per selected mesh, using each object's name. An optional prefix is available.
- **STL name** automatically follows the active selected mesh (or the sole selected mesh). Type a different name to override it. The reset arrow restores automatic naming. This field controls the one-file and active-only buttons; separate exports use object names plus the prefix.
- **Folder** starts at `~/Downloads` and can be changed.
- **Include modifiers** exports visible evaluated geometry without applying modifiers to your Blender objects. Disable it to export the base mesh.
- **Millimeters** converts coordinate values using the scene's unit scale, so a 10 mm object remains 10 mm when imported into a slicer. STL files do not store unit metadata. With Unit System **None**, this option assumes one Blender unit is one millimeter. Choose **Raw Blender units** to bypass conversion.
- **Existing files** defaults to **Add number**, preventing replacement by appending `_001`, `_002`, etc. Choose **Overwrite** to replace matching files.
- **ASCII STL** is optional; compact binary STL is the default.
- **Open Export Folder** opens the destination in your file manager; **Copy Last Export Paths** copies the file paths.

Exports preserve the active object, selection, and Object/Edit Mode. In Edit Mode, the selected **objects** are exported in full, including unselected faces. Non-mesh objects are ignored. Files retain world position and Z-up orientation; objects are not automatically centered.

A multi-file failure may leave files already exported; the error reports that count. Folder/name/settings are stored with the Blender scene.

Blender 4.2+ targeted; tested on **Blender 5.2.0**.

## Tests

```sh
blender --background --factory-startup --python tests/test_blender.py
```

Tests export actual STL files and inspect dimensions and filenames, including combined/separate/active exports, unit scale conversion, ASCII output, collisions, and selection/mode restoration.

## License

GPL-3.0-or-later.
