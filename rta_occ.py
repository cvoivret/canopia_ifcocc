import ifcopenshell
import ifcopenshell.geom

# due to some bugs in ipython parsing
__import__("logging").getLogger("parso.python.diff").setLevel("INFO")
__import__("logging").getLogger("parso.cache").setLevel("INFO")
__import__("logging").getLogger("asyncio").setLevel("INFO")


# Initialize a graphical display window (from ifcos)

setting=ifcopenshell.geom.settings()
setting.set(setting.USE_PYTHON_OPENCASCADE, True)

ifc_file= ifcopenshell.open('data/villa_2.ifc')

list= ifc_file.by_type('IfcWall')
w=list[0]
association=w.HasAssociations[0]

matinwall=set()
#for x in list:
#    print(x.HasAssociations[0].RelatingMaterial.Name)
#    matinwall.add(x.HasAssociations[0].RelatingMaterial.id())
    
listmat = ifc_file.by_type('IfcMaterial')
#for id in matinwall:
#    print(ifc_file.by_id(4071).AssociatedTo[0].RelatedObjects)


# exploration de la representation geometrique    
wl=ifc_file.by_type('IfcWindow')
w=wl[5]
wr=w.Representation # fenetre--> IfcProductDefintionShape
wsr=wr.Representations[0] # un product peut avoir plusieurs representation ( comment les choisir ?)
# wsr est de la classe IfcShapeRepresentation avec un representation_type = MappedRepresentation
# ça veut dire que la representation est utilisée par plusieurs objet dans le modele
# la geometrie n'est stockée qu'une fois dans le modele mais référencées plusieurs fois.
mappeditem=wsr.Items[0]
msource=mappeditem.MappingSource
mappedshape=msource.MappedRepresentation
items = mappedshape.Items
ids=[x.id() for x in mappedshape.Items]


# cherchons si un materiau et associé à chaque Id
listmat= ifc_file.by_type('IfcMaterial')
#listmatverre=[ mat if 'verre' in str.lower(mat.Name) for mat in listmat]
for mat in listmat:
    print(' mat name : ',mat.Name)
    #if 'verre' not in str.lower(mat.Name):
     #   continue
    associated =mat.AssociatedTo
    if len(associated)==0:
        continue
    relobj=associated[0].RelatedObjects
    idsmat=[x.id() for x in relobj]
    for idm in idsmat:
        for idgeom in ids:
            if idm==idm:
                print(' ', idgeom , ' seems related to material ', idm)



"""
wall = ifc_file.by_type('IfcWall')[0]
for definition in wall.IsDefinedBy:
    # To support IFC2X3, we need to filter our results.
    if definition.is_a('IfcRelDefinesByProperties'):
        property_set = definition.RelatingPropertyDefinition
        print(property_set.Name) # Might return Pset_WallCommon

for property in property_set.HasProperties:
    if property.is_a('IfcPropertySingleValue'):
        print(property.Name)
        print(property.NominalValue.wrappedValue)
"""
"""
products = ifc_file.by_type('IfcProduct')
for product in products:
    print(product.is_a())
"""
#etablir le mapping des materiaux utilise dans les objects
# extraire la geometrie de chaque materiaux instancie (verre notamment)


"""

# import ifc model
model= ifcopenshell.open('data/villa.ifc')


display=ifcopenshell.geom.utils.initialize_display()

#show walls
walls= model.by_type('IfcWall')
walls_shapes=[ ifcopenshell.geom.create_shape(setting, w).geometry for w in walls]
[ifcopenshell.geom.utils.display_shape(ws,viewer_handle=display) for ws in walls_shapes]
#display_shape = ifcopenshell.geom.utils.display_shape(shape,viewer_handle=display)

display.FitAll() 
ifcopenshell.geom.utils.main_loop()
"""

