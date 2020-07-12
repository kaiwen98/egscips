################################################# SPACEY Initiation GUI Wizard #############################################
# Author: Looi Kai Wen                                                                                                     #
# Last edited: 11/07/2020                                                                                                  #
# Summary:                                                                                                                 #
#   For use by BLE network administrators to configure their database with invariant information,                          #
#   eg. relative coordinates of the sensor mote, cluster level, etc.                                                       #
############################################################################################################################


from tkinter import *
import classdef as spc
from tkinter import filedialog
import config as cfg
from sensor_data import *
import imgpro
import os
from os.path import dirname as dir, splitext, basename, join
import sys
import base64


# Need to choose depending on running from exe or py. Should point to /Spacey API
#root = dir(dir(dir(sys.executable)))
_root = dir(dir(__file__)) 

# To extract database interface functions
sys.path.append(join(_root, "Redis"))
import redisDB
# Relevant file directories

floorplan_folder_input = os.path.join(_root, "floorplan_images", "input floorplan")
floorplan_folder_output = os.path.join(_root, "floorplan_images", "output floorplan")
json_folder = os.path.join(_root, "json_files")

# Default folder for JSON files
json_folder_config = os.path.join(json_folder, "config")

# Image Assets
image_folder = os.path.join(_root, "images")
image_asset_folder = os.path.join(image_folder, "assets")
image_output_graphic_folder = os.path.join(image_folder, "output graphic")
icon_path = os.path.join(image_asset_folder, "spacey_icon.ico")
gif_path = os.path.join(image_asset_folder, "spacey_icon.gif")
nodeOff_path = os.path.join(image_asset_folder,"unoccupied_nodes.png")
nodeOn_path = os.path.join(image_asset_folder, "occupied_nodes.png")
private_key_folder = os.path.join(_root, "private key")

# Database information
"""
remote_host = 'redis-13969.c11.us-east-1-3.ec2.cloud.redislabs.com'
password = 'PbKFE8lJq8HFGve4ON5rRFXhlVrGYUHL'
port = '13969'
"""
remote_host = 'localhost'
password = None
port = '6379'


database = redisDB.redis_database(_root, remote_host, port, password)

# Global Variables
root = None #TK window root
x_list = [] #list of all possible coordinates
y_list = []
img = None #image file 
num_coordinates_max = 0 #max num of coordinates
res = None #glb restaurant space
node = None #node pointer
x, y = 0, 0 #mid coords of the latest node placed
x_bb1, y_bb1 = 0,0 #Bounding box coordinates of active canva region (blue)
x_bb2, y_bb2 = 0,0
deposit_flag = True #If a node can be deposit on the spot
updateTextDone = False # Signal update of err msg
myCanvas = None #glb myCanvasObj
node_idx = None
prev_node_idx = None
step = 5 #dist between each grid line
toggle = 0 #toggle btw entry[left] or canvas
initflag = 0 #detect correct user input
error = None #error obj
error_font = None #error font
json_font = None #json font
max_step = 200 #prevent grid line from scaling down to self collapse
hlcolor = "yellow" #glb highlight color
cursor = None #glb cursor
box_len = step #length of node
scale = 50 #num of grid lines along x axis
bg = None #backgroun sky blue
prepimgpath = None #path of image
postimgpath = None
pady = 5 #padding for widget format
padx = 5
grid = None
filename = ""
img_padding = 0
image_flag = False
load_flag = False
img_x_bb1 = -1 #img bb box corner
img_y_bb1 = -1
cfg.db_options = ["No Database Selected"] 

export_to_local = False
import_from_local = False

# Variables that will be stored to restore save states with the Node Manager
config_op = ["image_flag", "x_bb1", "x_bb2", "y_bb1", "y_bb2", "img_x_bb1", "img_y_bb1", "box_len", "prepimgpath", "scale", "postimgpath", "img_padding"]

# Dictionaries for JSON compilation purposes.
configinfo = {}
devinfo = {}

json_zipinfo = {}
json_occupancy = {}
json_hash = {}
json_coord = {}
output_graphic_coord = {}

def save_private_key(key, name):
    file_path = os.path.join(cfg.private_key_folder, name+".bin")
    with open(file_path, "wb") as outfile:
        outfile.write(key)
    outfile.close()

def load_private_key(name):
    file_path = os.path.join(cfg.private_key_folder, name+".bin")
    try:
        with open(file_path, "rb") as infile:
            key = infile.read()
        return key
    except:
        return 0



# File functions
def getbasename(path):
    return splitext(basename(path))[0]


# Return filename of the new output graphic
def get_output_graphic_path():
    result = os.path.join(image_output_graphic_folder, "output_"+cfg.session_name+".png")
    return result

def get_output_floor_plan_path():
    result = os.path.join(floorplan_folder_output, "processed_img_"+cfg.session_name+".png")
    return result


# Serializes image from png to string
def json_serialize_image(image_file):
    with open(image_file, mode='rb') as file:
        img = file.read()
    return base64.b64encode(img).decode("utf-8") #picture to bytes, then to string 

# Deserializes image from string to png, then save it in the specified file directory
def json_deserialize_image(encoded_str,image_file):
    result = encoded_str.encode("utf-8")
    result = base64.b64decode(result)
    image_result = open(image_file, 'wb') # create a writable image and write the decoding result
    image_result.write(result)

def configJsonDir(root):
    json_folder = join(root, 'json_files')
    json_file_config = join(json_folder, 'config')
    json_file_occupancy = join(json_folder, 'occupancy')
    json_file_hash = join(json_folder, 'hash')
    json_file_coord = join(json_folder, 'coord')
    return [json_file_config, json_file_occupancy, json_file_hash, json_file_coord]

def compile(root, export_to_local = True):
    for i in config_op:
        configinfo[i] = globals()[i] 
  
    for i in res.devinfo:
        devinfo[i] = getattr(res, i) 

    # Populate the dictionary with the serialized information
    json_zipinfo["configinfo"] = json.dumps(configinfo)
    json_zipinfo["devinfo"] = json.dumps(devinfo)
    json_occupancy = cfg.res.occupancy
    json_hash = cfg.res.tuple_idx
    json_coord = cfg.output_graphic_coord
    json_coord["processed_img"] = json_serialize_image(cfg.get_output_graphic_path())
    json_zipinfo["processed_floorplan"] = json_serialize_image(cfg.get_output_floor_plan_path())

    # List of dictionaries containing serialised information. We will now write it into a json file to store in database/ local disk
    json_dict_list = [json_zipinfo, json_occupancy, json_hash, json_coord]

    if export_to_local:
        for i in range(len(json_dict_list)):
            path = os.path.join(configJsonDir(cfg._root)[i], cfg.session_name+".json")
            with open(path, 'w') as outfile:
                json.dump(json_dict_list[i], outfile)
    else:  
        cfg.database.exportToDB(cfg.session_name, import_from_script = json_dict_list)

    data = {}
    # Confirms the json file's existence and prints contents on console.
    if export_to_local:
        path = os.path.join(configJsonDir(cfg._root)[0], cfg.session_name+".json")
        with open(path, 'r') as infile:
            data = json.loads(infile.read())
        return str(json.dumps(data["configinfo"], indent=1)) 
    else:
        data = cfg.database.importFromDB(cfg.session_name, export_to_script = [data])
        print("-------")
        
        

    return str(json.dumps(data[0]["configinfo"], indent=1)) 



def decompile(root, import_from_local = True):
    global json_zipinfo, json_occupancy, json_hash, json_coord
    json_zipinfo.clear()
    json_occupancy.clear()
    json_hash.clear()
    json_coord.clear()
    cfg.output_graphic_coord.clear()
    # List of dictionaries containing serialised information. We will now write it into a json file to store in database/ local disk
    json_dict_list_name = ["json_zipinfo", "json_occupancy", "json_hash", "json_coord"]
    data = []
    for i in range(4):
        data.append({})

    if import_from_local:
        for i in range(len(configJsonDir(cfg._root))):
            path = os.path.join(configJsonDir(cfg._root)[i], cfg.session_name+".json")
            with open(path, 'r') as outfile:
                globals()[json_dict_list_name[i]] = json.load(outfile)
    else:
        data = cfg.database.importFromDB(cfg.session_name, export_to_script = data)
        print(data)
        for i in json_dict_list_name:
            globals()[i] = data[json_dict_list_name.index(i)]


    configinfo = json.loads(json_zipinfo.get("configinfo"))
    devinfo = json.loads(json_zipinfo.get("devinfo"))
    processed_img = json_coord.get("processed_img")
    processed_floorplan = json_zipinfo.get("processed_floorplan")
    if not import_from_local:
        cfg.json_deserialize_image(processed_img, cfg.get_output_graphic_path())
        cfg.json_deserialize_image(processed_floorplan, cfg.get_output_floor_plan_path())

    output_graphic_coord = json_coord
    cfg.box_len = json_coord['box_len']
    json_coord.pop('box_len')
    devinfo["tuple_idx"] = json_hash
    devinfo["occupancy"] = json_occupancy

    for i in config_op:
        globals()[i] = configinfo[i]
    
    for i in res.devinfo:
        setattr(res, i, devinfo[i])

    unpackFromJson()
    res.unpackFromJson()

    return json.dumps(json_zipinfo["configinfo"], indent=1)

def unpackFromJson():
    global img
  
    if cfg.image_flag is True: img = imgpro.floorPlan(postimgpath, cfg.myCanvas.canvas, False)
    grid.refresh(delete = False, resize = False)
    cfg.myCanvas.restoreTagOrder()

