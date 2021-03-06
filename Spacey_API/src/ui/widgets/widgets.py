################################################# SPACEY Initiation GUI Wizard #############################################
# Author: Looi Kai Wen                                                                                                     #
# Last edited: 28/06/2020                                                                                                  #
# Summary:                                                                                                                 #
#   For use by BLE network administrators to configure their database with invariant information,                          #
#   eg. relative coordinates of the sensor mote, cluster level, etc.                                                       #
#
############################################################################################################################
import sys

print("here", sys.path)
from tkinter import *
import tkinter as tk
from tkinter import filedialog
from ...config import *
from ...node.node_controller import *
from functools import partial
from queue import Queue
from tkinter import font
from ...image import imgpro
from platform import system as platf
from ...image.imagegen import *
from ...storage import redisDB
import time
import hashlib
from ...testconn import internet_on


class map_canvasObject(object):
    def __init__(self, frame, width, height):
        self.canvas = Canvas(
            frame,
            width=width,
            height=height,
            highlightcolor=config.hlcolor,
            highlightthickness=5,
            bg="SteelBlue1",
        )
        self.line_obj = []
        self.rec_obj = {}
        self.border_obj = []
        self.floorplan_obj = None
        config.canvas_w = self.canvas.winfo_reqwidth()
        config.canvas_h = self.canvas.winfo_reqheight()
        self.xlen = config.canvas_w
        self.ylen = config.canvas_h
        # self.canvas.bind('<Configure>' , self.resize)

    def resize(self, event):
        print("resize")
        print(event.width)
        print(event.height)
        config.canvas_w = event.width
        config.canvas_h = event.height
        wscale = float(event.width) / self.xlen
        hscale = float(event.height) / self.ylen
        self.xlen = event.width
        self.ylen = event.height
        # resize the canvas
        self.canvas.config(width=self.xlen, height=self.xlen)
        # rescale all the objects tagged with the "all" tag
        self.canvas.scale("all", 0, 0, wscale, wscale)
        config.map_grid.refresh()

    def resetCursorLocation(self):
        self.canvas.move(
            config.cursor,
            config.x_list[0] - config.x,
            config.y_list[0] - config.y,
        )
        config.x = config.x_list[0]
        config.y = config.y_list[0]

        self.canvas.move(
            config.cursor,
            config.x_list[int(config.scale / 2)]
            - config.x,
            config.y_list[int(config.scale / 2)]
            - config.y,
        )
        config.x = config.x_list[
            int(config.scale / 2)
        ]
        config.y = config.y_list[
            int(config.scale / 2)
        ]

        if config.error is not None:
            config.error.updateText("Cursor location reset.", "yellow")

    def deleteImage(self):
        config.image_flag = False
        self.canvas.delete(self.floorplan_obj)
        config.img_x_bb1 = -1
        config.img_y_bb1 = -1

    def clearAllNodes(self):
        for i in self.rec_obj.values():
            self.canvas.delete(i)
        self.rec_obj.clear()

    def deleteNode(self, idx):
        if config.prev_node_idx is idx:
            config.prev_node_idx = None
        print("canvas")
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
        if config.image_flag:
            self.canvas.tag_raise(self.floorplan_obj)
        for i in self.rec_obj.values():
            self.canvas.tag_raise(i)
        self.canvas.tag_raise(config.cursor)
        for i in self.border_obj:
            self.canvas.tag_raise(i)

    def placeNode(self, idx, x, y):
        self.xlen, self.ylen = (
            config.box_len,
            config.box_len,
        )  # size of node
        # cfg.node = canvas.create_rectangle(xpos, ypos,xpos+self.xlen, ypos+self.ylen, fill = "blue")
        self.rec_obj[idx] = self.canvas.create_rectangle(
            x - self.xlen, y - self.ylen, x + self.xlen, y + self.ylen, fill="blue"
        )


class CanvasGridFrame(object):
    def __init__(self, canvas, num):
        self.xpos, self.ypos, self.xlen, self.ylen = (
            0,
            0,
            config.canvas_w,
            config.canvas_h,
        )
        self.canvas = canvas
        self.deviceID = 0
        config.bg = canvas.create_rectangle(
            self.xpos,
            self.ypos,
            self.xpos + self.xlen,
            self.ypos + self.ylen,
            fill="SteelBlue1",
            width=0,
        )
        self.map_grid = self.createGrid()

    def createGrid(self):
        print("Create grid")
        num = config.scale
        config.step = int(config.canvas_w / num)
        #   cfg.box_len = cfg.step
        config.x_list.clear()
        config.y_list.clear()
        for i in range(num + 10):
            config.x_list.append(
                round(self.xpos + i * config.step)
            )
            config.y_list.append(
                round(self.ypos + i * config.step)
            )
            config.map_canvas.line_obj.append(
                self.canvas.create_line(
                    self.xpos + i * config.step,
                    self.ypos,
                    self.xpos + i * config.step,
                    self.ypos + self.ylen,
                    fill="sky blue",
                    width=2,
                )
            )
            config.map_canvas.line_obj.append(
                self.canvas.create_line(
                    self.xpos,
                    self.ypos + i * config.step,
                    self.xpos + self.xlen,
                    self.ypos + i * config.step,
                    fill="sky blue",
                    width=2,
                )
            )

        config.num_coordinates_max = (
            config.canvas_w / config.step - 1
        ) * (config.canvas_h / config.step - 1)
        # if cfg.error is not None: cfg.error.updateText("Max coordinates: {_num}".format(_num = cfg.num_coordinates_max), "yellow")
        self.drawBoundary(config.step)
        config.map_canvas.resetCursorLocation()
        config.map_canvas.canvas.tag_raise(config.cursor)

    def drawBoundary(self, step):
        if int(config.canvas_w / step) > len(config.x_list):
            return
        print("step: " + str(step))
        print("canvas_w: " + str(config.canvas_w))
        x1 = config.x_list[0]
        x2 = config.x_list[1]
        _x1 = config.x_list[int(config.canvas_w / step) - 1]
        _x2 = config.x_list[int(config.canvas_w / step) - 2]

        y1 = config.y_list[0]
        y2 = config.y_list[1]
        _y1 = config.y_list[int(config.canvas_h / step) - 1]
        _y2 = config.y_list[int(config.canvas_h / step) - 2]

        # inner border bounded by the rectangle is the border of the visible canvas.
        (
            config.x_bb1,
            config.y_bb1,
            config.x_bb2,
            config.y_bb2,
        ) = (x2, y2, _x2, _y2)

        # if no image/ image deleted, set future image to fit the canvas as much as possible
        if config.img_x_bb1 is -1:
            config.img_x_bb1, config.img_y_bb1 = (
                config.x_bb1,
                config.y_bb1,
            )

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
        config.map_canvas.border_obj.append(
            self.canvas.create_rectangle(x1, y1, _x1 + step * 2, y2, fill="gray10")
        )  # north
        config.map_canvas.border_obj.append(
            self.canvas.create_rectangle(
                x1, _y2, _x1 + step * 2, _y1 + step * 10, fill="gray10"
            )
        )  # south
        config.map_canvas.border_obj.append(
            self.canvas.create_rectangle(x1, y2, x2, _y2, fill="gray10")
        )  # west
        config.map_canvas.border_obj.append(
            self.canvas.create_rectangle(_x2, y2, _x1 + step * 2, _y2, fill="gray10")
        )  # east

    def refresh(self, delete=True, resize=True):
        config.load_flag = not resize
        if delete:
            config.node_controller.deleteAllNodes()
        config.map_canvas.deleteAllGrids()
        self.map_grid = self.createGrid()
        # If need resize and there is an image to resize
        if resize and config.image_flag:
            config.img.resize()

        config.map_canvas.canvas.tag_raise(config.cursor)


class CursorNode(object):
    def __init__(self, canvas):
        self.canvas = canvas
        self.xpos, self.ypos = 0, 0
        self.xlen, self.ylen = 10, 10  # size of node
        config.x, config.y = int(
            self.xpos + self.xlen / 2
        ), int(self.ypos + self.ylen / 2)
        config.cursor = canvas.create_rectangle(
            self.xpos,
            self.ypos,
            self.xpos + self.xlen,
            self.ypos + self.ylen,
            fill="red",
        )

        canvas.tag_bind(config.cursor, "<B1-Motion>", self.move)
        canvas.bind("<ButtonRelease-1>", self.release)
        canvas.bind("<Button-3>", self.deleteNode)

        canvas.bind("<Up>", lambda event: self.move_unit(event, "W"))
        canvas.bind("<Left>", lambda event: self.move_unit(event, "A"))
        canvas.bind("<Down>", lambda event: self.move_unit(event, "S"))
        canvas.bind("<Right>", lambda event: self.move_unit(event, "D"))
        canvas.bind("<ButtonRelease-1>", self.release)
        canvas.bind("<KeyRelease-Up>", self.release_unit)
        canvas.bind("<KeyRelease-Down>", self.release_unit)
        canvas.bind("<KeyRelease-Left>", self.release_unit)
        canvas.bind("<KeyRelease-Right>", self.release_unit)
        canvas.bind("<Return>", self.enter)
        canvas.bind("<Button-3>", self.deleteNode)
        canvas.bind("<Control-x>", self.deleteNode)

        self.restaurant = config.node_controller
        self.move_flag = False
        self.callBack = []

    def deleteNode(self, event):
        if (
            config.x,
            config.y,
        ) in self.restaurant.dict_sensor_motes:
            print("deleted")
            self.restaurant.deleteNode(config.x, config.y)
            config.error.updateText(
                "Node deleted at x:{x} and y:{y}".format(
                    x=config.x, y=config.y
                ),
                "deep pink",
            )
            self.nodeDetectCallback()
            return
        else:
            print("Invalid")
            return

    def setCallback(self, cb):
        self.callBack.append(cb)

    def deposit(self):
        print("enter registered")
        if config.deposit_flag is True:
            self.nodeDetectCallback()
            config.deposit_flag = False
        else:
            return

    def estimate(self, x, _list):

        mid = round(len(_list) / 2)
        if len(_list) is 1:
            return _list[0]
        elif len(_list) is 2:
            if abs(_list[0] - x) > abs(_list[1] - x):
                return _list[1]
            else:
                return _list[0]
        else:
            if x > _list[mid]:
                x = x + 1
                return self.estimate(x, _list[mid:])
            elif x < _list[mid]:
                x = x - 1
                return self.estimate(x, _list[:mid])
            else:
                return x

    def move(self, event):
        if self.move_flag:
            new_xpos, new_ypos = event.x, event.y
            self.canvas.move(
                config.cursor,
                new_xpos - self.mouse_xpos,
                new_ypos - self.mouse_ypos,
            )
            config.x += new_xpos - self.mouse_xpos
            config.y += new_ypos - self.mouse_ypos
            self.mouse_xpos = new_xpos
            self.mouse_ypos = new_ypos
        else:
            self.move_flag = True
            self.canvas.tag_raise(config.cursor)
            self.mouse_xpos = event.x
            self.mouse_ypos = event.y

    def move_unit(self, event, dir):
        self.move_flag = True
        print("lol")
        if dir is "W":
            self.canvas.move(config.cursor, 0, -config.step)
            config.y -= config.step
        elif dir is "A":
            self.canvas.move(config.cursor, -config.step, 0)
            config.x -= config.step
        elif dir is "S":
            self.canvas.move(config.cursor, 0, config.step)
            config.y += config.step
        elif dir is "D":
            self.canvas.move(config.cursor, config.step, 0)
            config.x += config.step
        self.canvas.tag_raise(config.cursor)

    def release(self, event):
        new_xpos, new_ypos = self.estimate(
            event.x, config.x_list
        ), self.estimate(event.y, config.y_list)
        self.canvas.move(
            config.cursor,
            new_xpos - config.x,
            new_ypos - config.y,
        )
        self.mouse_xpos = new_xpos
        self.mouse_ypos = new_ypos
        self.move_flag = False
        config.x = new_xpos
        config.y = new_ypos
        config.initflag = True
        self.nodeDetectCallback()
        self.canvas.tag_raise(config.cursor)

    def release_unit(self, event):
        self.move_flag = False
        self.nodeDetectCallback()
        self.canvas.tag_raise(config.cursor)

    def enter(self, event):
        config.initflag = True
        self.nodeDetectCallback()

    def nodeDetectCallback(self):

        if (
            config.x,
            config.y,
        ) in self.restaurant.dict_sensor_motes:
            text = self.restaurant.printMoteAt(
                config.x, config.y
            )
            config.node_idx = self.restaurant.dict_sensor_motes.get(
                (config.x, config.y)
            ).idx
            config.map_canvas.canvas.itemconfig(
                config.map_canvas.rec_obj[config.node_idx],
                fill="orange",
            )
            if (
                config.prev_node_idx is not None
                and config.prev_node_idx is not config.node_idx
            ):
                config.map_canvas.canvas.itemconfig(
                    config.map_canvas.rec_obj[
                        config.prev_node_idx
                    ],
                    fill="blue",
                )
            self.callBack[1]("lawn green")
            self.callBack[0](text)  # Print text on status label
            config.prev_node_idx = config.node_idx

        else:
            if config.prev_node_idx is not None:
                config.map_canvas.canvas.itemconfig(
                    config.map_canvas.rec_obj[
                        config.prev_node_idx
                    ],
                    fill="blue",
                )
            config.deposit_flag = False
            self.callBack[0]("No node information")  # Print text on status label
            if config.err_inval_input:
                self.callBack[1]("MediumPurple1")
            err_inval_input = False


class menu_upload(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.labelFrame = LabelFrame(
            self.frame, text="Floor Plan Manager", height=150, width=550, bg="gray55"
        )
        self.labelFrame.pack(
            fill=X, side=TOP, pady=config.pady, padx=config.padx
        )
        self.obj = Button(
            self.labelFrame,
            text="Import Floor plan",
            command=self.fileupload,
            bg=config.buttcolor,
        )
        self.obj.pack(ipadx=10, ipady=10, fill=X, side=TOP)
        self.obj = Button(
            self.labelFrame,
            text="Clear Floor plan",
            command=self.floorplanclear,
            bg=config.buttcolor,
        )
        self.obj.pack(ipadx=10, ipady=10, fill=X, side=TOP)

    def fileupload(self):
        config.map_canvas.deleteImage()
        config.node_controller.deleteAllNodes()
        try:
            filename = filedialog.askopenfilename(
                initialdir=config.floorplan_folder_input,
                title="Select File",
                filetypes=(
                    ("all files", "*.*"),
                    ("png files", "*.png"),
                    ("jpeg files", "*.jpg"),
                ),
            )
        except:
            config.error.updateText("Upload failed", "red")
            return
        # Create Image generator
        config.img = imgpro.floorPlan(
            filename, config.map_canvas.canvas
        )

    def floorplanclear(self):
        config.map_canvas.deleteImage()
        config.node_controller.deleteAllNodes()
        config.get_output_graphic_path()


class map_refresh(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        # self.frame = Frame(frame)
        # self.frame.map_grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(
            self.frame, text="Grid scale... ", height=150, width=550, bg="gray55"
        )
        self.labelFrame.pack(
            fill=X, side=TOP, pady=config.pady, padx=config.padx
        )
        self.but1 = Button(
            self.labelFrame,
            text="Scale up",
            command=self.updateUp,
            bg=config.buttcolor,
        )
        self.but1.pack(ipadx=10, ipady=10, fill=X)
        self.but2 = Button(
            self.labelFrame,
            text="Scale down",
            command=self.updateDown,
            bg=config.buttcolor,
        )
        self.but2.pack(ipadx=10, ipady=10, fill=X)
        self.factor = factor

    def updateUp(self):
        print("scale: {}".format(config.scale))

        if config.scale >= 120:
            config.error.updateText(
                "[Grid] Cannot scale up any further", "orange"
            )
            return

        config.scale += self.factor
        print("lol: " + str(config.scale))
        refresh = config.map_grid.refresh()

    def updateDown(self):

        if (config.scale - self.factor) <= 0 or int(
            config.canvas_w / (config.scale - self.factor)
        ) > config.max_step:
            config.error.updateText(
                "[Grid] Cannot scale down any further", "orange"
            )
            return

        config.scale -= self.factor
        refresh = config.map_grid.refresh()


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

        self.labelFrame = LabelFrame(
            self.frame, text="Set Sensor ID", height=500, width=550, bg="gray55"
        )
        self.labelFrame.pack(
            fill=X, side=TOP, pady=config.pady, padx=config.padx
        )

        # Autosaved entries
        self.nodeEntry = [-1, -1, -1]
        self.prevEntry = [-1, -1, -1]

        # Set up rows of entry
        self.titleName = ["Level ID", "Cluster ID", "Sensor ID"]
        for i in range(self.numEntries):
            self.setEntryRow(i)

        # Key bindings
        for j in range(len(self.entryList)):  # bind all entries
            self.entryList[j].bind("<Return>", lambda event: self.enter(event, j))

    def setEntryRow(self, i):
        self.rowFrame.append(Frame(self.labelFrame, bg="gray55"))
        self.rowFrame[i].pack(side=TOP, fill=X, padx=10, pady=5)
        self.entryLabel.append(
            Label(self.rowFrame[i], text=self.titleName[i], bd=5, width=8)
        )
        self.entryLabel[i].pack(side=LEFT)
        self.entryList.append(
            Entry(
                self.rowFrame[i],
                bd=5,
                textvariable=self.text[i],
                highlightcolor=config.hlcolor,
                highlightthickness=5,
                highlightbackground="gray55",
                width=6,
            )
        )
        self.entryList[i].pack(side=LEFT)
        self.radio.append(
            Checkbutton(
                self.rowFrame[i],
                text="Hold",
                variable=self.hold[i],
                command=partial(self.restorePreviousEntries, i),
                bg="gray55",
            )
        )
        self.radio[i].pack(side=LEFT)

    def restorePreviousEntries(self, i):
        if self.hold[i].get():  # If the user selects radio button

            if (
                self.entryList[i].get() is ""
            ):  # If the user wants to recall and hold previous entry
                if i == 2:
                    self.prevEntry[i] += 1
                self.text[i].set(self.prevEntry[i])

            else:  # If the user typed a value to hold to
                self.text[i].set(self.entryList[i].get())
            self.entryList[i].config(state=DISABLED, disabledbackground="sky blue")
        else:
            self.text[i].set("")
            self.entryList[i].config(state=NORMAL)

    def setCallback(self, cb):
        self.callBack.append(cb)

    def highlightDeviceInfo(self, _bg):
        print("highlight: " + str(_bg))
        for i in self.entryList:
            i.config(bg=_bg)
        if self.keyEntry is None:
            self.keyEntry = self.entryList[0]

        # Grant focus to the entry only if it comes from a <Return> or a <Mouse Release>
        if config.initflag:
            self.keyEntry.focus()
            self.keyEntry.config(bg="yellow")
            config.initflag = False

    def enter(self, event, id):

        emptyCount = []
        # Performs a check throughout the inputs of all 3 entries

        for i in range(len(self.entryList)):

            if not len(self.entryList[i].get()):
                self.error_text.insert(
                    i,
                    ("<Entry [{num}]>: Empty".format(num=self.titleName[i]), "yellow"),
                )
                self.entryList[i].config(bg="red")
                self.needCorrect[i] = True
            elif (self.entryList[i].get()).isnumeric():
                if int(self.entryList[i].get()) >= 0:
                    self.nodeEntry[i] = int(self.entryList[i].get())
                    self.entryList[i].config(bg="lawn green")
                    self.needCorrect[i] = False
                    self.error_text.insert(i, None)
                else:
                    self.error_text.insert(
                        i,
                        (
                            "<Entry [{num}]>: Number must be positive".format(
                                num=self.titleName[i]
                            ),
                            "orange",
                        ),
                    )
                    self.entryList[i].config(bg="red")
                    self.needCorrect[i] = True

            else:
                self.error_text.insert(
                    i,
                    (
                        "<Entry [{num}]>: Entry must be a positive number".format(
                            num=self.titleName[i]
                        ),
                        "orange",
                    ),
                )
                self.entryList[i].config(bg="red")
                self.needCorrect[i] = True

        numErrors = 0
        for i in self.needCorrect:
            numErrors += i
        print(self.needCorrect)
        if numErrors:
            print(self.error_text)
            self.keyEntry = self.entryList[self.needCorrect.index(True)]
            config.error.updateText(
                self.error_text[self.needCorrect.index(True)][0],
                self.error_text[self.needCorrect.index(True)][1],
            )
            self.keyEntry.focus_set()
            return  # If there are invalid entries, cannot proceed to store data.

        self.error_text.clear()
        config.error.updateText("No error", "pale green")
        flag = True
        # If not voted by radio to hold value, clear it
        for i in range(len(self.entryList)):
            if not self.hold[i].get():
                self.entryList[i].delete(0, END)
                if flag:
                    self.keyEntry = self.entryList[i]
                    flag = False

        x = self.nodeEntry

        if (
            config.node_controller.registerNode(
                config.x,
                config.y,
                x[0],
                x[1],
                x[2],
                config.node,
            )
            is False
        ):
            config.err_inval_input = True
            self.highlightDeviceInfo("red")
            config.error.updateText(
                "[KeyError] Repeated cluster number! Key in a different combination of <cluster ID> <cluster level> <sensor ID>",
                "red",
            )
            self.keyEntry = self.entryList[0]
            self.keyEntry.focus_set()
            return

        for i in range(3):
            self.prevEntry[i] = self.nodeEntry[i]
            if i == 2 and self.hold[i].get():
                self.prevEntry[i] += 1
                self.text[i].set(self.prevEntry[i])

        # Deposit sensor node on map
        config.deposit_flag = True
        self.callBack[0]()

        # Save sensor detail locally in previously declared class

        config.node_controller.printMoteAt(
            config.x, config.y
        )

        # Reset the intermediate entry
        self.nodeEntry = [-1, -1, -1]

        self.callBack[1]()  # Callback to deposit sensor node
        self.callBack[2](1)  # Callback to give up focus back to canvas


class menu_status(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.labelFrame = LabelFrame(
            self.frame, text="Status bar", bg="gray55", height=150, width=550
        )
        self.labelFrame.pack(
            fill=X, padx=config.padx, pady=config.pady, side=TOP
        )
        self.labelFrame.pack_propagate(0)
        self.obj = Label(self.labelFrame, text="", bd=100, height=400, width=550)
        self.obj.pack(padx=10, pady=10)

    def updateText(self, _text):
        self.obj.configure(text=_text)
        self.obj.update()


class menu_help(object):
    def __init__(self, frame, width, height):
        self.frame = frame
        self.labelFrame = LabelFrame(
            self.frame, text="Help", bg="gray55", height=117 - 51, width=550
        )
        self.labelFrame.pack(
            fill=X, padx=config.padx, pady=config.pady, side=TOP
        )
        self.labelFrame.pack_propagate(0)
        self.obj = Button(
            self.labelFrame,
            text="Press me for help!",
            command=self.newWindow,
            bg="sky blue",
        )
        self.obj.pack(ipadx=10, ipady=10, fill=X)

    def newWindow(self):
        self.displayHelpMenu(config.root)

    def displayHelpMenu(self, root):
        helpMenu = Toplevel(root)
        helpMenu.geometry("500x" + str(config.canvas_h))
        helpMenu.title("Help Menu")
        # Icon of the window
        if platf() == "Linux":
            img = PhotoImage(file=config.gif_path)
            helpMenu.tk.call("wm", "iconphoto", helpMenu._w, img)
        elif platf() == "Windows":
            helpMenu.iconbitmap(config.icon_path)
        # x,y = self.findCentralize(helpMenu)
        # helpMenu.geometry("+{}+{}".format(x, y))
        frame = Frame(helpMenu, bg="gray10")
        frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=1)
        help = self.helpMessage(frame)
        helpMenu.configure(bg="sky blue")
        helpMenu.bind("<Escape>", lambda event: self.quitTop(event, helpMenu))

    def helpMessage(self, frame):
        config.help_font = font.Font(family="Arial", size=8, weight="bold")
        text = Text(
            frame, bg="white", font=config.help_font, bd=10, wrap=WORD
        )
        yscroll = Scrollbar(frame, orient="vertical", command=text.yview)
        yscroll.pack(padx=2, pady=2, side=LEFT, fill=Y)
        text.pack(pady=2, ipadx=2, ipady=2, side=LEFT, fill=tk.BOTH, expand=1)
        text.configure(yscrollcommand=yscroll.set)

        text.tag_config(
            "h1",
            foreground="deepskyblue2",
        )
        text.tag_config("h2", foreground="black")
        text.tag_config("h3a", foreground="DarkOrange1", justify=LEFT)
        text.tag_config("h3b", foreground="blue4", justify=LEFT)

        ##color##
        text.tag_config("h_red", foreground="red")
        text.tag_config("h_green", foreground="green")
        text.tag_config("h_purple", foreground="purple")
        text.tag_config("h_yellow", foreground="darkorange")
        text.tag_config("h_blue", foreground="blue")

        text.insert(END, "Info:", "h1")
        text.insert(
            END,
            "\nThis Node Manager allows network administrators to synchronise the location of the sensor motes with the graphic to be generated, as well as the communication of location-specific information between the sensor motes and the database."
            + "\n\nThe interface controls are easy to use and intuitive, allowing the user to quickly form a map of the sensor mote network without much delay. The graphic is then generated automatically for you! \n\nThe Node Manager comes embedded with an image processing functionality, which edits your floorplan image down to size and color requirement to fit on the canvas. \n\nSpacey Node Manager is now integrated with RedisDB. You can now create floor plans and save them in the cloud! You can also choose to save your work on your local drive.",
            "h2",
        )

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
        text.insert(
            END,
            " You may use the cursor to navigate the grid. You can navigate to an empty grid point to insert a Node, or navigate to an existing node to delete it off. Refer to the previous section above on the relevant controls.",
            "h2",
        )

        text.insert(END, "\nClear Floor plan", "h3a")
        text.insert(
            END, "\nUnder menu 1. Click to clear the canvas of the contents.", "h2"
        )

        text.insert(END, "\nFloor Plan upload", "h3a")
        text.insert(
            END,
            "\nUnder menu 1. You may upload your floor plan image using the upload button, preferably in PNG format. Feel free to grab some random floor plan for the internet and try it on the GUI!",
            "h2",
        )

        text.insert(END, "\nSet Sensor ID", "h3a")
        text.insert(
            END,
            "\n Under menu 1. The Sensor ID is a unique string associated with each sensor node, and MUST CORRESPOND with the sensor ID you have set on the ground. You may use the entry boxes to enter the sensor information, after you place the cursor on the grid and place a node. The entry boxes only accept integer inputs, and will not proceed upon an invalid input. Repeated entries are also not allowed.\n The color of the entry boxes denote its status to advise you on your next course of action:",
            "h2",
        )
        text.insert(END, "\n\n\tRED:\t\t\t" + "Needs correction to text field", "h_red")
        text.insert(
            END, "\n\tGREEN:\t\t\t" + "Valid Entry, node already placed here", "h_green"
        )
        text.insert(
            END,
            "\n\tPURPLE:\t\t\t" + "No Entry yet, node can be placed here",
            "h_purple",
        )
        text.insert(
            END, "\n\tYELLOW:\t\t\t" + "Awaiting Entry, fill in text field", "h_yellow"
        )
        text.insert(
            END,
            '\n\nYou can use the "hold" radio button to set your own value/freeze previous value, in case you are placing nodes with the same cluster id/ level. For the last entry box, the hold button allows you to set incremental values without typing it yourself!\n\nDo note that you are not allowed to enter the same combination more than once. As such, you should use the hold buttons to your advantage and spam away if you are only here to try the UI. Our interface is very keyboard-friendly! ',
            "h2",
        )
        text.insert(END, "\n\nStatus Bar", "h3a")
        text.insert(
            END,
            "\nUnder menu 1. You may use it to track the node information on an existing node.",
            "h2",
        )

        text.insert(END, "\nDebugger", "h3a")
        text.insert(
            END,
            "\nUnder menu 1. Alerts you of any status updates/ errors encountered",
            "h2",
        )

        text.insert(END, "\nDimension adjustments", "h3a")
        text.insert(
            END,
            "\nUnder menu 2. You may adjust the node size, grid partition size and floor plan size via the top menu 2 controls. You can also move the floorplan linearly. This is to allow you to find the best graphical configuration where the grid points best coincide with the seats on your floor plan to place the sensor nodes. The configuration you view here will be reflected on the output graphic.",
            "h2",
        )

        text.insert(END, "\nJSON Viewer", "h3a")
        text.insert(
            END,
            '\nUnder menu 2. You can save your work into a JSON file by clicking the "Upload JSON [Local]" button. Conversely, you can load a previous save file by clicking the "Download JSON [Local]" button. You can use the viewer below to check the JSON file contents for debugging purposes.',
            "h2",
        )
        text.insert(END, "\nDB Operations", "h3a")
        text.insert(
            END,
            "\nUnder menu 2. You can save your work to, or download an existing work from a running Redis Database!\n\n Users will need to register a new account, or use an existing account: \n\n\tUsername: NTU\n\tPassword: password\n\nYou can create a new restaurant under the account, then upload the restaurant information to the account on the cloud database. Once done, you can begin operation once you configured your sensor network properly!\nYou can also use this feature to update your restaurants' address and opening hours, which are displayed to the client from the chatbot.",
            "h2",
        )

        text.configure(state="disabled")

    def quitTop(self, event, top):
        top.destroy()
        top.update()


class menu_debug(object):
    def __init__(self, frame, width, height):
        # cfg.error_font = font.Font(family = "Times", font = "3", weight =  "BOLD")
        config.error_font = font.Font(
            family="Courier New", size=8, weight="bold"
        )
        self.frame = frame
        self.labelFrame = LabelFrame(
            self.frame, text="Debugger", bg="gray55", height=500, width=550
        )
        self.labelFrame.pack(
            fill=X, padx=config.padx, pady=config.pady, side=TOP
        )
        self.labelFrame.pack_propagate(0)
        self.obj = Listbox(
            self.labelFrame,
            height=300,
            width=550,
            bg="gray10",
            font=config.error_font,
        )
        self.yscroll = Scrollbar(
            self.labelFrame, orient="vertical", command=self.obj.yview
        )
        self.xscroll = Scrollbar(
            self.labelFrame, orient="horizontal", command=self.obj.xview
        )

        self.yscroll.pack(padx=10, pady=10, side=LEFT, fill=Y)
        self.xscroll.pack(padx=0, pady=10, side=TOP, fill=X)
        self.obj.pack(ipadx=30, ipady=30, side=LEFT, fill=Y)

        self.obj.configure(
            xscrollcommand=self.xscroll.set, yscrollcommand=self.yscroll.set
        )
        self.obj.insert(END, "Initialized")
        self.obj.itemconfig(0, foreground="sky blue")

    def updateText(self, _text, _bg):
        config.updateTextDone = False
        self.obj.insert(0, _text)
        self.obj.itemconfig(0, foreground=_bg)
        # self.obj.insert(END, " ")
        # self.obj.see(0)
        config.updateTextDone = False
        config.root.update_idletasks()
        # self.obj.update()
        return True


class img_xyshift(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        # self.frame = Frame(frame)
        # self.frame.map_grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(
            self.frame, text="Floorplan shifts...", height=140, width=550, bg="gray55"
        )
        self.labelFrame.pack(
            fill=X, side=TOP, pady=config.pady, padx=config.padx
        )
        self.parentFrame1 = Frame(self.labelFrame, height=140)
        self.parentFrame2 = Frame(self.labelFrame, height=140)
        self.parentFrame1.pack(side=LEFT, padx=10)
        self.parentFrame2.pack(side=LEFT, padx=10)

        self.framex = Frame(self.parentFrame1, height=70)
        self.framey = Frame(self.parentFrame1, height=70)
        self.framex.pack(side=TOP, fill=X)
        self.framey.pack(side=TOP, fill=X)

        self.but1 = Button(
            self.framex,
            text="Left",
            command=self.left,
            width=2,
            bg=config.buttcolor,
        )
        self.but1.pack(ipadx=10, ipady=10, side=LEFT)
        self.but2 = Button(
            self.framex,
            text="Right",
            command=self.right,
            width=2,
            bg=config.buttcolor,
        )
        self.but2.pack(ipadx=10, ipady=10, side=LEFT)

        self.but1 = Button(
            self.framey,
            text="Up",
            command=self.up,
            width=2,
            bg=config.buttcolor,
        )
        self.but1.pack(ipadx=10, ipady=10, side=LEFT)
        self.but2 = Button(
            self.framey,
            text="Down",
            command=self.down,
            width=2,
            bg=config.buttcolor,
        )
        self.but2.pack(ipadx=10, ipady=10, side=LEFT)

        self.framex2 = Frame(self.parentFrame2, height=70)
        self.framey2 = Frame(self.parentFrame2, height=70)
        self.framex2.pack(side=TOP, fill=X)
        self.framey2.pack(side=TOP, fill=X)

        self.but1 = Button(
            self.framex2,
            text="Expand",
            command=self.s_up,
            width=8,
            bg=config.buttcolor,
        )
        self.but1.pack(ipadx=10, ipady=10, fill=X, side=TOP)
        self.but2 = Button(
            self.framey2,
            text="Contract",
            command=self.s_down,
            width=8,
            bg=config.buttcolor,
        )
        self.but2.pack(ipadx=10, ipady=10, fill=X, side=TOP)

        self.factor = factor

    def left(self):
        config.img_x_bb1 -= self.factor
        config.map_canvas.canvas.move(
            config.map_canvas.floorplan_obj, -self.factor, 0
        )

    def right(self):
        config.img_x_bb1 += self.factor
        config.map_canvas.canvas.move(
            config.map_canvas.floorplan_obj, self.factor, 0
        )

    def up(self):
        config.img_y_bb1 -= self.factor
        config.map_canvas.canvas.move(
            config.map_canvas.floorplan_obj, 0, -self.factor
        )

    def down(self):
        config.img_y_bb1 += self.factor
        config.map_canvas.canvas.move(
            config.map_canvas.floorplan_obj, 0, self.factor
        )

    def s_up(self):
        if config.map_canvas.floorplan_obj is None:
            config.error.updateText(
                "<Floor Plan> Cannot scale down before inserting floor plan!", "orange"
            )
            return
        if config.img_padding == 0:
            config.error.updateText(
                "<Floor Plan> Cannot scale down further", "orange"
            )
            return
        config.img_padding -= self.factor
        config.img.resize()

    def s_down(self):
        config.img_padding += self.factor
        config.img.resize()


class img_scaleshift(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        # self.frame = Frame(frame)
        # self.frame.map_grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(
            self.frame, text="Floorplan scales...", height=150, width=550, bg="gray55"
        )
        self.labelFrame.pack(
            fill=X, side=TOP, pady=config.pady, padx=config.padx
        )
        self.but1 = Button(
            self.labelFrame,
            text="Size +",
            command=self.up,
            width=4,
            bg=config.buttcolor,
        )
        self.but1.pack(ipadx=10, ipady=10, side=LEFT)
        self.but2 = Button(
            self.labelFrame,
            text="Size -",
            command=self.down,
            width=4,
            bg=config.buttcolor,
        )
        self.but2.pack(ipadx=10, ipady=10, side=LEFT)
        self.factor = factor

    def up(self):
        if config.img_padding == 0:
            config.error.updateText(
                "<Floor Plan> Cannot scale down further", "orange"
            )
            return
        config.padding -= self.factor
        config.img.resize()

    def down(self):
        config.img_padding += self.factor
        config.img.resize()


class node_scaleshift(object):
    def __init__(self, frame, factor, width, height):
        self.frame = frame
        # self.frame = Frame(frame)
        # self.frame.map_grid(row = 0, column = 0, sticky = E+W)
        self.labelFrame = LabelFrame(
            self.frame, text="Node scales...", height=150, width=550, bg="gray55"
        )
        self.labelFrame.pack(
            fill=X, side=TOP, pady=config.pady, padx=config.padx
        )
        self.but1 = Button(
            self.labelFrame,
            text="Up",
            command=self.up,
            width=4,
            bg=config.buttcolor,
        )
        self.but1.pack(ipadx=10, ipady=10, side=LEFT, padx=25)
        self.but2 = Button(
            self.labelFrame,
            text="Down",
            command=self.down,
            width=4,
            bg=config.buttcolor,
        )
        self.but2.pack(ipadx=10, ipady=10, side=LEFT, padx=12)
        self.factor = factor

    def up(self):
        config.box_len += self.factor
        config.error.updateText(
            "Node length: {n}".format(n=config.box_len), "yellow"
        )
        config.node_controller.changeNodeSize()

    def down(self):
        config.box_len -= self.factor
        config.node_controller.changeNodeSize()


class json_viewer(object):
    def __init__(self, frame, width, height):
        # cfg.error_font = font.Font(family = "Times", font = "3", weight =  "BOLD")
        config.json_font = font.Font(
            family="Courier New", size=8, weight="bold"
        )
        self.frame = frame
        self.labelFrame = LabelFrame(
            self.frame, text="JSON Viewer", bg="gray55", height=550, width=550
        )
        self.labelFrame.pack(
            fill="x",
            padx=config.padx,
            pady=config.pady,
            side=TOP,
        )
        self.labelFrame.pack_propagate(0)
        self.frame2 = Frame(self.labelFrame, bg="gray55", height=40)
        self.frame2.pack(fill=X, side=TOP)
        self.frame1 = Frame(self.labelFrame, bg="gray55")
        self.frame1.pack(fill=X, side=TOP)

        self.butt1 = Button(
            self.frame2,
            text="Import JSON [Local]",
            command=self.download,
            width=550,
            bg=config.buttcolor,
        )
        self.butt1.pack()
        self.butt = Button(
            self.frame2,
            text="Export JSON [Local]",
            command=self.upload,
            width=550,
            bg=config.buttcolor,
        )
        self.butt.pack()
        self.dbframe = LabelFrame(self.frame2, text="RedisDB Operations: ", bg="gray55")
        self.dbframe.pack(expand=True, fill=X, ipadx=2, ipady=2)

        self.refreshbutt = Button(
            self.dbframe,
            text="Connect to RedisDB",
            command=self.refreshDB,
            width=550,
            bg="IndianRed2",
            activebackground="salmon",
        )
        # self.refreshbutt = Button(self.dbframe, text = "Connect to RedisDB", command = partial(self.displayUploadMenu, cfg.root), width = 550, bg = "IndianRed2", activebackground= "salmon")
        self.refreshbutt.pack()
        self.dbselect = tk.StringVar(config.root)
        self.dbselect.set(config.db_options[0])  # default value
        self.dbselect.trace("w", self.callback)
        self.optionmenu = OptionMenu(
            self.dbframe, self.dbselect, *config.db_options
        )
        self.optionmenu.pack(expand=1, fill=X)

        self.butt2 = Button(
            self.dbframe,
            text="Import from DB",
            command=self.downloadDB,
            width=550,
            bg="RosyBrown1",
        )
        self.butt2.pack_forget()
        self.butt3 = Button(
            self.dbframe,
            text="Export to DB",
            command=partial(self.displayUploadMenu, config.root),
            width=550,
            bg="RosyBrown1",
        )
        self.butt3.pack_forget()

        self.buttdel1 = Button(
            self.dbframe,
            text="Delete Selected Restaurant",
            command=self.DBclearDB,
            width=550,
            bg="RosyBrown1",
        )
        self.buttdel1.pack_forget()
        self.buttdel2 = Button(
            self.dbframe,
            text="Delete Account",
            command=self.DBclearUser,
            width=550,
            bg="RosyBrown1",
        )
        self.buttdel2.pack_forget()
        self.buttupdate = Button(
            self.dbframe,
            text="Update Restaurant Information",
            command=partial(self.displayUploadMenu, config.root, True),
            width=550,
            bg="sky blue",
        )
        self.buttupdate.pack_forget()

        # self.butt.pack(ipadx = 30, ipady = 30, fill = X)
        self.obj = Text(
            self.frame1,
            width=550,
            height=190,
            bg="gray10",
            font=config.json_font,
        )
        self.yscroll = Scrollbar(self.frame1, orient="vertical", command=self.obj.yview)
        self.yscroll.pack(padx=10, pady=10, side=LEFT, fill=Y)
        self.obj.pack(pady=10, ipadx=30, ipady=30, side=LEFT, fill=Y)

        self.obj.configure(yscrollcommand=self.yscroll.set)
        self.obj.tag_config("b", foreground="sky blue")
        self.obj.tag_config("p", foreground="deep pink")
        self.obj.tag_config("y", foreground="yellow")
        self.obj.insert(END, "Wait for JSON to be \nuploaded...\n\n", "b")

        self.text_input = [StringVar() for i in range(3)]

    def refreshDB(self):
        if not internet_on():
            config.error.updateText(
                "[DB] No Network... cannot connect to database", "red"
            )
            return

        config.error.updateText("[DB] Connecting...", "yellow")

        err = config.database.timeout()
        if err == 1:
            config.error.updateText(
                "[DB] No Network... cannot connect to database", "red"
            )
        else:

            config.error.updateText(
                "[DB] Connected to database", "pale green"
            )
            config.db_options.clear()
            # cfg.db_options += cfg.database.get_registered_restaurants()
            self.displayLoginMenu(config.root)

    def DBclearUser(self):
        config.database.clearUser(config.userid)
        config.error.updateText(
            "Acc Del: {}. See you!".format(config.userid), "yellow"
        )
        config.userid = ""
        self.refresh()

    def DBclearDB(self):
        res = self.dbselect.get()
        name = res
        config.database.clearDB(name)
        config.error.updateText(
            "Restaurant deleted: {}".format(name), "yellow"
        )
        self.refresh()

    def refresh(self):
        # Reset var and delete all old options
        self.dbselect.set("")
        self.optionmenu["menu"].delete(0, "end")

        # Insert list of new options (tk._setit hooks them up to var)
        if config.userid == "":
            config.db_options.clear()
            config.db_options = ["No Database Selected"]
            self.dbselect.set(config.db_options[0])
            return

        new_choices = [
            "Enter New Restaurant"
        ] + config.database.get_registered_restaurants()
        for choice in new_choices:
            self.optionmenu["menu"].add_command(
                label=choice, command=tk._setit(self.dbselect, choice)
            )
        self.dbselect.set(new_choices[0])

    def callback(self, *args):
        if self.dbselect.get() == "No Database Selected":
            self.butt2.pack_forget()
            self.butt3.pack_forget()
            self.buttdel1.pack_forget()
            self.buttdel2.pack_forget()
            self.buttupdate.pack_forget()
            self.session_name_set = False
            config.session_name = None
        elif self.dbselect.get() == "Enter New Restaurant":
            self.butt2.pack_forget()
            self.butt3.pack()
            self.buttdel1.pack_forget()
            self.buttdel2.pack()
            self.buttupdate.pack_forget()
            self.session_name_set = False
            config.session_name = None
        else:
            self.butt2.pack()
            self.butt3.pack()
            self.buttdel1.pack()
            self.buttdel2.pack()
            self.buttupdate.pack()
            config.session_name = self.dbselect.get()
            self.session_name_set = True

            config.res_info = config.database.getResInfo(
                config.userid + "_" + config.session_name
            )
            for i in config.res_info_op:
                print(config.res_info)
                config.getvar()[i] = config.res_info[i]
            config.res_info.clear()

    def updateText(self, _text, _bg):

        self.obj.insert(END, _text, _bg)
        self.obj.see("end")

    def downloadDB(self):
        while True:
            if (
                config.error.updateText(
                    "Downloading, please wait...", "yellow"
                )
                == True
            ):
                break

        if self.dbselect.get() in ["No Database Selected", "No restaurants stored"]:
            return
        config.local_disk = False
        config.session_name = self.dbselect.get()
        if config.node_controller.size:
            config.node_controller.deleteAllNodes()
        if config.image_flag:
            config.map_canvas.deleteImage()
        str1 = config.decompile(
            config.json_folder, local_disk=False
        )
        config.error.updateText("JSON Updated successfully", "pale green")
        self.updateText(str1 + "\n", "p")
        self.updateText(">>>" + "+" * 15 + "\n", "b")

    def upload(self):
        config.error.updateText("Uploading, please wait...", "yellow")
        time.sleep(2)
        if config.node_controller.size == 0:
            config.error.updateText("[ERR] Need at least 1 node", "red")
            return
        config.local_disk = True
        try:
            config.json_path = filedialog.asksaveasfilename(
                initialdir=config.json_folder_config,
                title="Select File",
                filetypes=[("Json File", "*.json")],
            )
        except:
            config.error.updateText("Upload failed", "red")
        config.session_name = config.getbasename(
            config.json_path
        )

        if config.img is not None:
            config.img.save()
        # cfg.json_path = cfg.json_path + ".json"
        if config.map_canvas.floorplan_obj is None:
            config.no_floor_plan = True
        else:
            config.no_floor_plan = False
        imagegen()  # Generates template
        str1 = config.compile(config.json_folder)
        self.updateText(str1 + "\n", "p")
        self.updateText(">>>" + "-" * 15 + "\n", "b")
        config.error.updateText("JSON Updated successfully", "pale green")
        self.refresh()

    def displayUploadMenu(self, root, update=False):

        # If restaurant is recognised
        if self.dbselect.get() not in [
            "No Database Selected",
            "No restaurants stored",
            "Enter New Restaurant",
        ]:
            config.session_name = self.dbselect.get()

            if update is False:
                self.uploadDB()
                return
            else:
                config.res_info = config.database.getResInfo(
                    config.userid + "_" + config.session_name
                )

                for i in config.res_info_op:
                    print(config.res_info)
                    config.getvar()[i] = config.res_info[i]

                config.res_info.clear()

        if config.node_controller.size == 0 and update == False:
            config.error.updateText("[ERR] Need at least 1 node", "red")
            return
        self.helpMenu = Toplevel(root)
        self.helpMenu.geometry("300x750")
        if update:
            self.helpMenu.configure(bg="sky blue")
        else:
            self.helpMenu.configure(bg="tomato2")

        if update:
            self.helpMenu.title("Update Restaurant Details!")
        else:
            self.helpMenu.title("Enter Restaurant Details!")
        # Icon of the window
        if platf() == "Linux":
            img = PhotoImage(file=config.gif_path)
            self.helpMenu.tk.call("wm", "iconphoto", self.helpMenu._w, img)
        elif platf() == "Windows":
            self.helpMenu.iconbitmap(config.icon_path)

        frame = Frame(self.helpMenu, bg="gray10")
        info_frame1 = Frame(self.helpMenu, bg="gray10")
        info_frame2 = LabelFrame(
            self.helpMenu,
            bg="gray10",
            text="Enter location coordinates\nfor Google Map support!",
            font=("Courier, 10"),
            foreground="white",
        )
        info_frame3 = Frame(self.helpMenu, bg="gray10")
        info_frame4 = Frame(self.helpMenu, bg="gray10")

        if update:
            _text = "Update your restaurant information."
        else:
            _text = (
                "Please enter the restaurant name,\nthat field is compulsory!\n\nYou can choose to input your\nrestaurant details so that\nother customers can find you!",
            )

        Label(
            self.helpMenu,
            bg="gray10",
            text=_text,
            height=10,
            foreground="white",
            font=("Courier, 12"),
        ).pack(fill=X, side=TOP, pady=15, padx=10)

        frame.pack(fill=X, side=TOP, pady=15, padx=10)

        info_frame2.pack(fill=X, side=TOP, pady=2, padx=10)
        info_frame3.pack(fill=X, side=TOP, pady=2, padx=10)
        info_frame1.pack(fill=X, side=TOP, pady=2, padx=10)
        info_frame4.pack(fill=BOTH, side=TOP, pady=2, padx=2, expand=1)

        # LONG, LAT, ADDR, OPHR

        Label(
            frame,
            text="Restaurant Name",
            bg="gray10",
            foreground="white",
            font=("Courier, 10"),
        ).pack(side=LEFT, padx=10, pady=10)
        # restaurant nam -> text_input[0]
        e = Entry(frame, textvariable=self.text_input[0], bg="khaki")
        e.pack(fill=X, padx=8, pady=10, side=LEFT, expand=1)

        res_op_hr = LabelFrame(
            info_frame1,
            text="Operating hours: \neg. <Mon-Sun, 7.00am - 9.30pm>",
            bg="gray10",
            foreground="white",
            font=("Courier, 10"),
        )
        res_op_hr.pack(expand=1, fill=X)
        # op hrs -> t1
        self.t1 = Text(res_op_hr, width=15, height=7)
        self.t1.pack(padx=2, pady=2, fill=X)

        res_addr_hr = LabelFrame(
            info_frame3,
            text="Restaurant Address",
            bg="gray10",
            foreground="white",
            font=("Courier, 10"),
        )
        res_addr_hr.pack(expand=1, fill=X)
        # addr -> t2
        self.t2 = Text(res_addr_hr, width=15, height=7)
        self.t2.pack(padx=2, pady=2, fill=X)

        Label(
            info_frame2,
            text="Lat",
            bg="gray10",
            foreground="white",
            font=("Courier, 10"),
        ).pack(side=LEFT, padx=10, pady=10)
        Entry(info_frame2, textvariable=self.text_input[1], width=7).pack(
            padx=10, pady=10, side=LEFT
        )

        Label(
            info_frame2,
            text="Long",
            bg="gray10",
            foreground="white",
            font=("Courier, 10"),
        ).pack(side=LEFT, padx=10, pady=10)
        Entry(info_frame2, textvariable=self.text_input[2], width=7).pack(
            padx=8, pady=10, side=LEFT
        )
        # Button(info_frame4, text = "Register restaurant", command = self.uploadDB)
        if update:
            Button(
                info_frame4,
                text="Update restaurant",
                command=partial(self.updateInfo, False),
                font=("Courier, 10"),
                height=3,
            ).pack(fill=X, expand=1, padx=10, pady=10)
        else:
            Button(
                info_frame4,
                text="Register restaurant",
                command=partial(self.updateInfo, True),
                font=("Courier, 10"),
                height=3,
            ).pack(fill=X, expand=1, padx=10, pady=10)

        if update:
            self.text_input[0].set(config.session_name)
            e.config(state=DISABLED)
            for i in config.res_info_op:
                if config.getvar()[i].rstrip("\n") == "-":
                    temp = ""
                else:
                    temp = config.getvar()[i].rstrip("\n")
                if i == "res_addr":
                    self.t2.insert(1.0, temp)
                elif i == "res_occup_hr":
                    self.t1.insert(1.0, temp)
                elif i == "res_lat":
                    self.text_input[1].set(temp)
                elif i == "res_lng":
                    self.text_input[2].set(temp)
        else:
            temp = ""
            self.t2.insert(1.0, temp)
            self.t1.insert(1.0, temp)
            self.text_input[0].set(temp)
            self.text_input[1].set(temp)
            self.text_input[2].set(temp)

    def updateInfo(self, push_floor_plan):
        config.res_lat = self.text_input[1].get().rstrip("\n")
        config.res_lng = self.text_input[2].get().rstrip("\n")
        config.res_addr = self.t2.get(1.0, END).rstrip("\n")
        config.res_occup_hr = self.t1.get(1.0, END).rstrip("\n")
        for i in config.res_info_op:
            if len(config.getvar()[i].rstrip("\n")) == 0:
                print("here")
                config.getvar()[i] = "-"
        if push_floor_plan:
            if self.text_input[0].get() is "":
                config.error.updateText("Empty field not allowed!", "Red")
                return
            self.uploadDB()
        else:
            for i in config.res_info_op:
                config.resinfo[i] = config.getvar()[i]
            if config.database.setResInfo(
                config.userid + "_" + config.session_name,
                config.resinfo,
            ):
                config.error.updateText(
                    "Updated Restaurant info!", "pale green"
                )
                self.helpMenu.destroy()

    def displayLoginMenu(self, root):
        self.helpMenu = Toplevel(root)
        self.helpMenu.geometry("300x150")
        self.helpMenu.configure(bg="tomato2")
        self.helpMenu.title("Enter Login Details")

        # Icon of the window
        if platf() == "Linux":
            img = PhotoImage(file=config.gif_path)
            self.helpMenu.tk.call("wm", "iconphoto", self.helpMenu._w, img)
        elif platf() == "Windows":
            self.helpMenu.iconbitmap(config.icon_path)
        frame = Frame(self.helpMenu, bg="gray10")
        frame.pack(expand=1, padx=15, pady=10, fill=X)

        self.text = [None, None]

        self.text_input_uid = StringVar()
        self.text_input_pw = StringVar()

        frame_but = Frame(frame, bg="gray10")
        frame_but.pack(side=TOP)
        frame_but1 = Frame(frame, bg="gray10")
        frame_but1.pack(side=TOP)

        text_label = Label(
            frame_but, text="User ID", width=10, foreground="white", bg="gray10"
        )
        text_label.config(font=("Courier", 8))
        text_label.pack(side=LEFT)
        self.text[0] = Entry(
            frame_but, textvariable=self.text_input_uid, highlightcolor="white"
        )
        self.text[0].pack(expand=1, padx=10, pady=10, side=LEFT)

        text_label = Label(
            frame_but1, text="Password", width=10, foreground="white", bg="gray10"
        )
        text_label.pack(side=LEFT)
        text_label.config(font=("Courier", 8))
        self.text[1] = Entry(
            frame_but1,
            textvariable=self.text_input_pw,
            show="*",
            highlightcolor="white",
        )
        self.text[1].pack(expand=1, padx=10, pady=10, side=LEFT)

        bottomframe = Frame(frame, bg="gray10")
        bottomframe.pack(side=TOP, fill=X, expand=1, ipady=10)
        but = Button(bottomframe, text="Login", command=self.login)
        but.pack(side=LEFT, padx=20)
        but1 = Button(bottomframe, text="Register", command=self.register)
        but1.pack(side=RIGHT, padx=20)

        self.text_input_uid.trace(mode="w", callback=self.entryfocus)
        self.text_input_pw.trace(mode="w", callback=self.entryfocus1)
        self.canIclear = False

    def entryfocus(self, *args):
        if self.canIclear:
            self.text_input_uid.set("")
            self.canIclear = False
        self.text[0].config(bg="white")

    def entryfocus1(self, *args):
        if self.canIclear:
            self.text_input_pw.set("")
            self.canIclear = False
        self.text[1].config(bg="white")

    def login(self):
        name = self.text_input_uid.get()
        user_acc = self.text_input_uid.get() + "_" + self.text_input_pw.get()
        """
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(bytes(user_acc, 'utf-8'))
        encrypted_key = digest.finalize()
        """
        hashvalue = hashlib.sha256(user_acc.encode())
        encrypted_key = hashvalue.hexdigest()
        err = config.database.login_user(name, encrypted_key)
        if err == 0:
            self.text_input_uid.set("[DB] Incorrect login details. Try again.")
            self.canIclear = True
            self.text[0].config(bg="red")
            self.text[1].config(bg="red")
        elif err == 1:
            config.userid = name
            config.error.updateText(
                "[DB] Welcome: {}".format(config.userid), "pale green"
            )
            self.helpMenu.destroy()
            self.refresh()
        else:
            config.error.updateText(
                "[DB] Connection Timed out, try again", "red"
            )

    def register(self):
        name = self.text_input_uid.get()
        user_acc = self.text_input_uid.get() + "_" + self.text_input_pw.get()
        hashvalue = hashlib.sha256(user_acc.encode())
        encrypted_key = hashvalue.hexdigest()
        err = config.database.register_user(name, encrypted_key)
        if err == 0:
            self.text_input_uid.set("[DB] Username already taken.")
            self.canIclear = True
            self.text[0].config(bg="red")
        elif err == 1:
            config.userid = name
            config.error.updateText(
                "[DB] Account created: {}".format(config.userid),
                "pale green",
            )
            self.helpMenu.destroy()
            self.refresh()
        else:
            config.error.updateText(
                "[DB] Connection Timed out, try again", "red"
            )

        # encrypted_user_acc =

    def uploadDB(self, event=None):
        while True:
            if (
                config.error.updateText(
                    "Uploading, please wait...", "yellow"
                )
                == True
            ):
                break
        if self.session_name_set is False:
            if self.text_input[0].get() is "":
                config.error.updateText("Empty field not allowed!", "Red")
                return
            config.session_name = self.text_input[0].get()
            self.helpMenu.destroy()
        self.session_name_set = False
        config.error.updateText(
            "[DB] Created new session: " + str(config.session_name),
            "pale green",
        )
        config.local_disk = False
        # cfg.database.clearDB(cfg.session_name)
        if config.img is not None:
            config.img.save()
        # cfg.json_path = cfg.json_path + ".json"

        if config.map_canvas.floorplan_obj is None:
            config.no_floor_plan = True
        else:
            config.no_floor_plan = False

        imagegen()  # Generates template
        str1 = config.compile(
            config.json_folder, local_disk=False
        )
        self.updateText(str1 + "\n", "p")
        self.updateText(">>>" + "-" * 15 + "\n", "b")
        config.error.updateText("JSON Updated successfully", "pale green")
        self.refresh()

    def download(self):
        config.local_disk = True
        try:
            filename = filedialog.askopenfilename(
                initialdir=config.json_folder_config,
                title="Select File",
                filetypes=[("Json File", "*.json")],
            )
        except:
            config.error.updateText("Download failed", "red")
            return
        config.session_name = config.getbasename(filename)
        if config.node_controller.size:
            config.node_controller.deleteAllNodes()
        if config.image_flag:
            config.map_canvas.deleteImage()
        str1 = config.decompile(config.json_folder)
        self.updateText(str1 + "\n", "p")
        self.updateText(">>>" + "+" * 15 + "\n", "b")
