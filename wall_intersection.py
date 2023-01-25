from collections import defaultdict

import ifcopenshell
import ifcopenshell.geom

from OCC.Display.SimpleGui import init_display


from OCC.Extend.TopologyUtils import TopologyExplorer, WireExplorer
from OCC.Core.BRep import BRep_Tool
import OCC.Core.BOPTools as bpt
from OCC.Core.gp import gp_Pnt,gp_Dir,gp_Vec
from OCC.Core.Geom import Geom_Plane
import OCC.Core.BRepPrimAPI as brpapi

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakePrism
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepExtrema import BRepExtrema_ShapeProximity
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface

from OCC.Core.TopoDS import TopoDS_Face

from OCC.Core.BOPAlgo import BOPAlgo_MakerVolume,BOPAlgo_BOP,BOPAlgo_Operation,BOPAlgo_GlueEnum
from OCC.Core.BOPTools import BOPTools_AlgoTools_OrientFacesOnShell
from OCC.Core.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape,TopTools_MapOfShape

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.TopExp import topexp_MapShapes

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib


#from OCC.Core.TopoDS import Solid

#from OCC.Display.SimpleGui import init_display

#

# due to some bugs in ipython parsing
__import__("logging").getLogger("parso.python.diff").setLevel("INFO")
__import__("logging").getLogger("parso.cache").setLevel("INFO")
__import__("logging").getLogger("asyncio").setLevel("INFO")


# Initialize a graphical display window (from ifcos)

setting=ifcopenshell.geom.settings()
setting.set(setting.USE_PYTHON_OPENCASCADE, True)

#display=ifcopenshell.geom.utils.initialize_display()

ifc_file= ifcopenshell.open('data/office_ifcwiki.ifc')
#ifc_file= ifcopenshell.open('data/villa.ifc')

#opening_list=ifc_file.by_type('IfcOpeningElement')
#opening=opening_list[0]

walls=ifc_file.by_type('IfcWall')
roof=ifc_file.by_type('IfcRoof')
slab=ifc_file.by_type('IfcSlab')
spaces=ifc_file.by_type('IfcSpace')
windows=ifc_file.by_type('IfcWindow')
doors=ifc_file.by_type('IfcDoor')
opening=ifc_file.by_type('IfcOpeningElement')


building=walls+spaces+slab+opening#+doors#+roof+slab


buildingelementtype=['IfcBuildingElementProxy', 'IfcCovering', 'IfcBeam', 'IfcColumn', 'IfcCurtainWall', 
                     'IfcDoor', 'IfcMember', 'IfcRailing', 'IfcRamp', 'IfcRampFlight', 'IfcWall',
                     'IfcSlab', 'IfcStairFlight', 'IfcWindow', 'IfcStair', 'IfcRoof', 'IfcPile', 
                     'IfcFooting', 'IfcBuildingElementComponent', 'IfcPlate']
                     
                    
#building=ifc_file.by_type('IfcBuildingElement')
wall_shapes=[ifcopenshell.geom.create_shape(setting, w).geometry for w in walls if w.Representation is not None]
#rep=[el.Representation for el in building]
shapes=[ifcopenshell.geom.create_shape(setting, w).geometry for w in building if w.Representation is not None]
#wall_shapes=wall_shapes[:8]
#wall_shapes=[ifcopenshell.geom.occ_utils.yield_subshapes(w) for w in wall_shapes]


wallwindow=defaultdict(list)
for w in walls:
    
    for op in w.HasOpenings:
        #print('\n ***',w)
        #print('  ',op)
        for re in op.RelatedOpeningElement.HasFillings:
            #print('Related ', re.RelatedBuildingElement)
            if(re.RelatedBuildingElement.is_a()=='IfcWindow'):
                #print("++++++++   window ")
                
                wallwindow[w.id()].append(re.RelatedBuildingElement.id())

# get shapes as solid with possible conversion/extraction
lsolid=[]
for (i,w) in enumerate(shapes):
    #print('\n',i,' Roottype of shape  ', w)
    if w.ShapeType()==0: # CompoundType
        lshape=list(ifcopenshell.geom.occ_utils.yield_subshapes(w))
        #print('--- compound with nbchildren ', w.NbChildren())
        for (j,s) in enumerate(lshape):
            if s.ShapeType()==0:# compound
                
                lshape2=list(ifcopenshell.geom.occ_utils.yield_subshapes(s))
                shapetype=[s2.ShapeType() for s2 in lshape2]
                #print('--- number of shape in subcompound ', len(shapetype))
                if(shapetype==[2]):#unique solid
                    lsolid.append(lshape2[0])
                    continue
                if( (len(shapetype)>3) & (len(shapetype)<50)& (list(set(shapetype))==[4])):
                # Only faces and more than 3 (tetraedron)
                    #print('--- shape types in the compound :',[s2.ShapeType() for s2 in lshape2])
                    #print('--- ', i,' possible multiple shape ', lshape2)
                    sewer=BRepBuilderAPI_Sewing()
                    for sh in lshape2:
                        sewer.Add(sh)
                    sewer.Perform()
                    sewed=sewer.SewedShape()
                    #print('--- ',j,' ',sewed)
                    if(sewed.ShapeType()==0):
                        lshell=list(ifcopenshell.geom.occ_utils.yield_subshapes(sewed))
                        for shell in lshell:
                            lsolid.append(BRepBuilderAPI_MakeSolid(shell).Solid())
                        #print('--- ',j,' few sewed shape added ',s)
                    else:
                        solid=BRepBuilderAPI_MakeSolid(sewed).Solid()
                        lsolid.append(solid)
                        #print('--- ',j,' one sewed shape added ',s)
                else:
                    continue
                
            else:
                #print('--- ',i,' one added shape ',s)
                lsolid.append(s)


#unioning
args=TopTools_ListOfShape()
[args.Append(b) for b in lsolid[::2]]

tools=TopTools_ListOfShape()
[tools.Append(b) for b in lsolid[1::2]]
#print('args ',temp[::2])
#print('tool ',temp[1::2])

bop=BOPAlgo_BOP()
bop.SetOperation(BOPAlgo_Operation.BOPAlgo_FUSE)
bop.SetArguments(args)
bop.SetTools(tools)
bop.SetFuzzyValue(0.00001)
#bop.SetGlue(BOPAlgo_GlueEnum.BOPAlgo_GlueFull)

bop.Perform()
unionsolid=bop.Shape()
print(bop.DumpErrorsToString())


# TODO : cut below zero elevation (underground)
# and cut above the upper limit of space's upper storey
# --> limit size model if no opening are located on the roof


# Create the bounding box of the unioned model
box=Bnd_Box()
brepbndlib.Add(unionsolid,box)
boxshape=BRepPrimAPI_MakeBox(box.CornerMin(),box.CornerMax()).Shape()



#boolean difference between the unioned model and its bounding box
# 
diff=BOPAlgo_BOP()
diff.SetOperation(BOPAlgo_Operation.BOPAlgo_CUT)
diff.AddArgument(boxshape)
diff.AddTool(unionsolid)
diff.SetFuzzyValue(0.0001)
diff.Perform()
diffshape=diff.Shape()
print(bop.DumpErrorsToString())

# boolean common of shells : could be considered as the shell 
# separating interior and exterior of the building
"""
common=BOPAlgo_BOP()
common.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
common.AddArgument(diffshape)
common.AddTool(unionsolid)
common.SetFuzzyValue(0.0001)
common.Perform()
commonshape=common.Shape()
print(bop.DumpErrorsToString())
"""

top=TopologyExplorer(unionsolid)
unionshell = top.shells()


top=TopologyExplorer(diffshape)
diffshell = top.shells()

common=BOPAlgo_BOP()
common.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
args=TopTools_ListOfShape()
[args.Append(shell) for shell in unionshell]
tools=TopTools_ListOfShape()
[tools.Append(shell) for shell in diffshell]
common.SetArguments(args)
common.SetTools(tools)
common.SetFuzzyValue(0.0001)
common.Perform()
commonshell=common.Shape()
BOPTools_AlgoTools_OrientFacesOnShell(commonshell)
print(bop.DumpErrorsToString())



# Pour chaque mur contenant une fentre, identification de la normale,
# identification de la face de la fenetre colinéaire à la normale,
# extrusion de la fenetre selon la normale

wall_shapes=[ifcopenshell.geom.create_shape(setting, ifc_file.by_guid(w_id)).geometry 
                for w_id in wallwindow.keys() if ifc_file.by_guid(w_id).Representation 
                is not None]


glassface=[]


lshell=[]
lextru=[]
tools=TopTools_ListOfShape()
tools.Append(commonshell) 
common=BOPAlgo_BOP()
gpp=GProp_GProps()       
for (w_id,ws) in zip(wallwindow.keys(),wall_shapes):
    common.Clear()
    args=TopTools_ListOfShape()
    args.Append(ws)
    
    common.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
        
    common.SetArguments(args)
    common.SetTools(tools)
    
    common.SetFuzzyValue(0.0001)
    common.Perform()
    commonshell2=common.Shape()
    lshell.append(commonshell2)
    
    #print(list(ifcopenshell.geom.occ_utils.yield_subshapes(commonshell2)))
    #print(bop.DumpErrorsToString())
    
    # mur exterieur !!
    if commonshell2:
        faces=list(TopologyExplorer(commonshell2).faces())
        # en toute logique, une seule face doit être retournée
        if len(faces)>1:
            #print("   plusieurs faces !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # need sewing ???
            # all the faces have the same orientation
            print(len(faces))
            
        for f in faces[:1]:
            srf = BRep_Tool().Surface(f)
            #srf.D0(0,0, p)
            plane = Geom_Plane.DownCast(srf)
            face_norm = plane.Axis().Direction()
            #print("++++++++++ ",face_norm.Coord())
            #extruded = BRepPrimAPI_MakePrism(f,-face_norm,False).Shape()
            #lextru.append(extruded)
            #if(face_norm.IsEqual(swept_dir,0.01)):
            #    print('face found')
            #    #break
            windowshapes=[ifcopenshell.geom.create_shape(setting, ifc_file.by_guid(win_id)).geometry 
                for win_id in wallwindow[w_id]] 
            for i,winshape in enumerate(windowshapes):
                faceswin=list(TopologyExplorer(winshape).faces())
                #print(" nb face par fenetre ", len(faceswin))
                facelist=[]
                facearea=[]
                #facenormal=[]
                for fw in faceswin:
                    srf = BRep_Tool().Surface(fw)
                    plane2 = Geom_Plane.DownCast(srf)
                    face_norm2 = plane2.Axis().Direction()
                    #print(" face2 ",face_norm2.Coord())
                    if(face_norm2.IsEqual(face_norm,0.0001)):
                        #print(" face found for window ",i)
                        brepgprop_SurfaceProperties(fw,gpp)
                        #print(" area ", gpp.Mass())
                        facearea.append(gpp.Mass())
                        facelist.append(fw)
                        #facenormal.append(face_norm)
                maxarea=max(facearea)
                glassface.extend([ f for area,f in zip(facearea,facelist) if 
                            area>maxarea*.9] )
    

# extrusion of each window

# fusion of wall shapes
wall_fuser=BOPAlgo_BOP()
wall_fuser.SetOperation(BOPAlgo_Operation.BOPAlgo_FUSE)
los_walls1=TopTools_ListOfShape()
[los_walls1.Append(s) for s in wall_shapes[::2]]
los_walls2=TopTools_ListOfShape()
[los_walls2.Append(s) for s in wall_shapes[1::2]]
wall_fuser.SetArguments(los_walls1)
wall_fuser.SetTools(los_walls2)
wall_fuser.SetFuzzyValue(0.00001)
wall_fuser.Perform()
unioned_walls=wall_fuser.Shape()
print(bop.DumpErrorsToString())

los_walls=TopTools_ListOfShape()
#args.Append(unionsolid)
[los_walls.Append(s) for s in wall_shapes]
#lextru.clear()
lextru1=[]
lextru2=[]
linter=[]
lcut=[]
lgf=[]
to_compute=glassface[0:10]
for (i,gf) in enumerate(to_compute):
    print(i ,' / ',len(to_compute)) 
    lgf.append(gf)
    
    srf = BRep_Tool().Surface(gf)
    plane = Geom_Plane.DownCast(srf)
    face_norm = plane.Axis().Direction()
    #norm=BRepAdaptor_Surface(gf)
    face_norm.SetZ(-1) # automatic normalization
    ext_vec=gp_Vec(face_norm)
    ext_vec.Multiply(3)
    extrusion1=BRepPrimAPI_MakePrism(gf,-ext_vec,False,True).Shape()
    lextru1.append(extrusion1)
    
    
    inter=BOPAlgo_BOP()
    
    inter.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
    
    inter.AddTool(extrusion1) # only one tool 
    inter.AddArgument(unioned_walls)
    #inter.SetArguments(los_walls) # 
    
    #inter.SetFuzzyValue(0.00000001)
    #inter.SetNonDestructive(True)
    inter.Perform()
    intersection=inter.Shape()
    linter.append(intersection)

    
    
    intersection_faces=list(TopologyExplorer(intersection).faces())
    lfacetoextr=[]
    sewer=BRepBuilderAPI_Sewing()
    for ff in intersection_faces:
        srf3 = BRep_Tool().Surface(ff)
        plane3 = Geom_Plane.DownCast(srf3)
        face_norm3 = plane3.Axis().Direction()
        if(face_norm3.Dot(face_norm)<0.):
            sewer.Add(ff)
        
    sewer.Perform()
    sewed=sewer.SewedShape()
    
    
    ext2=BRepPrimAPI_MakePrism(sewed,ext_vec,False,True).Shape()
    lextru2.append(ext2)
    
    cut=BOPAlgo_BOP()
    cut.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
    cut.AddArgument(gf) ## qui coupe qui ? histoire de dimension ?
    cut.AddTool(ext2)
    
    
    cut.SetFuzzyValue(0.0001)
    cut.Perform()
    cutshape=cut.Shape()
    lcut.append(cutshape)
    #print('lcut ',lcut)
    
    
    
    

#display.DisplayShape(wall_shapes[7], transparency=0.5)


windowshapes=[ifcopenshell.geom.create_shape(setting, win).geometry for win in windows]


display, start_display, add_menu, add_function_to_menu = init_display()

#display
#display.DisplayShape(unioned_walls,transparency=0.98)
#display.DisplayShape(boxshape, transparency=0.5)
#display.DisplayShape(diffshape, transparency=0.5)
#display.DisplayShape(commonshell, transparency=0.5,color='BLUE')
#display.DisplayShape(commonshell2, transparency=0.5)
[display.DisplayShape(gf,color='YELLOW') for gf in lgf]
#[display.DisplayShape(w, transparency=0.9) for w in wall_shapes]
#[display.DisplayShape(shell) for shell in lshell]
[display.DisplayShape(extru,color='BLACK',transparency=0.95) for extru in lextru1]
[display.DisplayShape(extru,color='RED',transparency=0.9) for extru in lextru2]
#[display.DisplayShape(extru) for extru in lextru]
#[display.DisplayShape(w) for w in windowshapes]
[display.DisplayShape(intersection,transparency=0.5,color='GREEN') for intersection in linter]
#[display.DisplayShape(w, transparency=0.5) for w in wall_shapes]
[display.DisplayShape(x,color='BLACK') for x in lcut]


display.FitAll()
#ifcopenshell.geom.utils.main_loop()
start_display()






#windows=ifc_file.by_type('IfcWindow')
#doors = ifc_file.by_type('IfcDoor')

#temp=windows#+doors


"""
# test extrusion de chaque face de common (verification orientation normale)

lextru=[]
for f in faces:
    srf = BRep_Tool().Surface(f)
    #srf.D0(0,0, p)
    plane = Geom_Plane.DownCast(srf)
    face_norm = plane.Axis().Direction()
    #print(face_norm.Coord())
    extruded = BRepPrimAPI_MakePrism(f,-face_norm,False).Shape()
    lextru.append(extruded)
    #if(face_norm.IsEqual(swept_dir,0.01)):
    #    print('face found')
    #    #break
"""

"""
need to compute normal for external
	Handle(Geom_Surface) gSurface = BRep_Tool::Surface(face);
	Handle(Geom_ElementarySurface) aElementarySurface = Handle(Geom_ElementarySurface)::DownCast(gSurface);
	gp_Dir normal = aElementarySurface->Axis().Direction();
	if (face.Orientation() == TopAbs_REVERSED)
		return -normal;
"""

"""
for obj in temp:
    #replist=obj.Representation.Representations
    # get the body representation
    print('\n rep ',obj.Representation.Representations) 
    body = [obj for r in obj.Representation.Representations
                    if r.RepresentationIdentifier=='Body'][0]
    
    
    bodyrep=body.Representation.Representations[0]
    # only one body rep
    if bodyrep.RepresentationType=='MappedRepresentation':
        actual_rep = body.Representation.Representations[0].Items[0].MappingSource.MappedRepresentation
        print(' mapped by ', actual_rep)
        #print('origin ', body.Representation.Representations[0].Items[0].MappingSource.MappingOrigin.get_info())
    else :
        print(' direct ', bodyrep)
        
    #reptype = [t.RepresentationType for t in bodyrep]
    #print(reptype)
"""    
    

"""
for win in temp:
    print(win)
    if len(win.FillsVoids)==1:
        openingRep=win.FillsVoids[0].RelatingOpeningElement.Representation.Representations[0]
        print(openingRep.RepresentationType)
        if openingRep.RepresentationType=='Tessellation':
            #print('--- tessellation')
            shape=ifcopenshell.geom.create_shape(setting, openingRep)
            l=list(ifcopenshell.geom.occ_utils.yield_subshapes(shape))
            if l[0].ShapeType()==0:# compound
                lshape2=list(ifcopenshell.geom.occ_utils.yield_subshapes(l[0]))
            #print(lshape2)
        if openingRep.RepresentationType=='SweptSolid':
            #print('--- tessellation')
            direction=openingRep.Items[0]
           
           
            #else if opening.RepresentationType=='ff':
    #    print(' else')
  """      
