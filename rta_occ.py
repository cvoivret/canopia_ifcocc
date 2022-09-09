import ifcopenshell
#from ifcopenshell import geom
#from OCC.Display.SimpleGui import init_display
#import OCC

# Initialize a graphical display window (from ifcos)
ifcopenshell.geom.utils.initialize_display()
setting=ifcopenshell.geom.settings()

# setting OCC display 
#display, start_display, add_menu, add_function_to_menu = init_display()
 
# import ifc model
model= ifcopenshell.open('data/villa.ifc')


#extract windows
windows= model.by_type('IfcWindow')
win=windows[3]
shape=ifcopenshell.geom.create_shape(setting,win)
display_shape = ifcopenshell.geom.utils.display_shape(shape)




