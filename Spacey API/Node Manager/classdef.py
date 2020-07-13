################################################# SPACEY Initiation GUI Wizard #############################################
# Author: Looi Kai Wen                                                                                                     #
# Last edited: 28/06/2020                                                                                                  #
# Summary:                                                                                                                 #
#   For use by BLE network administrators to configure their database with invariant information,                          #
#   eg. relative coordinates of the sensor mote, cluster level, etc.                                                       #
#   
############################################################################################################################

from tkinter import * 
import tkinter as tk
from tkinter import filedialog
import config as cfg
from sensor_data import *
from functools import partial
from queue import Queue
from tkinter import font
import imgpro
from platform import system as platf
from imagegen import imagegen
import redisDB as redisDB
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes



class myCanvasObject(object):
    def __init__(self,frame, width, height):
        self.canvas = Canvas(frame, width = width, height = height, highlightcolor = cfg.hlcolor, highlightthickness = 5, bg="SteelBlue1")
        self.line_obj = []
        self.rec_obj = {}
        self.border_obj = []
        self.floorplan_obj = None
        cfg.canvas_w = self.canvas.winfo_reqwidth()
        cfg.canvas_h = self.canvas.winfo_reqheight()
        self.xlen = cfg.canvas_w
        self.ylen = cfg.canvas_h
        #self.canvas.bind('<Configure>' , self.resize)


    def resize(self, event):
        print("resize")
        print(event.width)
        print(event.height)
        cfg.canvas_w = event.width
        cfg.canvas_h = event.height
        wscale = float(event.width)/self.xlen
        hscale = float(event.height)/self.ylen
        self.xlen = event.width
        self.ylen = event.height
        # resize the canvas 
        self.canvas.config(width=self.xlen, height=self.xlen)
        # rescale all the objects tagged with the "all" tag
        self.canvas.scale("all",0,0,wscale,wscale)
        cfg.grid.refresh()
   

    
    def resetCursorLocation(self):
        self.canvas.move(cfg.cursor, cfg.x_list[0] - cfg.x, cfg.y_list[0] - cfg.y)
        cfg.x = cfg.x_list[0]
        cfg.y = cfg.y_list[0]
        
        self.canvas.move(cfg.cursor, cfg.x_list[int(cfg.scale/2)] - cfg.x, cfg.y_list[int(cfg.scale/2)] - cfg.y)
        cfg.x = cfg.x_list[int(cfg.scale/2)]
        cfg.y = cfg.y_list[int(cfg.scale/2)]
        
        if cfg.error is not None: 
            cfg.error.updateText("Cursor location reset.","yellow")

    def deleteImage(self):
        cfg.image_flag = False
        self.canvas.delete(self.floorplan_obj)
        cfg.img_x_bb1 = -1
        cfg.img_y_bb1 = -1


    def clearAllNodes(self):
        for i in self.rec_obj.values():
            self.canvas.delete(i)
        self.rec_obj.clear()

    def deleteNode(self, idx):
        if cfg.prev_node_idx is idx: cfg.prev_node_idx = None
        print("before ", self.rec_obj.keys())
        self.canvas.delete(self.rec_obj[idx])
        del self.rec_obj[idx]
        print("after ", self.rec_obj.keys())
    

    def deleteAllGrids(self):
        for i in self.line_obj:
            self.canvas.delete(i)
        for j in self.border_obj:
            self.canvas.delete(j)

    def restoreTagOrder(self):
        for i in self.line_obj:
            self.canvas.tag_raise(i)
        if cfg.image_flag: self.canvas.tag_raise(self.floorplan_obj)
        for i in self.rec_obj.values():
            self.canvas.tag_raise(i)
        self.canvas.tag_raise(cfg.cursor)
        for i in self.border_obj:
            self.canvas.tag_raise(i)

    def placeNode(self, idx, x, y):
        self.xlen, self.ylen = cfg.box_len, cfg.box_len #size of node
        #cfg.node = canvas.create_rectangle(xpos, ypos,xpos+self.xlen, ypos+self.ylen, fill = "blue")
        self.rec_obj[idx] = self.canvas.create_rectangle(x-self.xlen, y-self.ylen,x+self.xlen, y+self.ylen, fill = "blue")

class CanvasGridFrame(object):
    def __init__(self,canvas, num):
        self.xpos, self.ypos, self.xlen, self.ylen = 0, 0, cfg.canvas_w, cfg.canvas_h
        self.canvas = canvas
        self.deviceID = 0
        cfg.bg = canvas.create_rectangle(self.xpos, self.ypos, self.xpos + self.xlen, self.ypos+self.ylen, fill="SteelBlue1", width = 0)
        self.grid = self.createGrid()

    def createGrid(self):
        print("Create grid")
        num = cfg.scale
        cfg.step = int(cfg.canvas_w / num)
        #   cfg.box_len = cfg.step
        cfg.x_list.clear()
        cfg.y_list.clear()
        for i in range(num+10):
            cfg.x_list.append(round(self.xpos+i*cfg.step))
            cfg.y_list.append(round(self.ypos+i*cfg.step))
            cfg.myCanvas.line_obj.append(self.canvas.create_line(self.xpos+i*cfg.step, self.ypos, self.xpos+i*cfg.step, self.ypos + self.ylen, fill = "sky blue", width = 2))
            cfg.myCanvas.line_obj.append(self.canvas.create_line(self.xpos, self.ypos+i*cfg.step, self.xpos+self.xlen, self.ypos+i*cfg.step, fill = "sky blue", width = 2))

 
        cfg.num_coordinates_max = (cfg.canvas_w/cfg.step-1) * (cfg.canvas_h/cfg.step-1)
        #if cfg.error is not None: cfg.error.updateText("Max coordinates: {_num}".format(_num = cfg.num_coordinates_max), "yellow")
        self.drawBoundary(cfg.step)
        cfg.myCanvas.resetCursorLocation()
        cfg.myCanvas.canvas.tag_raise(cfg.cursor)
    
    def drawBoundary(self, step):
        if int(cfg.canvas_w/step) > len(cfg.x_list): return
        print("step: "+str(step))
        print("canvas_w: "+str(cfg.canvas_w))
        x1 = cfg.x_list[0]
        x2 = cfg.x_list[1]
        _x1 = cfg.x_list[int(cfg.canvas_w/step)-1]
        _x2 = cfg.x_list[int(cfg.canvas_w/step)-2]

        y1 = cfg.y_list[0]
        y2 = cfg.y_list[1]
        _y1 = cfg.y_list[int(cfg.canvas_h/step)-1]
        _y2 = cfg.y_list[int(cfg.canvas_h/step)-2]

        cfg.x_bb1, cfg.y_bb1, cfg.x_bb2, cfg.y_bb2 = x2,y2,_x2, _y2
        if cfg.img_x_bb1 is -1:  cfg.img_x_bb1, cfg.img_y_bb1 = cfg.x_bb1, cfg.y_bb1
        
        
        """
        print("x1: " + str(x1))
        print("x2: " + str(x2))
        print("_x1: " + str(_x1))
        print("_x2: " + str(_x2))
        print("y1: " + str(y1))
        print("y2: " + str(y2))
        print("_y1: " + str(_y1))
        print("_y2: " + str(_y2))
        """
        cfg.myCanvas.border_obj.append(self.canvas.create_rectangle(x1,y1,_x1+step*2,y2, fill = "gray10"))    #north    
        cfg.myCanvas.border_obj.append(self.canvas.create_rectangle(x1,_y2,_x1+step*2,_y1+step*10, fill = "gray10")) #south
        cfg.myCanvas.border_obj.append(self.canvas.create_rectangle(x1,y2,x2,_y2, fill = "gray10")) #west
        cfg.myCanvas.border_obj.append(self.canvas.create_rectangle(_x2,y2,_x1+step*2,_y2, fill = "gray10")) #east


    def refresh(self, delete = True, resize = True):
        cfg.load_flag = not resize
        if delete: cfg.res.deleteAllNodes()
        cfg.myCanvas.deleteAllGrids()
        self.grid = self.createGrid()
        if resize and cfg.image_flag: cfg.img.resize()
        
        cfg.myCanvas.canvas.tag_raise(cfg.cursor)
        

class CursorNode(object):
    def __init__(self, canvas):
        self.canvas = canvas
        self.xpos, self.ypos = 0,0
        self.xlen, self.ylen = 10, 10 #size of node
        cfg.x, cfg.y = int(self.xpos + self.xlen/2), int(self.ypos + self.ylen/2)
        cfg.cursor = canvas.create_rectangle(self.xpos, self.ypos,self.xpos+self.xlen, self.ypos+self.ylen, fill = "red")
       
        canvas.tag_bind(cfg.cursor, '<B1-Motion>', self.move)
        canvas.bind('<ButtonRelease-1>', self.release)
        canvas.bind('<Button-3>', self.deleteNode)
        

        canvas.bind('<Up>', lambda event: self.move_unit(event, 'W') )
        canvas.bind('<Left>', lambda event: self.move_unit(event, 'A') )
        canvas.bind('<Down>', lambda event: self.move_unit(event, 'S') )
        canvas.bind('<Right>', lambda event: self.move_unit(event, 'D') )
        canvas.bind('<ButtonRelease-1>', self.release)
        canvas.bind('<KeyRelease-Up>', self.release_unit)
        canvas.bind('<KeyRelease-Down>', self.release_unit)
        canvas.bind('<KeyRelease-Left>', self.release_unit)
        canvas.bind('<KeyRelease-Right>', self.release_unit)
        canvas.bind('<Return>', self.enter)
        canvas.bind('<Button-3>', self.deleteNode)
        canvas.bind('<Control-x>', self.deleteNode)


        self.restaurant = cfg.res
        self.move_flag = False
        self.callBack = []
    
    def deleteNode(self, event):
        if (cfg.x, cfg.y) in self.restaurant.dict_sensor_motes:
            print("deleted")            
            self.restaurant.deleteNode(cfg.x, cfg.y)
            cfg.error.updateText("Node deleted at x:{x} and y:{y}".format(x = cfg.x, y = cfg.y), "deep pink")
            self.nodeDetectCallback()
            return
        else:
            print("Invalid")
            return
    

    
    def setCallback(self, cb):
        self.callBack.append(cb)
        
    def deposit(self):
        print("enter registered")
        if cfg.deposit_flag is True:
            self.nodeDetectCallback()
            cfg.deposit_flag = False
        else:
            return
    

 
    def estimate(self,x,_list):

        mid = round(len(_list)/2)
        if len(_list) is 1:
            return _list[0]
        elif len(_list) is 2:
            if abs(_list[0] - x) > abs(_list[1] - x):
                return _list[1]
            else:
                return _list[0] 
        else:
            if x > _list[mid]:
                x = x+1
                return self.estimate(x,_list[mid:])
            elif x < _list[mid]:
                x = x-1
                return self.estimate(x,_list[:mid])
            else:
                return x

    def move(self, event):
        if self.move_flag:
            new_xpos, new_ypos = event.x, event.y
            self.canvas.move(cfg.cursor, new_xpos-self.mouse_xpos ,new_ypos-self.mouse_ypos)
            cfg.x += new_xpos-self.mouse_xpos
            cfg.y += new_ypos-self.mouse_ypos
            self.mouse_xpos = new_xpos
            self.mouse_ypos = new_ypos
        else:
            self.move_flag = True
            self.canvas.tag_raise(cfg.cursor)
            self.mouse_xpos = event.x
            self.mouse_ypos = event.y

    def move_unit(self, event, dir):
        self.move_flag = True
        print("lol")
        if dir is "W":
            self.canvas.move(cfg.cursor, 0 , -cfg.step)
            cfg.y -= cfg.step
        elif dir is "A":
            self.canvas.move(cfg.cursor, -cfg.step, 0)
            cfg.x -= cfg.step
        elif dir is "S":
            self.canvas.move(cfg.cursor, 0 , cfg.step)
            cfg.y += cfg.step
        elif dir is "D":
            self.canvas.move(cfg.cursor, cfg.step, 0)
            cfg.x += cfg.step
        self.canvas.tag_raise(cfg.cursor)

    def release(self, event):
        new_xpos, new_ypos = self.estimate(event.x,cfg.x_list), self.estimate(event.y,cfg.y_list)
        self.canvas.move(cfg.cursor, new_xpos-cfg.x ,new_ypos-cfg.y)
        self.mouse_xpos = new_xpos
        self.mouse_ypos = new_ypos
        self.move_flag = False
        cfg.x = new_xpos
        cfg.y = new_ypos
        cfg.initflag = True
        self.nodeDetectCallback()
        self.canvas.tag_raise(cfg.cursor)
        

    def release_unit(self, event):
        self.move_flag = False
        self.nodeDetectCallback()
        self.canvas.tag_raise(cfg.cursor)
    
    def enter(self, event):
        cfg.initflag = True
        self.nodeDetectCallback()

        

    def nodeDetectCallback(self):

        if (cfg.x, cfg.y) in self.restaurant.dict_sensor_motes:
            text = self.restaurant.printMoteAt(cfg.x, cfg.y)
            cfg.node_idx = self.restaurant.dict_sensor_motes.get((cfg.x, cfg.y)).idx
            cfg.myCanvas.canvas.itemconfig(cfg.myCanvas.rec_obj[cfg.node_idx], fill = "orange")
            if cfg.prev_node_idx is not None and cfg.prev_node_idx is not cfg.node_idx: cfg.myCanvas.canvas.itemconfig(cfg.myCanvas.rec_obj[cfg.prev_node_idx], fill = "blue")
            self.callBack[1]("lawn green")
            self.callBack[0](text) # Print text on status label
            cfg.prev_node_idx = cfg.node_idx

        else:   
            if cfg.prev_node_idx is not None: cfg.myCanvas.canvas.itemconfig(cfg.myCanvas.rec_obj[cfg.prev_node_idx], fill = "blue")
            cfg.deposit_flag = False
            self.callBack[0]("No node information") # Print text on status label
            self.callBack[1]("MediumPurple1")
            

class menu_upload(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.labelFrame = LabelFrame(self.frame, text = "Floor Plan Manager", height = 150, width = 550, bg = "gray55")
        self.labelFrame.pack(fill = X, side = TOP, pady = cfg.pady, padx = cfg.padx)
        self.obj = Button(self.labelFrame, text = "Import Floor plan", command = self.fileupload)
        self.obj.pack(ipadx = 10, ipady = 10, fill = X, side = TOP)
        self.obj = Button(self.labelFrame, text = "Clear Floor plan", command = self.floorplanclear)
        self.obj.pack(ipadx = 10, ipady = 10, fill = X, side = TOP)

    def fileupload(self):
        cfg.myCanvas.deleteImage()
        cfg.res.deleteAllNodes()
        filename = filedialog.askopenfilename(initialdir = cfg.floorplan_folder_input, title = "Select File", filetypes = (("all files","*.*"),("png files","*.png"), ("jpeg files","*.jpg")))

        # Create Image generator
        cfg.img = imgpro.floorPlan(filename, cfg.myCanvas.canvas)
    
    def floorplanclear(self):
        cfg.myCanvas.deleteImage()
        cfg.res.deleteAllNodes()
        

class map_refresh(object):
    def __init__(self, frame,factor, width, height):
        self.frame = frame
        #self.frame = Frame(frame)
        #self.frame.grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(self.frame, text = "Grid scale... ", height = 150, width = 550, bg = "gray55")
        self.labelFrame.pack(fill = X, side = TOP, pady = cfg.pady, padx = cfg.padx)
        self.but1 = Button(self.labelFrame, text = "Scale up", command = self.updateUp)
        self.but1.pack(ipadx = 10, ipady = 10, fill = X)
        self.but2 = Button(self.labelFrame, text = "Scale down", command = self.updateDown)
        self.but2.pack(ipadx = 10, ipady = 10, fill = X)
        self.factor = factor

    def updateUp(self):
        print("scale: {}".format(cfg.scale))
        
        if cfg.scale >= 120:
            cfg.error.updateText("[Grid] Cannot scale up any further", "orange")
            return
    
        cfg.scale += self.factor
        print("lol: " + str(cfg.scale))
        refresh = cfg.grid.refresh()
        

    def updateDown(self):
        
        if (cfg.scale - self.factor) <= 0 or int(cfg.canvas_w/(cfg.scale - self.factor)) > cfg.max_step:
            cfg.error.updateText("[Grid] Cannot scale down any further", "orange")
            return

        cfg.scale -= self.factor
        refresh = cfg.grid.refresh()
        

      
        

class menu_devinfo(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.rowFrame = []
        self.entryLabel = []
        self.radio = []
        self.getFlag = False
        self.entryList = []
        self.callBack = []
        self.hold = []
        self.text = []
        self.numEntries = 3
        self.keyEntry = None
        self.needCorrect = [False, False, False]
        self.error_text = []

        # Initialize variable texts
        for i in range(3):
            self.hold.append(IntVar())
            self.text.append(StringVar())
     

        self.labelFrame = LabelFrame(self.frame, text = "Set Sensor ID", height = 500, width = 550, bg = "gray55")
        self.labelFrame.pack(fill = X, side = TOP, pady = cfg.pady, padx = cfg.padx)

        # Autosaved entries
        self.nodeEntry = [-1, -1, -1]
        self.prevEntry = [-1, -1, -1]

        # Set up rows of entry
        self.titleName = ["Level ID", "Cluster ID", "Sensor ID"]
        for i in range(self.numEntries):
            self.setEntryRow(i)

        # Key bindings
        for j in range(len(self.entryList)): #bind all entries    
            self.entryList[j].bind('<Return>', lambda event : self.enter(event, j))
    
        
    def setEntryRow(self,i):
        self.rowFrame.append(Frame(self.labelFrame, bg = "gray55"))
        self.rowFrame[i].pack(side = TOP, fill = X, padx = 10, pady = 5)
        self.entryLabel.append(Label(self.rowFrame[i], text = self.titleName[i], bd = 5, width = 8))
        self.entryLabel[i].pack(side = LEFT)
        self.entryList.append(Entry(self.rowFrame[i], bd = 5, textvariable = self.text[i], highlightcolor = cfg.hlcolor, highlightthickness = 5, highlightbackground = "gray55", width = 6))
        self.entryList[i].pack(side = LEFT)
        self.radio.append(Checkbutton(self.rowFrame[i], text = "Hold", variable = self.hold[i], command = partial(self.restorePreviousEntries, i), bg = "gray55"))
        self.radio[i].pack(side = LEFT)



    def restorePreviousEntries(self, i):
        
        if self.hold[i].get():  # If the user selects radio button 
            if self.entryList[i].get() is "":   # If the user wants to recall and hold previous entry
                self.text[i].set(self.prevEntry[i])
            else:   # If the user typed a value to hold to 
                self.text[i].set(self.entryList[i].get())
            self.entryList[i].config(state = DISABLED, disabledbackground= "sky blue")
        else:
            self.text[i].set("")
            self.entryList[i].config(state = NORMAL)

    def setCallback(self, cb):
        self.callBack.append(cb)

    def highlightDeviceInfo(self, _bg):
        print("highlight: " + str(_bg))
        for i in self.entryList:
            i.config(bg = _bg)
        if self.keyEntry is None: self.keyEntry = self.entryList[0]

        # Grant focus to the entry only if it comes from a <Return> or a <Mouse Release>
        if cfg.initflag: 
            self.keyEntry.focus()
            self.keyEntry.config(bg = "yellow")
            cfg.initflag = False
   
    def enter(self, event, id):
        
        emptyCount = []
        # Performs a check throughout the inputs of all 3 entries
        for i in range(len(self.entryList)):
            if not len(self.entryList[i].get()): 
                self.error_text.insert(i, ("<Entry [{num}]>: Empty".format(num = self.titleName[i]), "yellow"))
                self.entryList[i].config(bg = "red")
                self.needCorrect[i] = True
            elif (self.entryList[i].get()).isnumeric():
                if int(self.entryList[i].get()) >=0:
                    self.nodeEntry[i] = int(self.entryList[i].get())
                    self.prevEntry[i] = self.nodeEntry[i]
                    self.entryList[i].config(bg = "lawn green")
                    self.needCorrect[i] = False
                    self.error_text.insert(i,None)
                else:
                    self.error_text.insert(i,("<Entry [{num}]>: Number must be positive".format(num = self.titleName[i]), "orange"))
                    self.entryList[i].config(bg = "red")
                    self.needCorrect[i] = True

            else:
                self.error_text.insert(i,("<Entry [{num}]>: Entry must be a positive number".format(num = self.titleName[i]), "orange"))
                self.entryList[i].config(bg = "red")
                self.needCorrect[i] = True
        
            

        numErrors = 0
        for i in self.needCorrect:
            numErrors += i
        print(self.needCorrect)
        if numErrors: 
            print(self.error_text)
            self.keyEntry = self.entryList[self.needCorrect.index(True)]
            cfg.error.updateText(self.error_text[self.needCorrect.index(True)][0], self.error_text[self.needCorrect.index(True)][1])
            self.keyEntry.focus_set()
            return # If there are invalid entries, cannot proceed to store data.

        self.error_text.clear()
        cfg.error.updateText("No error", "pale green") 
        flag = True
        # If not voted by radio to hold value, clear it
        for i in range(len(self.entryList)):
            if not self.hold[i].get():
                self.entryList[i].delete(0, END)
                if flag: 
                    self.keyEntry = self.entryList[i]
                    flag = False

        x = self.nodeEntry
        
        # Deposit sensor node on map
        cfg.deposit_flag = True
        self.callBack[0]()

        # Save sensor detail locally in previously declared class
        cfg.res.registerNode(cfg.x, cfg.y, x[0], x[1], x[2], cfg.node)
        
        cfg.res.printMoteAt(cfg.x, cfg.y)

        # Reset the intermediate entry
        self.nodeEntry = [-1,-1,-1]

        self.callBack[1]()  # Callback to deposit sensor node
        self.callBack[2](1) # Callback to give up focus back to canvas

class menu_status(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.labelFrame = LabelFrame(self.frame, text = "Status bar", bg = "gray55", height = 170+20, width = 550)
        self.labelFrame.pack(fill = X, padx = cfg.padx, pady = cfg.pady, side = TOP)
        self.labelFrame.pack_propagate(0)
        self.obj = Label(self.labelFrame,text = "", bd = 100, height = 300, width = 550)
        self.obj.pack(padx = 10, pady = 10)
    def updateText(self, _text):
        self.obj.configure(text = _text)
        self.obj.update()

class menu_help(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.labelFrame = LabelFrame(self.frame, text = "Help", bg = "gray55", height = 117-51, width = 550)
        self.labelFrame.pack(fill = X, padx = cfg.padx, pady = cfg.pady, side = TOP)
        self.labelFrame.pack_propagate(0)
        self.obj = Button(self.labelFrame,text = "Press me for help!", command = self.newWindow, bg = "sky blue")
        self.obj.pack(ipadx = 10, ipady = 10, fill = X)
    
    def newWindow(self):
        self.displayHelpMenu(cfg.root)

    def displayHelpMenu(self, root):
        helpMenu = Toplevel(root)
        helpMenu.geometry('500x'+ str(cfg.canvas_h))
        helpMenu.title("Help Menu")
            # Icon of the window
        if platf() == 'Linux':
            img = PhotoImage(file= cfg.gif_path)
            helpMenu.tk.call('wm', 'iconphoto', helpMenu._w, img)
        elif platf() == 'Windows':
            helpMenu.iconbitmap('/home/kaiwen98/Desktop/spacey/Spacey API/images/assets/spacey_icon.ico')
        #x,y = self.findCentralize(helpMenu)
        #helpMenu.geometry("+{}+{}".format(x, y))
        frame = Frame(helpMenu, bg = "gray10")
        frame.pack(padx = 15, pady = 15, fill = tk.BOTH, expand = 1)
        help = self.helpMessage(frame)
        helpMenu.configure(bg = "sky blue")
        helpMenu.bind('<Escape>', lambda event: self.quitTop(event, helpMenu))
    
  


    def helpMessage(self, frame):
        cfg.help_font = font.Font(family="Arial", size=8, weight = "bold")
        text = Text(frame,  bg = "white", font = cfg.help_font, bd = 10, wrap = WORD)
        yscroll = Scrollbar(frame, orient = "vertical", command = text.yview)
        yscroll.pack(padx = 2, pady = 2, side = LEFT, fill = Y)
        text.pack(pady = 2, ipadx = 2, ipady = 2, side = LEFT, fill = tk.BOTH, expand = 1)
        text.configure(yscrollcommand = yscroll.set)


        text.tag_config("h1", foreground = "deepskyblue2", )
        text.tag_config("h2", foreground = "black")
        text.tag_config("h3a", foreground = "DarkOrange1", justify = LEFT)
        text.tag_config("h3b", foreground = "blue4", justify = LEFT)

        ##color##
        text.tag_config("h_red", foreground = "red")
        text.tag_config("h_green", foreground = "green")
        text.tag_config("h_purple", foreground = "purple")
        text.tag_config("h_yellow", foreground = "darkorange")
        text.tag_config("h_blue", foreground = "blue")

        text.insert(END, "Info:", "h1")
        text.insert(END, "\nThis Node Manager allows network administrators to synchronise the location of the sensor motes with the graphic to be generated, as well as the communication of location-specific information between the sensor motes and the database."+ 
                        "\n\nThe interface controls are easy to use and intuitive, allowing the user to quickly form a composition of the sensor mote network without much delay. You can then use Spacey Image Processor to generate the graphic! \n\nThe Node Manager comes embedded with an image processing functionality, which edits your floorplan image down to size and color requirement to fit on the canvas.", "h2")

        text.insert(END, "\n\nControls:", "h1")
        text.insert(END, "\n\t>> Quit from Node Manager\t\t\t\t", "h3a")
        text.insert(END, "<ESCAPE>", "h3b")

        text.insert(END, "\n\t>> Toggle Control to Grid\t\t\t\t", "h3a")
        text.insert(END, "<CTRL-Z>", "h3b")

        text.insert(END, "\n\t>> Place Node\t\t\t\t", "h3a")
        text.insert(END, "<MOUSE-L>\t", "h3b")
        text.insert(END, "<ENTER>", "h3b")

        text.insert(END, "\n\t>> Delete Node\t\t\t\t", "h3a")
        text.insert(END, "<MOUSE-R>\t", "h3b")
        text.insert(END, "<CTRL-X>", "h3b")

        text.insert(END, "\n\t>> Move Node\t\t\t\t", "h3a")
        text.insert(END, "<MOUSE-DRAG>\t", "h3b")
        text.insert(END, "<ARROW KEYS>", "h3b")

        text.insert(END, "\n\nFeatures:", "h1")
        text.insert(END, "\nCursors and Nodes", "h3a")
        text.insert(END, "\nThe Cursor is red in color.", "h_red")
        text.insert(END, " The Nodes are blue in color.", "h_blue")
        text.insert(END, " You may use the cursor to navigate the grid. You can navigate to an empty grid point to insert a Node, or navigate to an existing node to delete it off. Refer to the previous section above on the relevant controls.", "h2")

        text.insert(END, "\nClear Floor plan", "h3a")
        text.insert(END, "\nUnder menu 1. Click to clear the canvas of the contents.", "h2")

        text.insert(END, "\nFloor Plan upload", "h3a")
        text.insert(END, "\nUnder menu 1. You may upload your floor plan image using the upload button, preferably in PNG format.", "h2")

        
        text.insert(END, "\nSet Sensor ID", "h3a")
        text.insert(END, "\nUnder menu 1. You may use the entry boxes to enter the sensor information, after you place the cursor on the grid and place a node. The entry boxes only accept integer inputs, and will not proceed upon an invalid input. The color of the entry boxes denote its status to advise you on your next course of action:","h2")
        text.insert(END, "\n\n\tRED:\t\t\t" + "Needs correction to text field", "h_red")
        text.insert(END, "\n\tGREEN:\t\t\t" + "Valid Entry, node already placed here", "h_green")
        text.insert(END, "\n\tPURPLE:\t\t\t" + "No Entry yet, node can be placed here", "h_purple")
        text.insert(END, "\n\tYELLOW:\t\t\t" + "Awaiting Entry, fill in text field", "h_yellow")
        text.insert(END, "\n\nYou can use the \"hold\" radio button to set your own value/freeze previous value, in case you are placing nodes with the same cluster id/ level.","h2")
        text.insert(END, "\n\nStatus Bar", "h3a")
        text.insert(END, "\nUnder menu 1. You may use it to track the node information on an existing node.", "h2")

        text.insert(END, "\nDebugger", "h3a")
        text.insert(END, "\nUnder menu 1. Alerts you of any status updates/ errors encountered", "h2")

        text.insert(END, "\nDimension adjustments", "h3a")
        text.insert(END, "\nUnder menu 2. You may adjust the node size, grid partition size and floor plan size via the top menu 2 controls. You can also move the floorplan linearly. This is to allow you to find the best graphical configuration where the grid points best coincide with the seats on your floor plan to place the sensor nodes. The configuration you view here will be reflected on the output graphic.", "h2")
        
        text.insert(END, "\nJSON Viewer", "h3a")
        text.insert(END, "\nUnder menu 2. You can save your work into a JSON file by clicking the \"Upload JSON\" button. Conversely, you can load a previous save file by clicking the \"Download JSON\" button. You can use the viewer below to check the JSON file contents for debugging purposes.", "h2")

        
        
        text.configure(state = "disabled")


    def quitTop(self, event, top):
        top.destroy()
        top.update()








class menu_debug(object):
    def __init__(self, frame, width, height):
        #cfg.error_font = font.Font(family = "Times", font = "3", weight =  "BOLD")
        cfg.error_font = font.Font(family="Courier New", size=10, weight = "bold")
        self.frame = frame
        self.labelFrame = LabelFrame(self.frame, text = "Debugger", bg = "gray55", height = 300, width = 550)
        self.labelFrame.pack(fill = X, padx = cfg.padx, pady = cfg.pady, side = TOP)
        self.labelFrame.pack_propagate(0)
        self.obj = Listbox(self.labelFrame,height = 300, width = 550, bg = "gray10", font = cfg.error_font)
        self.yscroll = Scrollbar(self.labelFrame, orient = "vertical", command = self.obj.yview)
        self.xscroll = Scrollbar(self.labelFrame, orient = "horizontal", command = self.obj.xview)

        self.yscroll.pack(padx = 10, pady = 10, side = LEFT, fill = Y)
        self.xscroll.pack(padx = 10, pady = 10, side = BOTTOM, fill = X)
        self.obj.pack(ipadx = 30, ipady = 30, side = LEFT, fill = Y)
        

        self.obj.configure(xscrollcommand= self.xscroll.set, yscrollcommand = self.yscroll.set)
        self.obj.insert(END, "Initialized")
        self.obj.itemconfig(0, foreground="sky blue")

    def updateText(self, _text, _bg):
        cfg.updateTextDone = False
        self.obj.insert(END, _text)
        self.obj.itemconfig(END, foreground = _bg)
        self.obj.see("end")
        cfg.updateTextDone = False
        #self.obj.update()


class img_xyshift(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        #self.frame = Frame(frame)
        #self.frame.grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(self.frame, text = "Floorplan shifts...", height = 140, width = 550, bg = "gray55")
        self.labelFrame.pack(fill = X, side = TOP, pady = cfg.pady, padx = cfg.padx)
        self.parentFrame1 = Frame(self.labelFrame, height = 140)
        self.parentFrame2 = Frame(self.labelFrame, height = 140)
        self.parentFrame1.pack(side = LEFT, padx = 10)
        self.parentFrame2.pack(side = LEFT, padx = 10)

        self.framex = Frame(self.parentFrame1, height = 70)
        self.framey = Frame(self.parentFrame1, height = 70)
        self.framex.pack(side = TOP, fill = X)
        self.framey.pack(side = TOP, fill = X)

        self.but1 = Button(self.framex, text = "Left", command = self.left, width = 3)
        self.but1.pack(ipadx = 10, ipady = 10, side = LEFT)
        self.but2 = Button(self.framex, text = "Right", command = self.right, width = 3)
        self.but2.pack(ipadx = 10, ipady = 10, side = LEFT)

        self.but1 = Button(self.framey, text = "Up", command = self.up, width = 3)
        self.but1.pack(ipadx = 10, ipady = 10, side = LEFT)
        self.but2 = Button(self.framey, text = "Down", command = self.down, width = 3)
        self.but2.pack(ipadx = 10, ipady = 10, side = LEFT)

        self.framex2 = Frame(self.parentFrame2, height = 70)
        self.framey2 = Frame(self.parentFrame2, height = 70)
        self.framex2.pack(side = TOP, fill = X)
        self.framey2.pack(side = TOP, fill = X)  

        self.but1 = Button(self.framex2, text = "Scale +", command = self.s_up, width = 3)
        self.but1.pack(ipadx = 10, ipady = 10, fill = X, side = TOP)
        self.but2 = Button(self.framey2, text = "Scale -", command = self.s_down, width = 3)
        self.but2.pack(ipadx = 10, ipady = 10, fill = X, side = TOP)

        self.factor = factor

    def left(self):
        cfg.img_x_bb1 -= self.factor 
        cfg.myCanvas.canvas.move(cfg.myCanvas.floorplan_obj, -self.factor, 0)
    def right(self):
        cfg.img_x_bb1 += self.factor 
        cfg.myCanvas.canvas.move(cfg.myCanvas.floorplan_obj, self.factor, 0)
    
    def up(self):
        cfg.img_y_bb1 -= self.factor 
        cfg.myCanvas.canvas.move(cfg.myCanvas.floorplan_obj, 0, -self.factor)
    def down(self):
        cfg.img_y_bb1 += self.factor 
        cfg.myCanvas.canvas.move(cfg.myCanvas.floorplan_obj, 0, self.factor)
    
    def s_up(self):
        if cfg.img_padding == 0: 
            cfg.error.updateText("<Floor Plan> Cannot scale down further", "orange")
            return
        cfg.img_padding -= self.factor
        cfg.img.resize()
    def s_down(self):
        cfg.img_padding += self.factor
        cfg.img.resize()

class img_scaleshift(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        #self.frame = Frame(frame)
        #self.frame.grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(self.frame, text = "Floorplan scales...", height = 150, width = 550, bg = "gray55")
        self.labelFrame.pack(fill = X, side = TOP, pady = cfg.pady, padx = cfg.padx)
        self.but1 = Button(self.labelFrame, text = "Size +", command = self.up, width = 4)
        self.but1.pack(ipadx = 10, ipady = 10, side = LEFT)
        self.but2 = Button(self.labelFrame, text = "Size -", command = self.down, width = 4)
        self.but2.pack(ipadx = 10, ipady = 10, side = LEFT)
        self.factor = factor

    def up(self):
        if cfg.img_padding == 0: 
            cfg.error.updateText("<Floor Plan> Cannot scale down further", "orange")
            return
        cfg.padding -= self.factor
        cfg.img.resize()
    def down(self):
        cfg.img_padding += self.factor
        cfg.img.resize()
        

class node_scaleshift(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        #self.frame = Frame(frame)
        #self.frame.grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(self.frame, text = "Node scales...", height = 150, width = 550, bg = "gray55")
        self.labelFrame.pack(fill = X, side = TOP, pady = cfg.pady, padx = cfg.padx)
        self.but1 = Button(self.labelFrame, text = "Up", command = self.up, width = 4)
        self.but1.pack(ipadx = 10, ipady = 10, side = LEFT, padx = 25)
        self.but2 = Button(self.labelFrame, text = "Down", command = self.down, width = 4)
        self.but2.pack(ipadx = 10, ipady = 10, side = LEFT, padx = 12)
        self.factor = factor

    def up(self):
        cfg.box_len += self.factor
        cfg.error.updateText("Node length: {n}".format(n = cfg.box_len), "yellow")
        cfg.res.changeNodeSize()
    def down(self):
        cfg.box_len -= self.factor
        cfg.res.changeNodeSize()

class json_viewer(object):
    def __init__(self, frame, width, height):
        #cfg.error_font = font.Font(family = "Times", font = "3", weight =  "BOLD")
        cfg.json_font = font.Font(family="Courier New", size=8, weight = "bold")
        self.frame = frame
        self.labelFrame = LabelFrame(self.frame, text = "JSON Viewer", bg = "gray55", height = 550, width = 550)
        self.labelFrame.pack(fill = "x", padx = cfg.padx, pady = cfg.pady, side = TOP)
        self.labelFrame.pack_propagate(0)
        self.frame2 = Frame(self.labelFrame, bg = "gray55", height = 40)
        self.frame2.pack(fill = X, side = TOP)
        self.frame1 = Frame(self.labelFrame, bg = "gray55")
        self.frame1.pack(fill = X, side = TOP)

        self.butt1 = Button(self.frame2, text = "Import JSON", command = self.download, width = 550)
        self.butt1.pack()
        self.butt = Button(self.frame2, text = "Export JSON", command = self.upload, width = 550)
        self.butt.pack()
        self.dbframe = LabelFrame(self.frame2, text = "RedisDB Operations: ", bg = "gray55")
        self.dbframe.pack(expand = True, fill = X, ipadx = 2, ipady = 2)
        
        self.refreshbutt = Button(self.dbframe, text = "Connect to RedisDB", command = self.refreshDB, width = 550, bg = "IndianRed2", activebackground= "salmon")
        self.refreshbutt.pack()
        self.dbselect = tk.StringVar(cfg.root)
        self.dbselect.set(cfg.db_options[0]) # default value
        self.dbselect.trace("w", self.callback)
        self.optionmenu = OptionMenu(self.dbframe, self.dbselect, *cfg.db_options)
        self.optionmenu.pack(expand = 1, fill = X)

        
        self.butt2 = Button(self.dbframe, text = "Import from DB", command = self.downloadDB, width = 550, bg = "RosyBrown1")
        self.butt2.pack_forget()
        self.butt3 = Button(self.dbframe, text = "Export to DB", command = partial(self.displayUploadMenu, cfg.root), width = 550, bg = "RosyBrown1")
        self.butt3.pack_forget()

        self.buttdel1 = Button(self.dbframe, text = "Delete Selected Restaurant", command = self.DBclearDB, width = 550, bg = "RosyBrown1")
        self.buttdel1.pack_forget()
        self.buttdel2 = Button(self.dbframe, text = "Delete Account", command = self.DBclearUser, width = 550, bg = "RosyBrown1")
        self.buttdel2.pack_forget()
    
        #self.butt.pack(ipadx = 30, ipady = 30, fill = X)
        self.obj = Text(self.frame1,  width = 550, height = 190, bg = "gray10", font = cfg.json_font)
        self.yscroll = Scrollbar(self.frame1, orient = "vertical", command = self.obj.yview)
        self.yscroll.pack(padx = 10, pady = 10, side = LEFT, fill = Y)
        self.obj.pack(pady = 10, ipadx = 30, ipady = 30, side = LEFT, fill = Y)
        


        self.obj.configure(yscrollcommand = self.yscroll.set)
        self.obj.tag_config("b", foreground = "sky blue")
        self.obj.tag_config("p", foreground = "deep pink")
        self.obj.tag_config("y", foreground = "yellow")
        self.obj.insert(END, "Wait for JSON to be \nuploaded...\n\n", "b")

    def refreshDB(self):
        cfg.error.updateText("[DB] Connecting...", "yellow")
        err = cfg.database.timeout()
        if err == 0: cfg.error.updateText("[DB] Time out... cannot connect to database", "red")
        else:
            cfg.error.updateText("[DB] Connected to database", "pale green")
            cfg.db_options.clear()
            #cfg.db_options += cfg.database.get_registered_restaurants()
            self.displayLoginMenu(cfg.root)
    
    def DBclearUser(self):
        cfg.database.clearUser(cfg.userid)
        cfg.error.updateText("Acc Del: {}. See you!".format(cfg.userid), "yellow")
        cfg.userid = ""
        self.refresh()

    def DBclearDB(self):
        res = self.dbselect.get()
        name = cfg.userid + "_" + res
        cfg.database.clearDB(name)
        cfg.error.updateText("Restaurant deleted: {}".format(name), "yellow")
        self.refresh()

    def refresh(self):
        # Reset var and delete all old options
        self.dbselect.set('')
        self.optionmenu['menu'].delete(0, 'end')

        # Insert list of new options (tk._setit hooks them up to var)
        if cfg.userid == "": 
            cfg.db_options.clear()
            cfg.db_options = ["No Database Selected"] 
            self.dbselect.set(cfg.db_options[0])
            return

        new_choices = ["Enter New Restaurant"] + cfg.database.get_registered_restaurants()
        for choice in new_choices:
            self.optionmenu['menu'].add_command(label=choice, command = tk._setit(self.dbselect, choice))
        self.dbselect.set(new_choices[0])
        
    def callback(self, *args):
        if self.dbselect.get() == "No Database Selected":
            self.butt2.pack_forget()
            self.butt3.pack_forget()
            self.buttdel1.pack_forget()
            self.buttdel2.pack_forget()
            self.session_name_set = False
        elif self.dbselect.get() == "Enter New Restaurant":
            self.butt2.pack_forget()
            self.butt3.pack()
            self.buttdel1.pack_forget()
            self.buttdel2.pack()
            self.session_name_set = False
        else:
            self.butt2.pack()
            self.butt3.pack()
            self.buttdel1.pack()
            self.buttdel2.pack()
            cfg.session_name = self.dbselect.get()
            self.session_name_set = True
    def updateText(self, _text, _bg):
        
        self.obj.insert(END, _text, _bg)
        self.obj.see("end")

    def downloadDB(self): 
        if self.dbselect.get() in ["No Database Selected", "No restaurants stored"]: return
        cfg.export_to_local = False
        cfg.session_name = self.dbselect.get()
        if cfg.res.size: cfg.res.deleteAllNodes()
        if cfg.image_flag: cfg.myCanvas.deleteImage()
        str1 = cfg.decompile(cfg.json_folder, import_from_local = False)
        self.updateText(str1+"\n", "p")
        self.updateText(">>>"+"+"*15+"\n", "b")

    def upload(self):
        if cfg.res.size == 0:
            cfg.error.updateText("[ERR] Need at least 1 node", "red")
            return
        cfg.import_from_local = True
        cfg.json_path = filedialog.asksaveasfilename(initialdir = cfg.json_folder_config, title = "Select File", filetypes = [("Json File", "*.json")])
        cfg.session_name = cfg.getbasename(cfg.json_path)
        
        if cfg.img is not None: cfg.img.save()
        #cfg.json_path = cfg.json_path + ".json"
        imagegen() # Generates template
        str1 = cfg.compile(cfg.json_folder)
        self.updateText(str1+"\n", "p")
        self.updateText(">>>"+"-"*15+"\n", "b")
        cfg.error.updateText("JSON Updated successfully", "pale green")
        self.refresh()
    
    def displayUploadMenu(self, root):
        if cfg.res.size == 0:
            cfg.error.updateText("[ERR] Need at least 1 node", "red")
            return
        if self.dbselect.get() not in ["No Database Selected", "No restaurants stored", "Enter New Restaurant"]: 
            self.uploadDB()
            return
        self.helpMenu = Toplevel(root)
        self.helpMenu.geometry('300x55')
        self.helpMenu.configure(bg = "tomato2")
        self.helpMenu.title("Enter Restaurant Name!")
            # Icon of the window
        if platf() == 'Linux':
            img = PhotoImage(file= cfg.gif_path)
            self.helpMenu.tk.call('wm', 'iconphoto', self.helpMenu._w, img)
        elif platf() == 'Windows':
            self.helpMenu.iconbitmap(cfg.icon_path)
        frame = Frame(self.helpMenu, bg = "gray10")
        frame.pack(expand = 1)
        self.text_input = StringVar()
        text = Entry(frame, textvariable = self.text_input)
        text.pack(expand = 1, padx = 10, pady = 10)
        text.bind('<Return>', self.uploadDB)

    def displayLoginMenu(self, root):
        self.helpMenu = Toplevel(root)
        self.helpMenu.geometry('300x150')
        self.helpMenu.configure(bg = "tomato2")
        self.helpMenu.title("Enter Login Details")
        
            # Icon of the window
        if platf() == 'Linux':
            img = PhotoImage(file= cfg.gif_path)
            self.helpMenu.tk.call('wm', 'iconphoto', self.helpMenu._w, img)
        elif platf() == 'Windows':
            self.helpMenu.iconbitmap(cfg.icon_path)
        frame = Frame(self.helpMenu, bg = "gray10")
        frame.pack(expand = 1, padx = 15, pady = 10, fill = X)
    
        self.text = [None, None]

        self.text_input_uid = StringVar()
        self.text_input_pw = StringVar()
        
        frame_but = Frame(frame, bg = "gray10")
        frame_but.pack(side = TOP)
        frame_but1 = Frame(frame, bg = "gray10")
        frame_but1.pack(side = TOP)

        text_label = Label(frame_but, text = "User ID", width = 10, foreground = "white", bg = "gray10")
        text_label.config(font=("Courier", 8))
        text_label.pack(side = LEFT)
        self.text[0] = Entry(frame_but, textvariable = self.text_input_uid, highlightcolor = "white")
        self.text[0].pack(expand = 1, padx = 10, pady = 10, side = LEFT)

        text_label = Label(frame_but1, text = "Password", width = 10, foreground = "white", bg = "gray10")
        text_label.pack(side = LEFT)
        text_label.config(font=("Courier", 8))
        self.text[1] = Entry(frame_but1, textvariable = self.text_input_pw, show = "*", highlightcolor = "white")
        self.text[1].pack(expand = 1, padx = 10, pady = 10, side = LEFT)
        
        bottomframe = Frame(frame, bg = "gray10")
        bottomframe.pack(side = TOP, fill = X, expand = 1, ipady = 10)
        but = Button(bottomframe, text = "Login", command = self.login)
        but.pack(side = LEFT, padx = 20)
        but1 = Button(bottomframe, text = "Register", command = self.register)
        but1.pack(side = RIGHT, padx = 20)

        self.text_input_uid.trace(mode="w", callback=self.entryfocus)
        self.text_input_pw.trace(mode="w", callback=self.entryfocus1)
        self.canIclear = False

    def entryfocus(self, *args):
        if self.canIclear: 
            self.text_input_uid.set("")
            self.canIclear = False
        self.text[0].config(bg = "white")
    def entryfocus1(self, *args):
        if self.canIclear: 
            self.text_input_pw.set("")
            self.canIclear = False
        self.text[1].config(bg = "white")

    def login(self): 
        name = self.text_input_uid.get()
        user_acc = self.text_input_uid.get() + "_" + self.text_input_pw.get()
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(bytes(user_acc, 'utf-8'))
        encrypted_key = digest.finalize()
        if not cfg.database.login_user(name, encrypted_key): 
            self.text_input_uid.set("Incorrect login details. Try again.")
            self.canIclear = True
            self.text[0].config(bg = "red")
            self.text[1].config(bg = "red")
        else:
            cfg.userid = name
            cfg.error.updateText("Welcome: {}".format(cfg.userid), "pale green")
            self.helpMenu.destroy()
            self.refresh()
 

    def register(self): 
        name = self.text_input_uid.get()
        user_acc = self.text_input_uid.get() + "_" + self.text_input_pw.get()
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(bytes(user_acc, 'utf-8'))

        encrypted_key = bytes(str(digest.finalize()), 'utf-8')

        if not cfg.database.register_user(name, encrypted_key):
            self.text_input_uid.set("Username already taken.")
            self.canIclear = True
            self.text[0].config(bg = "red")
        else:
            cfg.userid = name
            cfg.error.updateText("Account created: {}".format(cfg.userid), "pale green")
            self.helpMenu.destroy()
            self.refresh()


        #encrypted_user_acc = 

    def uploadDB(self, event = None):
        if self.session_name_set is False:
            if self.text_input.get() is "": return
            cfg.session_name = self.text_input.get()
            self.helpMenu.destroy()
        self.session_name_set = False
        cfg.error.updateText("[DB] Created new session: "+ str(cfg.session_name), "pale green")
        cfg.import_from_local = False
        if cfg.img is not None: cfg.img.save()
        #cfg.json_path = cfg.json_path + ".json"
        imagegen() # Generates template
        str1 = cfg.compile(cfg.json_folder, export_to_local = False)
        self.updateText(str1+"\n", "p")
        self.updateText(">>>"+"-"*15+"\n", "b")
        cfg.error.updateText("JSON Updated successfully", "pale green")
        self.refresh()

        
    
    def download(self):
        cfg.export_to_local = True
        filename = filedialog.askopenfilename(initialdir = cfg.json_folder_config, title = "Select File", filetypes = [("Json File", "*.json")])
        cfg.session_name = cfg.getbasename(filename)
        if cfg.res.size: cfg.res.deleteAllNodes()
        if cfg.image_flag: cfg.myCanvas.deleteImage()
        str1 = cfg.decompile(cfg.json_folder)
        self.updateText(str1+"\n", "p")
        self.updateText(">>>"+"+"*15+"\n", "b")