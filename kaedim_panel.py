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
CREATED_OBJECTS = [] # List of ObjectAsset
TEMP_DIR = tempfile.mkdtemp()

'''
Define the Storage Structure of downlaoded assets
'''
class ObjectAsset:
    def __init__(self, name, online_filepath):
        self.name = name
        self.online_filepath = online_filepath
        self.local_filepath = None

'''
Define helper functions
'''
def display_info_message(message):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title="Info Message", icon='INFO')

'''
Define the Kaedim Panel
'''

# Function to download the image from the URL
def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    return False

# Function to load the image into Blender
def load_image(image_path):
    if os.path.exists(image_path):
        try:
            img = bpy.data.images.load(image_path)
        except RuntimeError:
            img = None
    else:
        img = None
    return img


# Custom property to hold the image
class ImageItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    asset_path : bpy.props.IntProperty()
    image: bpy.props.PointerProperty(type=bpy.types.Image)


class KAEDIM_PT_panel(bpy.types.Panel):
    bl_idname = 'KAEDIM_PT_PANEL'
    bl_label = 'Kaedim'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Kaedim'
 
    def draw(self, context):
        layout = self.layout
        scene = context.scene

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
#            
#            grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True)
            row = None
            for i, item in enumerate(scene.my_image_collection):
                if i % 2 == 0:
                    row = layout.row()
                box = row.box()
                col = box.column()
                col.template_ID_preview(item, "image", hide_buttons=True)
                col.operator("kaedim.add_object", text="Import").obj_idx = item.asset_path

                    
            

            

'''
Define the Panel's Operators
'''

class KAEDIM_OT_register_keys(bpy.types.Operator):
    bl_idname = "kaedim.register_keys"
    bl_label = "Register Keys"
    bl_description = "Register Keys"
    bl_category = 'Kaedim'
    bl_options = {'REGISTER'}
    
    def try_register(self, dev_id, api_key, destinationURL):
        # Call the API to retrieve the JWT
        global JWT
        url = "https://api.kaedim3d.com/api/v1/registerHook"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        body = {
            'devID': dev_id,
            'destination': destinationURL
        }
        try:
            response = requests.post(url, headers=headers, json=body)
            data = response.json()
            print('Received Response', data)
            if data['message'] == 'Webhook already registered':
                return False
            JWT = data['jwt']
            display_info_message('Keys successfully registered')
        except:
            return False
        return True



    def execute(self, context):
        # Get the text from the text boxes and save them to the global variables
        global DEV_ID, API_KEY
        DEV_ID = context.scene.dev_id
        API_KEY = context.scene.api_key
        
        destinationURL = 'http://example.com/invalid-webhook'
        attemptLimit = 3
        attempts = 0
        
        while attempts < attemptLimit:
            if self.try_register(DEV_ID, API_KEY, destinationURL): 
                break
            attempts += 1
            destinationURL += '1'


        if attempts == attemptLimit:
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
#            print("Response Data: ", data)  # 

            if not data or 'assets' not in data:
                display_info_message("No assets found in response")
                return {'CANCELLED'}

            global TEMP_DIR, CREATED_OBJECTS
            print("Objects stored in " + TEMP_DIR)
            CREATED_OBJECTS.clear()

            temp_dir = bpy.app.tempdir
            counter_index = 0

            for asset in data['assets']:
                try:
                    name = asset['image_tags'][0] if asset['image_tags'] else f"Asset_{counter_index}"
                    image_url = asset['image'][0] if asset['image'] else None
                    print(f'Looking at asset `{name}` ')

                    if not name:
                        continue

                    online_filepath = asset['iterations'][-1]['results']['obj'] if asset['iterations'] and 'results' in asset['iterations'][-1] else None
                    if not online_filepath:
                        continue

                    CREATED_OBJECTS.append(ObjectAsset(name, online_filepath))

                    temp_image_path = os.path.join(temp_dir, f"{name}_.png")
                    if download_image(image_url, temp_image_path):
                        img = load_image(temp_image_path)
                        if img:
                            item = bpy.context.scene.my_image_collection.add()
                            item.name = name
                            item.asset_path = counter_index
                            item.image = img
                    counter_index += 1

                except Exception as image_error:
                    print(f"Error processing asset {counter_index}: {image_error}")
                    # display_info_message(str(image_error))

            print('Finished looking at assets')
        except Exception as e:
            print(f"Error retrieving assets: {e}")
            display_info_message("Ran into error retrieving assets, try saving your keys again")
        return {'FINISHED'}

class KAEDIM_OT_add_object(bpy.types.Operator):
    bl_idname = "kaedim.add_object"
    bl_label = "Add Object"
    bl_description = "Add Object"

    obj_idx: bpy.props.IntProperty()

    def execute(self, context):
        global CREATED_OBJECTS
        print(f"the selected index is {self.obj_idx}")
        asset = CREATED_OBJECTS[self.obj_idx]
        if not asset.local_filepath:
            self.download_object(asset)
        print(asset.local_filepath)
        bpy.ops.wm.obj_import(filepath=asset.local_filepath)
        return {'FINISHED'}
    
    def download_object(self, asset: CREATED_OBJECTS):
        global TEMP_DIR, CREATED_OBJECTS
        img_response = requests.get(asset.online_filepath)
        local_filepath = os.path.join(TEMP_DIR, asset.name)
        with open(local_filepath, "wb") as file:
            file.write(img_response.content)
        asset.local_filepath = local_filepath

'''
Register newly defined operators, panels, and properties
'''

def register():
    bpy.utils.register_class(ImageItem)
    bpy.types.Scene.dev_id = bpy.props.StringProperty(
        name="Enter your DEV_ID from the portal here",
    )
    bpy.types.Scene.api_key = bpy.props.StringProperty(
        name="Enter your API_KEY from the portal here",
    )
    bpy.types.Scene.selected_file_name = bpy.props.StringProperty(name="Selected File", default="")
    bpy.types.Scene.my_image_collection = bpy.props.CollectionProperty(type=ImageItem)
    bpy.types.Scene.max_polycount = bpy.props.StringProperty(name="Desired Maximum Polycount, maximum 30000")
    bpy.types.Scene.quality_options = bpy.props.StringProperty(name='Desired Object Quality, must be "standard", "high", or "ultra"')
    bpy.utils.register_class(KAEDIM_PT_panel)
    bpy.utils.register_class(KAEDIM_OT_register_keys)
    bpy.utils.register_class(KAEDIM_OT_select_file)
    bpy.utils.register_class(KAEDIM_OT_upload_file)
    bpy.utils.register_class(KAEDIM_OT_retrieve_assets)
    bpy.utils.register_class(KAEDIM_OT_add_object)

def unregister():
    global DEV_ID, API_KEY, JWT, CREATED_OBJECTS
    for asset in CREATED_OBJECTS:
        os.remove(asset.local_filepath)
    DEV_ID, API_KEY, JWT, CREATED_OBJECTS = '', '', '', []
    bpy.utils.unregister_class(KAEDIM_PT_panel)
    bpy.utils.unregister_class(ImageItem)
    bpy.utils.unregister_class(KAEDIM_OT_register_keys)
    bpy.utils.unregister_class(KAEDIM_OT_select_file)
    bpy.utils.unregister_class(KAEDIM_OT_upload_file)
    bpy.utils.unregister_class(KAEDIM_OT_retrieve_assets)
    bpy.utils.unregister_class(KAEDIM_OT_add_object)
    del bpy.types.Scene.my_image_collection

if __name__ == '__main__':
    register()