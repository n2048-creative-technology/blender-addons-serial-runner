import bpy

from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, PointerProperty, EnumProperty
from bpy.types import Operator
import struct
import math
import threading
import time
import serial 
import serial.tools.list_ports
import zlib

# Function to get the list of available serial ports
def get_serial_ports(self, context):
    items = []
    ports = serial.tools.list_ports.comports()
    for port in ports:
        items.append((port.device, port.device, port.description))
    return items

class ScaleFactors:
    def __init__(self, x1,x2,x3,x4,x5,x6):
        self.x1 = x1
        self.x2 = x2
        self.x3 = x3
        self.x4 = x4
        self.x5 = x5
        self.x6 = x6
        
class SerialManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.ser = None
        self.selected_object = None
        self.scale_factors = None
        self.prev_data = None
        self.start_marker = b'<'
        self.end_marker = b'>'
        self.lock = threading.Lock()  # Create a lock
        
    def start(self, serial_port, selected_object, scale_factors):
        if not self.running:
            self.running = True
            self.prev_checksum = None; # so it sends the current position
            self.selected_object = selected_object
            self.scale_factors = scale_factors
            self.ser = serial.Serial(serial_port, 9600)

            time.sleep(2)
            
            self.thread = threading.Thread(target=self.run)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            
            with self.lock:  # Use lock to ensure thread-safe access
                if self.ser is not None and self.ser.is_open:
                    self.ser.close()

            if self.thread is not None:
                self.thread.join()

    def sendData(self):
        with self.lock:  # Use lock to ensure thread-safe access
            if not self.running:
                return

            loc = self.selected_object.location
            rot = self.selected_object.rotation_euler            
            data = struct.pack('6f', 
                loc.x * self.scale_factors.x1,
                loc.y * self.scale_factors.x2,
                loc.z * self.scale_factors.x3,
                math.degrees(rot.x) * self.scale_factors.x4,
                math.degrees(rot.y) * self.scale_factors.x5,
                math.degrees(rot.z) * self.scale_factors.x6
            )   
            checksum = zlib.crc32(data)  & 0xFFFFFFFF
            if checksum != self.prev_checksum: 
                message = self.start_marker + data + struct.pack('I', checksum) + self.end_marker
                self.ser.write(message)
                self.prev_checksum = checksum           

    def run(self):  
        try:
            while self.running:   
                if self.selected_object:
                    self.sendData()    
                    time.sleep(1.0 / bpy.context.scene.render.fps)

        except Exception as e:
            print(f"Error in thread: {e}")
            self.stop()


class RunButtonOperator(bpy.types.Operator):
    bl_idname = "object.run_button"
    bl_label = "Run Button"

    def execute(self, context):                    
        
        # Connect to selected serial Port
        serial_manager = context.scene.serial_manager
        serial_port = context.scene.serial_port
        selected_object = context.scene.selected_object
        
        scale_factors = ScaleFactors(
            context.scene.scale_factor_1,
            context.scene.scale_factor_2,
            context.scene.scale_factor_3,
            context.scene.scale_factor_4,
            context.scene.scale_factor_5,
            context.scene.scale_factor_6,
        )
        
        if selected_object:
            serial_manager.start(serial_port, selected_object, scale_factors)
            self.report({'INFO'}, "Running")
        else:
            self.report({'WARNING'}, "No object selected")
            
        # Toggle the button state
        context.scene.run_button_state = True         

        # bpy.ops.screen.animation_play()
            
        self.report({'INFO'}, "Running")
            
        return {'FINISHED'}


class StopButtonOperator(bpy.types.Operator):
    bl_idname = "object.stop_button"
    bl_label = "Stop Button"

    def execute(self, context):

        # Toggle the button state
        context.scene.run_button_state = False
        
        #bpy.ops.screen.animation_cancel()
        
        serial_manager = context.scene.serial_manager
        if serial_manager.running:
            serial_manager.stop()
            self.report({'INFO'}, "Stopped")
                            
        return {'FINISHED'}



class LayoutRABKPanel(bpy.types.Panel):
    bl_label = "RABK Automation Runner"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        
        layout = self.layout

        scene = context.scene

        # Create a simple row. 
        layout.label(text="Automation frames:")

        row = layout.row()
        row.prop(scene, "frame_start")
        row.prop(scene, "frame_end")        
                
        row = layout.row()
        row.prop_search(context.scene, "selected_object", context.scene, "objects")

        layout.label(text="Scale:")
        layout.prop(scene, "scale_factor_1", text="Scale factor 1")
        layout.prop(scene, "scale_factor_2", text="Scale factor 2")
        layout.prop(scene, "scale_factor_3", text="Scale factor 3")
        layout.prop(scene, "scale_factor_4", text="Scale factor 4")
        layout.prop(scene, "scale_factor_5", text="Scale factor 5")
        layout.prop(scene, "scale_factor_6", text="Scale factor 6")
        
        # Run animation on serial port
        layout.label(text="Run automation:")
        
        row = layout.row()
        # Dropdown menu to select serial port
        row.prop(context.scene, "serial_port", text="Port")


        row = layout.row()        
        row.scale_y = 3.0
        if context.scene.run_button_state == False:
            row.operator("object.run_button", text="Run")
        else:
            row.operator("object.stop_button", text="Stop")


def register(): 
    bpy.utils.register_class(RunButtonOperator)
    bpy.utils.register_class(StopButtonOperator)

    bpy.types.Scene.selected_object = PointerProperty(
        type=bpy.types.Object, 
        name="Automated Object"
    )

    bpy.types.Scene.scale_factor_1 = bpy.props.FloatProperty(
        name="scale factor 1",
        description="the ratio between the change in blender and the setpoint change of the motor",
        default=1.0,
        min=0.0
    )
    bpy.types.Scene.scale_factor_2 = bpy.props.FloatProperty(
        name="scale factor 2",
        description="the ratio between the change in blender and the setpoint change of the motor",
        default=1.0,
        min=0.0
    )
    bpy.types.Scene.scale_factor_3 = bpy.props.FloatProperty(
        name="scale factor 3",
        description="the ratio between the change in blender and the setpoint change of the motor",
        default=1.0,
        min=0.0
    )
    bpy.types.Scene.scale_factor_4 = bpy.props.FloatProperty(
        name="scale factor 4",
        description="the ratio between the change in blender and the setpoint change of the motor",
        default=1.0,
        min=0.0
    )
    bpy.types.Scene.scale_factor_5 = bpy.props.FloatProperty(
        name="scale factor 5",
        description="the ratio between the change in blender and the setpoint change of the motor",
        default=1.0,
        min=0.0
    )
    bpy.types.Scene.scale_factor_6 = bpy.props.FloatProperty(
        name="scale factor 6",
        description="the ratio between the change in blender and the setpoint change of the motor",
        default=1.0,
#        max=10.0,
        min=0.0
    )
    
    bpy.types.Scene.run_button_state = bpy.props.BoolProperty(
        default=False
    )
    
    # Add properties to the scene
    bpy.types.Scene.serial_port = bpy.props.EnumProperty(items=get_serial_ports, name="Port")

    bpy.types.Scene.serial_manager = SerialManager()

    bpy.utils.register_class(LayoutRABKPanel)
    
    
def unregister():    
    bpy.utils.unregister_class(LayoutRABKPanel)

    bpy.utils.unregister_class(RunButtonOperator)
    bpy.utils.unregister_class(StopButtonOperator)

    # Remove properties from the scene
    del bpy.types.Scene.selected_object
    
    del bpy.types.Scene.scale_factor_1
    del bpy.types.Scene.scale_factor_2
    del bpy.types.Scene.scale_factor_3
    del bpy.types.Scene.scale_factor_4
    del bpy.types.Scene.scale_factor_5
    del bpy.types.Scene.scale_factor_6
    
    del bpy.types.Scene.run_button_state   
     
    del bpy.types.Scene.serial_port
    del bpy.types.Scene.serial_manager

if __name__ == "__main__":
    register()   
    

