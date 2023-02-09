from collections import defaultdict

import ifcopenshell
import ifcopenshell.geom

from OCC.Display.SimpleGui import init_display


from OCC.Extend.TopologyUtils import TopologyExplorer, WireExplorer
from OCC.Core.BRep import BRep_Tool
import OCC.Core.BOPTools as bpt
from OCC.Core.gp import gp_Pnt,gp_Dir,gp_Vec,gp_Pln
from OCC.Core.Geom import Geom_Plane
import OCC.Core.BRepPrimAPI as brpapi

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakePrism,BRepPrimAPI_MakeHalfSpace
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepExtrema import BRepExtrema_ShapeProximity
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties,brepgprop_VolumeProperties
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomLProp import GeomLProp_SLProps
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepTools import breptools_UVBounds
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.Geom import Geom_Transformation

from OCC.Core.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

from OCC.Core.TopoDS import TopoDS_Face
 
from OCC.Core.BOPAlgo import BOPAlgo_MakerVolume,BOPAlgo_BOP,BOPAlgo_Operation,BOPAlgo_GlueEnum
from OCC.Core.BOPTools import BOPTools_AlgoTools_OrientFacesOnShell
from OCC.Core.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape,TopTools_MapOfShape

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid,BRepBuilderAPI_MakeFace
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Section
from OCC.Core.TopExp import topexp_MapShapes
from OCC.Core.TopAbs import TopAbs_SOLID


from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

import OCC.Core.ShapeFix as shapefix
import OCC.Core.ShapeBuild as shapebuild

import OCC.Extend.TopologyUtils as utils

import numpy as np


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

#ifc_file= ifcopenshell.open('data/office_ifcwiki.ifc')
#ifc_file= ifcopenshell.open('data/villa.ifc')
ifc_file= ifcopenshell.open('data/Brise_soleils_divers.ifc')

#ifc_file= ifcopenshell.open('data/DCE_CDV_BAT.ifc')

#ifc_file= ifcopenshell.open('data/Test Project - Scenario 1.ifc')
#ifc_file= ifcopenshell.open('data/Test Project - Scenario 1_wallmod.ifc')


#opening_list=ifc_file.by_type('IfcOpeningElement')
#opening=opening_list[0]

walls=ifc_file.by_type('IfcWall')
roof=ifc_file.by_type('IfcRoof')
slab=ifc_file.by_type('IfcSlab')
spaces=ifc_file.by_type('IfcSpace')
windows=ifc_file.by_type('IfcWindow')
doors=ifc_file.by_type('IfcDoor')
opening=ifc_file.by_type('IfcOpeningElement')
storeys=ifc_file.by_type('IfcBuildingStorey')
proxys=ifc_file.by_type('IfcBuildingElementProxy')

"""
storey_space=defaultdict(list)
[storey_space[s.Decomposes[0].RelatingObject].append(s) for s in spaces]
# if spaces are extruded, defined an average lower and upper limit
floor_ceiling=[]
for storey in storey_space.keys():
    depth=[]    
    for space in storey_space[storey]:
        print(space.Representation.Representations)
        rep =[ shaperep for shaperep in space.Representation.Representations 
                if ( shaperep. RepresentationIdentifier=='Body')
                & (shaperep. RepresentationType=='SweptSolid')]
        rep=rep[0]
        depth.append(rep.Items[0].Depth)
        print(rep.Items[0].Position.Location)
        #print(rep
    floor_ceiling.append( (storey.Elevation,
                            storey.Elevation+sum(depth)/len(depth)))
    print(floor_ceiling)
# the storeys should be in increasing order of Elevation
plane_position=gp_Pnt(0.0,0.0,floor_ceiling[0][0])
plane_dir=gp_Dir(0.0,0.0,-1.0)
lowerplane = gp_Pln(plane_position,plane_dir)
lowerface= BRepBuilderAPI_MakeFace(lowerplane).Shape()
plane_position.SetZ( floor_ceiling[0][0]-1.0)   
lowerhs= BRepPrimAPI_MakeHalfSpace(lowerface,plane_position).Shape()

plane_position=gp_Pnt(0.0,0.0,floor_ceiling[1][1])
plane_dir=gp_Dir(0.0,0.0,1.0)
upperplane = gp_Pln(plane_position,plane_dir)  
upperface= BRepBuilderAPI_MakeFace(upperplane).Shape()
plane_position.SetZ( floor_ceiling[1][1]+1.0)   
upperhs= BRepPrimAPI_MakeHalfSpace(upperface,plane_position).Shape()
  
"""




building=walls+spaces+slab#+opening#+doors#+roof+slab
#building=spaces


buildingelementtype=['IfcBuildingElementProxy', 'IfcCovering', 'IfcBeam', 'IfcColumn', 'IfcCurtainWall', 
                     'IfcDoor', 'IfcMember', 'IfcRailing', 'IfcRamp', 'IfcRampFlight', 'IfcWall',
                     'IfcSlab', 'IfcStairFlight', 'IfcWindow', 'IfcStair', 'IfcRoof', 'IfcPile', 
                     'IfcFooting', 'IfcBuildingElementComponent', 'IfcPlate']
lproxyshape=[ifcopenshell.geom.create_shape(setting, w).geometry for w in proxys if w.Representation is not None]                
solids=[]
maps=TopTools_IndexedMapOfShape()
for s in lproxyshape:
    topexp_MapShapes(s,TopAbs_SOLID,maps)
    solids.extend([maps.FindKey(i) for i in range(1,maps.Size()+1)])
#print(solids)
lproxyshape=solids
                    
#building=ifc_file.by_type('IfcBuildingElement')
wall_shapes=[ifcopenshell.geom.create_shape(setting, w).geometry for w in walls if w.Representation is not None]
#rep=[el.Representation for el in building]
shapes=[ifcopenshell.geom.create_shape(setting, w).geometry for w in building if w.Representation is not None]
#wall_shapes=wall_shapes[:8]
#wall_shapes=[ifcopenshell.geom.occ_utils.yield_subshapes(w) for w in wall_shapes]

"""
display, start_display, add_menu, add_function_to_menu = init_display()
[display.DisplayShape(s) for s in shapes]
display.FitAll()
start_display()
"""


# TODO : cut below zero elevation (underground)
# and cut above the upper limit of space's upper storey
# --> limit size model if no opening are located on the roof

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

"""
not working because of pointer and local variable, probably
def face_normal(face):
    srf = BRep_Tool().Surface(f)
    plane = Geom_Plane.DownCast(srf)
    fn = plane.Axis().Direction()
    if(f.Orientation()==1):
        return fn.Reverse()
    else:
        return fn
"""

def fuse_listOfShape(los,FuzzyValue=1e-6):
    
    
    fuser=BOPAlgo_BOP()
    fuser.SetOperation(BOPAlgo_Operation.BOPAlgo_FUSE)
    los_1=TopTools_ListOfShape()
    [los_1.Append(s) for s in los[::2]]
    los_2=TopTools_ListOfShape()
    [los_2.Append(s) for s in los[1::2]]
    fuser.SetArguments(los_1)
    fuser.SetTools(los_2)
    fuser.SetFuzzyValue(FuzzyValue)
    fuser.SetNonDestructive(True)
    fuser.Perform()
    return fuser.Shape()

def get_external_shell(building):
    """
    try to define the shell of external faces of a building
    building is a list of shape that represent the bulk of a building :
    walls+spaces+slab+opening
    """
    lsolid=[]
    for (i,wall) in enumerate(building):

        w=ifcopenshell.geom.create_shape(setting, wall).geometry
        rbody=[r for r in wall.Representation.Representations if r.RepresentationIdentifier=='Body']
        #print('\n', i,' representation body', [r.RepresentationType for r in rbody])
        #print(' Roottype of shape  ', w)
        topoex=utils.TopologyExplorer(w)
        #print(' topoex Solids ',[sol.this for sol in topoex.solids()])
        if w.ShapeType()==0: # CompoundType
            lshape=list(ifcopenshell.geom.occ_utils.yield_subshapes(w))
            #print('--- compound with nbchildren ', w.NbChildren())
            
            for (j,s) in enumerate(lshape):
                #print('---- in coumpound shapetype ',s.ShapeType())
                if s.ShapeType()==0:# compound
                    
                    lshape2=list(ifcopenshell.geom.occ_utils.yield_subshapes(s))
                    shapetype=[s2.ShapeType() for s2 in lshape2]
                    
                    #print('--- number of shape in subcompound ', len(shapetype))
                    #print('--- shapetype : ',shapetype)
                    if(shapetype==[2]):#unique shape and solid
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
                    
                elif s.ShapeType()==2: # solid type
                    #print('--- ',i,' one added shape ',s)
                    #print("++++++++++++++++++++++++++++++++++++++++")
                    
                    lsolid.append(s)
                    
                else:
                    #print("--- unmanaged shapetype")
                    scddsc



    #unioning of the bulk of the building (to find exteriro walls)
    
    unionsolid=fuse_listOfShape(lsolid)


    # Create the bounding box of the unioned model
    box=Bnd_Box()
    brepbndlib.Add(unionsolid,box)
    boxshape=BRepPrimAPI_MakeBox(box.CornerMin(),box.CornerMax()).Shape()



    #boolean difference between the unioned model and its bounding box
    diff=BOPAlgo_BOP()
    diff.SetOperation(BOPAlgo_Operation.BOPAlgo_CUT)
    diff.AddArgument(boxshape)
    diff.AddTool(unionsolid)
    diff.SetFuzzyValue(1e-5)
    diff.Perform()
    diffshape=diff.Shape()
    

    # boolean common of shells : could be considered as the shell 
    # separating interior and exterior of the building


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
    common.SetFuzzyValue(1e-5)
    common.Perform()
    commonshell=common.Shape()
    BOPTools_AlgoTools_OrientFacesOnShell(commonshell)
    return lsolid,commonshell
    
lsolid,external_shell=get_external_shell(building)




# Pour chaque mur contenant une fentre, identification de la normale,
# identification de la face de la fenetre colinéaire à la normale,
# extrusion de la fenetre selon la normale

wall_shapes=[ifcopenshell.geom.create_shape(setting, ifc_file.by_guid(w_id)).geometry 
                for w_id in wallwindow.keys() if ifc_file.by_guid(w_id).Representation 
                is not None]

glassface=[]
glassface_bywindowid=defaultdict(list)

lshell=[]
lextru=[]
lwin=[]
lface_wall=[]

tools=TopTools_ListOfShape()
tools.Append(external_shell) 

common=BOPAlgo_BOP()
gpp=GProp_GProps()   
    
for (w_id,ws) in zip(wallwindow.keys(),wall_shapes):
    common.Clear()
    args=TopTools_ListOfShape()
    args.Append(ws)
    
    common.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
        
    common.SetArguments(args)
    common.SetTools(tools)
    
    common.SetFuzzyValue(1e-6)
    common.Perform()
    commonshell2=common.Shape()
    lshell.append(commonshell2)
    
    #print(list(ifcopenshell.geom.occ_utils.yield_subshapes(commonshell2)))
    #print(bop.DumpErrorsToString())
    
    # mur exterieur !!
    if commonshell2:
        faces=list(TopologyExplorer(commonshell2).faces())
        norm_area=defaultdict(float)
        norm_map=defaultdict(list)
        for f in faces:
            srf = BRep_Tool().Surface(f)
            plane = Geom_Plane.DownCast(srf)
            fn = plane.Axis().Direction()
            if(f.Orientation()==1):
                fn.Reverse()
            face_norm_coord=fn.Coord()
            # maybe necessary to round...
            face_norm_coord = tuple(round(c,10) for c in face_norm_coord)
            brepgprop_SurfaceProperties(f,gpp)
            norm_area[face_norm_coord]+=gpp.Mass()
            norm_map[face_norm_coord].append(f)
        wall_norm = max(norm_area, key=norm_area.get)   
                
        #print(norm_area)
        #print(wall_norm)
        #print(norm_map[wall_norm])
                    
        # wall_norm is rounded but almost equal to all element in the list
        # taking the first
        lface_wall.append(norm_map[wall_norm])
        first_wall_face =norm_map[wall_norm][0]
        srf = BRep_Tool().Surface(first_wall_face)
        plane = Geom_Plane.DownCast(srf)
        wall_norm = plane.Axis().Direction()
        if(first_wall_face.Orientation()==1):
            wall_norm.Reverse()
        
        
        for win_id in wallwindow[w_id]:
        
            windowshape=ifcopenshell.geom.create_shape(setting, ifc_file.by_guid(win_id)).geometry
                
            #print("winwhapes ",windowshapes)
            #print("win window ",wallwindow[w_id])
                
            lwin.append(windowshape)
            
            faceswin=list(TopologyExplorer(windowshape).faces())
            #print(" nb face par fenetre ", len(faceswin))
            facelist=[]
            facearea=[]
            #facenormal=[]
            for fw in faceswin:
                top=TopologyExplorer(fw)
                #print(top.number_of_wires())
                if top.number_of_wires()>1:
                    continue
                srf = BRep_Tool().Surface(fw)
                plane2 = Geom_Plane.DownCast(srf)
                win_norm = plane2.Axis().Direction()
                if(fw.Orientation()==1):
                    win_norm.Reverse()
                
                #print(" face2 ",face_norm2.Coord())
                if(win_norm.IsEqual(wall_norm,1e-6)):
                    
                    #print(" face found for window ",i)
                    brepgprop_SurfaceProperties(fw,gpp)
                    #print(" area ", gpp.Mass())
                    facearea.append(round(gpp.Mass(),5))
                    facelist.append(fw)
                    #facenormal.append(face_norm)
            #print('\n window ',i)
            #print(facearea)
            maxarea=max(facearea)
            gfaces=[ f for area,f in zip(facearea,facelist) if 
                        area>maxarea*.9]
            #print([ f for area,f in zip(facearea,facelist) if 
            #            area>maxarea*.9])
            glassface_bywindowid[win_id].extend(gfaces)
            glassface.extend(gfaces)
    


# extrusion of each window

# fusion of wall shapes
#list_of_shape_to_fuse=wall_shapes



list_of_shape_to_fuse=lsolid + lproxyshape
unioned_walls=fuse_listOfShape(list_of_shape_to_fuse)

los_walls=TopTools_ListOfShape()
#args.Append(unionsolid)
[los_walls.Append(s) for s in list_of_shape_to_fuse]
#lextru.clear()
lextru1=[]
lextru2=[]
linter=[]
lsewed=[]
lcut=[]
lgf=[]
lsec=[]
lhs=[]
lshad=[]

sun_dir=gp_Dir(-1,-2,-1)

npos=5
x=np.cos(np.linspace(0,2*np.pi,npos))
y=np.sin(np.linspace(0,2*np.pi,npos))
l_sun_dir=[gp_Dir(xi,yi,-1) for (xi,yi) in zip(x,y)]
#l_sun_dir=[sun_dir]
results=defaultdict(list)

for (k,win_id) in enumerate(glassface_bywindowid.keys()):
    lglassfaces=glassface_bywindowid[win_id]
    print('\n window id ',win_id ,' ::  ',len(lglassfaces),flush=True) 
    lgf.append(lglassfaces)
          
    for i,gf in enumerate(lglassfaces):
        l_shadow_faces=[]
        brepgprop_SurfaceProperties(gf,gpp)
        gf_area=gpp.Mass()
        
        
        srf = BRep_Tool().Surface(gf)
        plane = Geom_Plane.DownCast(srf)
        face_norm = plane.Axis().Direction()
        if(gf.Orientation()==1):
            face_norm.Reverse()
        """
        # cut the building with halfspace to reduce the model
        umin,umax,vmin,vmax=breptools_UVBounds(gf)
        point=srf.Value(0.5*(umax-umin),0.5*(vmax-vmin))
        print('point ',point.Coord())
        point.Translate(gp_Vec(face_norm))
        print('point ',point.Coord())
        halfspace=BRepPrimAPI_MakeHalfSpace(gf,point).Solid()
        #lhs.append(halfspace)
        
        cutter=BOPAlgo_BOP()
        cutter.SetOperation(BOPAlgo_Operation.BOPAlgo_FUSE)
        cutter.AddArgument(halfspace)
        cutter.AddTool(unioned_walls)
        cutter.SetFuzzyValue(1e-8)
        cutter.Perform()
        print(cutter.DumpErrorsToString())
        print(cutter.DumpWarningsToString())
        cuttedshape=cutter.Shape()
        lhs.append(cuttedshape)
        """
        #exposed_building=cuttedshape
        exposed_building=unioned_walls
            
        for j,sun_dir in enumerate(l_sun_dir):
            counter=(j+1)*(k+1)
            print('--- win number   ',k,'/',len(glassface_bywindowid.keys()),flush=True)
            print('--- sun position ',j,'/',len(l_sun_dir),flush=True)
            print('--- ', counter,'/',len(l_sun_dir)*len(glassface_bywindowid.keys()),flush=True)
                                   
            
            if face_norm.Dot(sun_dir)>0.:
                print('   Not exposed',flush=True)
                l_shadow_faces.append(gf)
                continue
            
            ext_vec=gp_Vec(sun_dir)
            ext_vec.Multiply(3)
            extrusion1=BRepPrimAPI_MakePrism(gf,-ext_vec,False,True).Shape()
            lextru1.append(extrusion1)
            

            inter=BOPAlgo_BOP()
            inter.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
            inter.AddTool(extrusion1) # only one tool 
            inter.AddArgument(exposed_building)
            inter.Perform()
            intersection=inter.Shape()
            #intersection.
            
            top=TopologyExplorer(intersection)
            intershell = top.shells()
            # expected only one shell
            
            
            #linter.append(list(intershell)[0])
            linter.append(intersection)
        
            #intersection.Orientation(0)
            intersection_faces=list(TopologyExplorer(intersection).faces())
                        
            sewer=BRepBuilderAPI_Sewing()
            larea=[]
            lfaces=[]
            lcurve=[]
            for ff in intersection_faces:
                srf3 = BRep_Tool().Surface(ff)
                umin,umax,vmin,vmax=breptools_UVBounds(ff)
                props=GeomLProp_SLProps(srf3,0.5*(umax-umin),0.5*(vmax-vmin),1,0.001)
                fn=props.Normal()
                #print(" from geom ",fn2.Coord())
                #plane3 = Geom_Plane.DownCast(srf3)# a face can not be planar
                #fn = plane3.Axis().Direction()
                #print(" old school ",fn.Coord())
                
                if(ff.Orientation()==1):
                    fn.Reverse()
                
                if(fn.Dot(sun_dir)<-1e-5):# avoid face aligned with extrusion faces
                    brepgprop_SurfaceProperties(ff,gpp)
                    larea.append(gpp.Mass())
                    #lcurve.append(props.MeanCurvature())
                    #print(' curvemax ',props.MaxCurvature(),' curvemin ',props.MinCurvature(), 'mean ',props.MeanCurvature())
                    #print(' Area ',gpp.Mass(),' gaussiancurv ', props.GaussianCurvature())
                    
                    lfaces.append(ff)
            
            large_faces=[ff  for ff,a in zip(lfaces,larea) if a/gf_area>1e-2]
            
            if(len(large_faces)==0):
                l_shadow_faces.append(gf)
                lcut.append(gf)
                #print(" no
                continue
            
            [sewer.Add(f) for f in large_faces]
            
                
                        #sewer.Add(ff)
            
            #print('---area ',area)
            sewer.Perform()
            sewed=sewer.SewedShape()
            lsewed.append(sewed)
            
            ext2=BRepPrimAPI_MakePrism(sewed,ext_vec,False,True).Shape()
            
            lextru2.append(ext2)
            
            maps=TopTools_IndexedMapOfShape()
            

            topexp_MapShapes(ext2,TopAbs_SOLID,maps)
            
            list_of_shape_to_fuse=[maps.FindKey(i) for i in range(1,maps.Size()+1)]
            
            
            los = TopTools_ListOfShape()
            [los.Append(s) for s in list_of_shape_to_fuse] 
            mv=BOPAlgo_MakerVolume()
            mv.SetArguments(los)
            mv.Perform()
            unioned=mv.Shape()
            
                      
            cut=BOPAlgo_BOP()
            cut.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
            cut.AddArgument(gf) ## qui coupe qui ? histoire de dimension ?
            cut.AddTool(unioned)
            
            cut.SetFuzzyValue(1e-8)
            cut.Perform()
            #print(cut.DumpErrorsToString())
            #print(cut.DumpWarningsToString())
            cutshape=cut.Shape()
            
            if(cutshape.NbChildren()==0):
                l_shadow_faces.append(gf)
                lcut.append(gf)
                print(" null cuttttt")
                # print('---max area ',max(larea))
                # print('---min area ',min(larea))
                # print('---volume ',lvol)
                # print('---area ',larea)
                # print('---curve ',lcurve)
                continue
            
            lcut.append(cutshape)
            
            lcutted=list(ifcopenshell.geom.occ_utils.yield_subshapes(cutshape))
            #lshad.extend(lcutted)
            if lcutted[0].ShapeType()!=4:
                print(" PRoblemmmmmmmmm",flush=True)
            l_shadow_faces.append
            
            unify=ShapeUpgrade_UnifySameDomain(cutshape)
            unify.Build()
            uni=unify.Shape()
            
            lshad.append(uni)
            brepgprop_SurfaceProperties(uni,gpp)
            shadow_area=gpp.Mass()
            sfa = shadow_area/gf_area
            #print('     Shadow area ',shadow_area)
            #print('     Glass area ',glass_area)
            print('     SFA : ',sfa)
                    
            """
            shadow_area=0.0
            for f in l_shadow_faces:
                brepgprop_SurfaceProperties(f,gpp)
                shadow_area+=gpp.Mass()
                
            sfa = shadow_area/gf_area
            #print('     Shadow area ',shadow_area)
            #print('     Glass area ',glass_area)
            print('     SFA : ',sfa)
            results[win_id].append(sfa)
            """
    
    
#a=np.array(list(results.values()))
#np.savetxt('results.txt',a)

#display.DisplayShape(wall_shapes[7], transparency=0.5)


windowshapes=[ifcopenshell.geom.create_shape(setting, win).geometry for win in windows]


display, start_display, add_menu, add_function_to_menu = init_display()


#display.DisplayShape(cuttedunionsolid,transparency=0.5)

#display
[display.DisplayShape(s,transparency=0.5) for s in lproxyshape]
#display.DisplayShape(external_shell, transparency=0.9,color='BLUE')
#[display.DisplayShape(shell,transparency=0.9,color='RED') for shell in lshell]
[display.DisplayShape(shell,transparency=0.95,color='RED') for shell in lface_wall]
#[display.DisplayShape(gf,color='YELLOW') for gf in glassface]
#[display.DisplayShape(gf,color='RED',transparency=0.9) for gf in lwin]
#[display.DisplayShape(extru,color='BLACK',transparency=0.95) for extru in lextru1]
#[display.DisplayShape(extru,color='GREEN',transparency=0.9) for extru in linter]
[display.DisplayShape(extru,color='BLUE',transparency=0.1) for extru in lsewed]
#[display.DisplayShape(extru,color='RED',transparency=0.5) for extru in lextru2]
#[display.DisplayShape(extru,color='BLACK',transparency=0.5) for extru in lsec]

[display.DisplayShape(extru,color='BLACK',transparency=0.5) for extru in lhs]


#[display.DisplayShape(x,color='BLACK') for x in lcut]
[display.DisplayShape(x,color='BLACK') for x in lshad]
#display.DisplayShape(unionsolid,transparency=0.5)
#display.DisplayShape(boxshape, transparency=0.9)
#display.DisplayShape(diffshape, transparency=0.5)

"""
#display.DisplayShape(unionshell, transparency=0.5)
#display.DisplayShape(commonshell, transparency=0.5,color='BLUE')
#display.DisplayShape(commonshell2, transparency=0.5)
[display.DisplayShape(gf,color='YELLOW') for gf in lgf]
#[display.DisplayShape(w, transparency=0.9) for w in wall_shapes]


#[display.DisplayShape(extru) for extru in lextru]
#[display.DisplayShape(w) for w in windowshapes]
[display.DisplayShape(intersection,transparency=0.5,color='GREEN') for intersection in linter]
#[display.DisplayShape(w, transparency=0.5) for w in wall_shapes]
#
"""

display.FitAll()
#ifcopenshell.geom.utils.main_loop()
start_display()



