# C:\Users\ericc\OneDrive\Coding\kaedim\final_plugin\
bl_info = {
    "name": "Kaedim Add On",
    "author": "Kaedim",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "location": "View3D > N-panel > Kaedim",
    "description": "Kaedim add on for blender",
    "category": "Kaedim",
}

import bpy
import requests
import tempfile
import os
'''
Define Required global variables
'''
DEV_ID = None
API_KEY = None
JWT = None
CREATED_OBJECTS = [] # List of pairs of (name, directory)

'''
Define helper functions
'''
def display_info_message(message):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title="Info Message", icon='INFO')

# 
'''
Define the Kaedim Panel
'''
class KAEDIM_PT_panel(bpy.types.Panel):
    bl_idname = 'KAEDIM_PT_PANEL'
    bl_label = 'Kaedim'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kaedim'
 
    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene, "dev_id", text="DEV ID")
        layout.prop(context.scene, "api_key", text="API KEY")
        layout.operator("kaedim.register_keys", text="Save Keys")


        global DEV_ID
        if not DEV_ID or not API_KEY or not JWT:
            layout.label(text='Add valid keys to enable further functionality')
        else:
            """
            Section for Uploading new file
            """
            layout.label(text='')
            layout.label(text='Convert new image to 3D')
            layout.label(text="Selected File: " + context.scene.selected_file_name)
            layout.operator("kaedim.select_file")
            # layout.prop(context.scene, "object_name", text="Object Name")
            layout.prop(context.scene, "max_polycount", text="Max Polycount")
            layout.prop(context.scene, "quality_options", text="Quality", expand=True)
            layout.operator("kaedim.upload_file")

            """
            Section for Adding existing Objects to Layout
            """
            layout.label(text='')
            layout.label(text='')
            layout.label(text='Import Assets From Kaedim')
            layout.label(text='Asset names are adjustable online')
            layout.operator("kaedim.retrieve_assets")
            layout.label(text='')
            for i in range(len(CREATED_OBJECTS)):
                layout.operator("kaedim.add_object", text=f'Add {CREATED_OBJECTS[i][0]}').obj_idx = i

            

'''
Define the Panel's Operators
'''

class KAEDIM_OT_register_keys(bpy.types.Operator):
    bl_idname = "kaedim.register_keys"
    bl_label = "Register Keys"
    bl_description = "Register Keys"
    bl_category = 'Kaedim'
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Get the text from the text boxes and save them to the global variables
        global DEV_ID, API_KEY, JWT
        DEV_ID = context.scene.dev_id
        API_KEY = context.scene.api_key
        
        # Call the API to retrieve the JWT
        url = "https://api.kaedim3d.com/api/v1/registerHook"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }
        body = {
            'devID': DEV_ID,
            'destination': 'http://example.com/invalid-webhook'
        }
        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()
            print('Received Response', data)
            JWT = data['jwt']
            display_info_message('Keys successfully registered')

        except Exception as e:
            display_info_message(f'Ran into an issue registering keys, please check your keys')

        return {'FINISHED'}

class KAEDIM_OT_select_file(bpy.types.Operator):
    bl_idname = "kaedim.select_file"
    bl_label = "Select File"
    bl_description = "Select File"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        context.scene.selected_file_name = self.filepath
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class KAEDIM_OT_upload_file(bpy.types.Operator):
    bl_idname = "kaedim.upload_file"
    bl_label = "Upload File"
    bl_description = "Upload File"

    def execute(self, context):
        # Validate inputs
        scene = context.scene
        pcount = scene.max_polycount
        quality = scene.quality_options.lower()
        # name = scene.object_name

        # if not name:
        #     display_info_message("Name cannot be empty")
        #     return {'CANCELLED'}

        if not pcount.isdigit() or not (0 < int(pcount) < 30000):
            display_info_message("Polycount must be a number less than 30000")
            return {'CANCELLED'}

        if quality not in ['standard', 'high', 'ultra']:
            display_info_message('Quality must be either "standard", "high", or "ultra"')
            return {'CANCELLED'}
             
        try:
            global API_KEY, JWT, DEV_ID
            url = "https://api.kaedim3d.com/api/v1/process"
            headers = {
                "X-API-Key": API_KEY,
                "Authorization": JWT
            }
            files = {
                'devID': (None, DEV_ID),
                'LoQ': (None, 'standard'),
                'polycount': (None, '20000'),
                'image': ('image.png', open(scene.selected_file_name, 'rb'), 'image/png'),
            }

            response = requests.post(url, headers=headers, files=files)
            if response.status_code == 201:
                # scene.object_name = ''
                scene.max_polycount = ''
                scene.quality_options = ''
                scene.selected_file_name = ''
                display_info_message('Sucessfully Uploaded')
            else:
                display_info_message(f"Request failed with status code: {response.status_code}, reason {response.reason}")
        except Exception as e:
            display_info_message('Error occurred sending request to server')
            print(e)
            return{'CANCELLED'}
        
        return {'FINISHED'}

class KAEDIM_OT_retrieve_assets(bpy.types.Operator):
    bl_idname = "kaedim.retrieve_assets"
    bl_label = "Retrieve Assets"
    bl_description = "Retrieve your assets to add them to blender"

    def execute(self, context):
        url = "https://api.kaedim3d.com/api/v1/fetchAll"
        headers = {
            "X-API-Key": API_KEY,
            "Authorization": JWT
        }
        body = {
            'devID': DEV_ID,
        }

        try:
            response = requests.get(url, headers=headers, json=body)
            data = response.json()

            temp_dir = tempfile.mkdtemp()
            print("Objects stored in " + temp_dir)
            global CREATED_OBJECTS
            CREATED_OBJECTS = []
            print('data received')
            print(data)
            for asset in data['assets']:
                print('looking at asset')
                try:
                    name = asset['image_tags'][0]
                    if not name: continue

                    online_filepath = asset['iterations'][-1]['results']
                    if type(online_filepath) != dict: continue
                    else: online_filepath = online_filepath['obj']

                    img_response = requests.get(online_filepath)
                    local_filepath = os.path.join(temp_dir, name)
                    with open(local_filepath, "wb") as file:
                        file.write(img_response.content)

                    CREATED_OBJECTS.append((name, local_filepath))

                except Exception as image_error:
                    display_info_message(image_error)
            print('exiting loop')

        except Exception as e:
            display_info_message("Ran into error retrieving assets, try saving your keys again")
        return {'FINISHED'}

class KAEDIM_OT_add_object(bpy.types.Operator):
    bl_idname = "kaedim.add_object"
    bl_label = "Add Object"
    bl_description = "Add Object"

    obj_idx: bpy.props.IntProperty()

    def execute(self, context):
        global CREATED_OBJECTS
        obj_filepath = CREATED_OBJECTS[self.obj_idx][1]
        bpy.ops.wm.obj_import(filepath=obj_filepath)
        return {'FINISHED'}

'''
Register newly defined operators, panels, and properties
'''
def register():
    bpy.types.Scene.dev_id = bpy.props.StringProperty(name="Enter your DEV_ID from the portal here")
    bpy.types.Scene.api_key = bpy.props.StringProperty(name="Enter your API_KEY from the portal here")
    bpy.types.Scene.selected_file_name = bpy.props.StringProperty(name="Selected File", default = "")
    # bpy.types.Scene.object_name = bpy.props.StringProperty(name="Desired Object Name")
    bpy.types.Scene.max_polycount = bpy.props.StringProperty(name="Desired Maximum Polycount, maximum 30000")
    bpy.types.Scene.quality_options = bpy.props.StringProperty(name='Desired Object Quality, must be "standard", "high", or "ultra"')
    bpy.utils.register_class(KAEDIM_PT_panel)
    bpy.utils.register_class(KAEDIM_OT_register_keys)
    bpy.utils.register_class(KAEDIM_OT_select_file)
    bpy.utils.register_class(KAEDIM_OT_upload_file)
    bpy.utils.register_class(KAEDIM_OT_retrieve_assets)
    bpy.utils.register_class(KAEDIM_OT_add_object)

'''
Clean up all stored data
'''
def unregister():
    global DEV_ID, API_KEY, JWT, CREATED_OBJECTS
    for (_, filepath) in CREATED_OBJECTS:
        os.remove(filepath)
    DEV_ID, API_KEY, JWT, CREATED_OBJECTS = '', '', '', []
    bpy.utils.unregister_class(KAEDIM_PT_panel)
    bpy.utils.unregister_class(KAEDIM_OT_register_keys)
    bpy.utils.unregister_class(KAEDIM_OT_select_file)
    bpy.utils.unregister_class(KAEDIM_OT_upload_file)
    bpy.utils.unregister_class(KAEDIM_OT_retrieve_assets)
    bpy.utils.unregister_class(KAEDIM_OT_add_object)

 
if __name__ == '__main__':
    register()