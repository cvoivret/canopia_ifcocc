from collections import defaultdict
import itertools
from array import array
import matplotlib.pyplot as plt

from joblib import Parallel
import multiprocessing

#import ifcopenshell
import ifcopenshell.geom

from ifcopenshell.geom import create_shape
from ifcopenshell.geom.occ_utils import yield_subshapes


from OCC.Display.SimpleGui import init_display


from OCC.Extend.TopologyUtils import TopologyExplorer, WireExplorer
from OCC.Core.BRep import BRep_Tool
import OCC.Core.BOPTools as bpt
from OCC.Core.gp import gp_Pnt,gp_Dir,gp_Vec,gp_Pln,gp_Lin,gp_Trsf
from OCC.Core.Geom import Geom_Plane
import OCC.Core.BRepPrimAPI as brpapi

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakePrism,BRepPrimAPI_MakeHalfSpace,BRepPrimAPI_MakeSphere
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepExtrema import BRepExtrema_ShapeProximity
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties,brepgprop_VolumeProperties
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomLProp import GeomLProp_SLProps
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepTools import breptools_UVBounds
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.Geom import Geom_Transformation,Geom_Line

from OCC.Core.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

from OCC.Core.TopoDS import TopoDS_Face
 
from OCC.Core.BOPAlgo import BOPAlgo_MakerVolume,BOPAlgo_BOP,BOPAlgo_Operation,BOPAlgo_GlueEnum
from OCC.Core.BOPTools import BOPTools_AlgoTools_OrientFacesOnShell
from OCC.Core.TopTools import TopTools_ListOfShape,TopTools_IndexedMapOfShape,TopTools_MapOfShape

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid,BRepBuilderAPI_MakeFace
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Section
from OCC.Core.TopExp import topexp_MapShapes
from OCC.Core.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_SHELL


from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib

import OCC.Core.ShapeFix as shapefix
import OCC.Core.ShapeBuild as shapebuild

from OCC.Core.IntCurvesFace import IntCurvesFace_ShapeIntersector

import OCC.Extend.TopologyUtils as utils

import numpy as np


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

def shapes_as_solids(lshape):
    lsolid=[]
     
    maps=TopTools_IndexedMapOfShape()
    for s in lshape:
        maps.Clear()
        topexp_MapShapes(s,TopAbs_SOLID,maps)
        if(maps.Size()>0):
            lsolid.extend([maps.FindKey(i) for i in range(1,maps.Size()+1)])
        else:
            maps.Clear()
            topexp_MapShapes(s,TopAbs_FACE,maps)
            sewer=BRepBuilderAPI_Sewing()
            [sewer.Add(maps.FindKey(i)) for i in range(1,maps.Size()+1)]
            sewer.Perform()
            sewed=sewer.SewedShape()
            if(sewed.ShapeType()==0):
                lshell=list(yield_subshapes(sewed))
                #print(len(lshell))
                for shell in lshell:
                    lsolid.append(BRepBuilderAPI_MakeSolid(shell).Solid())
            else:
                solid=BRepBuilderAPI_MakeSolid(sewed).Solid()
                lsolid.append(solid)
    return lsolid

def get_external_shell2(lshape):
       
    #unionize solids
    unionsolid=fuse_listOfShape(lsolid)
    
    # Create the bounding box of the unioned model
    box=Bnd_Box()
    brepbndlib.Add(unionsolid,box)
    box.Enlarge(1.) # to avoid parallel face of bbox with face model to be coplanar(
    # broke shell intersection 
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
    return commonshell
 
   
# put it in a class to store the intermediate results ?
def shadow_caster(sun_dir,building,theface,theface_norm,min_area = 1e-3):
    """
    sun_dir = one vector (downward direction)
    building = a solids that possibily make shadow on face
    face = a face to cast shadow on from building along sun_dir
    face_norm = pointing to the exterior of the face (outside)
    
    return  : a face with zero or positive area, None if no shadow
    
    """
    #print(theface_norm.Dot(sun_dir))
    # face not exposed to the sun
    if theface_norm.Dot(sun_dir)>-1e-5:
        #print('not exposed',flush=True)
        return theface# void face with zero area
    gpp=GProp_GProps()
    brepgprop_SurfaceProperties(theface,gpp)
    gf_area=gpp.Mass()
    
    ext_vec=gp_Vec(sun_dir)
    ext_vec.Multiply(10)
    
    # extrusion of 
    extrusion1=BRepPrimAPI_MakePrism(theface,-ext_vec,False,True).Shape()
    
    intersector=BOPAlgo_BOP()
    intersector.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
    intersector.AddTool(extrusion1) 
    intersector.AddArgument(building)
    intersector.Perform()
    intersection=intersector.Shape()
        
    intersection_faces=list(TopologyExplorer(intersection).faces())
               
    
    larea=[]
    lfaces=[]
    
    for ff in intersection_faces:
        srf3 = BRep_Tool().Surface(ff)
        umin,umax,vmin,vmax=breptools_UVBounds(ff)
        props=GeomLProp_SLProps(srf3,0.5*(umax-umin),0.5*(vmax-vmin),1,0.001)
        fn=props.Normal()
                
        if(ff.Orientation()==1):
            fn.Reverse()
        # avoid face nearly parallel with extrusion generatrix
        # ie face with normal perpendicular with extrusion direction
        if(fn.Dot(sun_dir)<-1e-5):
            brepgprop_SurfaceProperties(ff,gpp)
            larea.append(gpp.Mass())
            lfaces.append(ff)
    
    # relative or absolute minimal area
    # for large window, better to have absolute
    # face below 1cm2 ?
    large_faces=[ff  for ff,a in zip(lfaces,larea) if a/gf_area>min_area]
    #print(large_faces)
    # No faces casting shadows, return a void face
    if(len(large_faces)==0):
        return TopoDS_Face() # void face with zero area
    
    # transform a collection of faces into one shell
    sewer=BRepBuilderAPI_Sewing()
    [sewer.Add(f) for f in large_faces]
    sewer.Perform()
    sewed=sewer.SewedShape()
    
    # extrude back to theface
    extrusion2=BRepPrimAPI_MakePrism(sewed,ext_vec,False,True).Shape()
        
    # fusing multiple solid to acheive better results in the final BOP intersection 
    maps=TopTools_IndexedMapOfShape()
    topexp_MapShapes(extrusion2, TopAbs_SOLID, maps)
    los = TopTools_ListOfShape()
    [los.Append(maps.FindKey(i)) for i in range(1,maps.Size()+1)]
    
    maker=BOPAlgo_MakerVolume()
    maker.SetArguments(los)
    maker.Perform()
    extrusion2=maker.Shape()
    
    # intersection of second extrusion with theface          
    intersector.Clear()
    intersector.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
    intersector.AddArgument(theface) ## qui coupe qui ? histoire de dimension ?
    intersector.AddTool(extrusion2)
    intersector.SetFuzzyValue(1e-8)
    intersector.Perform()
    
    intersectionfaces=intersector.Shape()
    
    
    unify=ShapeUpgrade_UnifySameDomain(intersectionfaces)
    unify.Build()
    shadowface=unify.Shape()
    
    return shadowface

def shadow_caster_ray(sun_dir,building,theface,theface_norm,Nray=5):
 
    sphere_rad=0.05
    lshape=[]
        
    #discretize the face with Nray points
    srf = BRep_Tool().Surface(theface)
    umin,umax,vmin,vmax=breptools_UVBounds(theface)
    
    uoffset=0.5*(umax-umin)/Nray
    voffset=0.5*(vmax-vmin)/Nray
    
    uvalues,vvalues= np.meshgrid(np.linspace(umin+uoffset,umax-uoffset,Nray),
                                 np.linspace(vmin+voffset,vmax-voffset,Nray))
    
    # face not exposed to the sun
    if theface_norm.Dot(sun_dir)>-1.e-5:
        
        for u,v in zip(uvalues.flatten(),vvalues.flatten()):
            point=srf.Value(u,v)
            lshape.append(BRepPrimAPI_MakeSphere(point,sphere_rad).Shape())
        return np.ones(uvalues.shape),lshape# all points of discretization are in shadow
    
    
    shape_inter = IntCurvesFace_ShapeIntersector()
    shape_inter.Load(building, 1e-6)
    infinity=float("+inf")
    nbpoints=array('b')
    for u,v in zip(uvalues.flatten(),vvalues.flatten()):
        point=srf.Value(u,v)
        line=gp_Lin(point,-sun_dir)
        shape_inter.PerformNearest(line, 0.0,infinity)
        nbpoints.append(shape_inter.NbPnt())
        if(shape_inter.NbPnt()>0):
            lshape.append(BRepPrimAPI_MakeSphere(point,sphere_rad).Shape())
    
    #print(nbpoints)
    res=np.array(nbpoints).reshape(uvalues.shape)
    
    res[res>0.]=1
    return res,lshape
    #intersect line with the building
    # 
    # 
    # 
    # count non void intersections


def exterior_wall_normal(wallwindow,external_shell):
    
    wallnorm=dict()
    #shape of wall with a window
    wall_shapes=[create_shape(setting, ifc_file.by_guid(w_id)).geometry 
                    for w_id in wallwindow.keys() if ifc_file.by_guid(w_id).Representation 
                    is not None]

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
            #lface_wall.append(norm_map[wall_norm])
            #lface_wall.append(norm_map[wall_norm][0])
            first_wall_face =norm_map[wall_norm][0]
            srf = BRep_Tool().Surface(first_wall_face)
            plane = Geom_Plane.DownCast(srf)
            wall_norm = plane.Axis().Direction()
            if(first_wall_face.Orientation()==1):
                wall_norm.Reverse()
            wallnorm[w_id]=wall_norm
            
    return wallnorm

def biggestfaces_along_normal(wallwindow,wallnormal):
    glassface_bywindowid=defaultdict(list)
    gpp=GProp_GProps()    
    #print(" wall norm ", wall_norm.Coord())
    for w_id in wallwindow.keys():
        if (w_id in wallnorm.keys()):
            wall_norm=wallnormal[w_id]
        else:
            # window in interior wall
            continue
            
        for win_id in wallwindow[w_id]:
        
            windowshape=create_shape(setting, ifc_file.by_guid(win_id)).geometry
                            
            #lwin.append(windowshape)
            
            faceswin=list(TopologyExplorer(windowshape).faces())
            #print(" nb face par fenetre ", len(faceswin))
            facelist=[]
            facearea=[]
            #facenormal=[]
            for fw in faceswin:
                top=TopologyExplorer(fw)
                #print(top.number_of_wires())
                # face with some kind of hole
                if top.number_of_wires()>1:
                    continue
                srf = BRep_Tool().Surface(fw)
                plane2 = Geom_Plane.DownCast(srf)
                win_norm = plane2.Axis().Direction()
                if(fw.Orientation()==1):
                    win_norm.Reverse()
                
                
                if(win_norm.IsEqual(wall_norm,1e-6)):
                    #print(" face2 ",win_norm.Coord())
                   
                    brepgprop_SurfaceProperties(fw,gpp)
                    #print(" area ", gpp.Mass())
                    facearea.append(round(gpp.Mass(),5))
                    facelist.append(fw)
                    #facenormal.append(face_norm)
            #print('\n window ',i)
            
            maxarea=max(facearea)
            gfaces=[ f for area,f in zip(facearea,facelist) if 
                        area>maxarea*.9]
            #print([ f for area,f in zip(facearea,facelist) if 
            #            area>maxarea*.9])
            glassface_bywindowid[win_id].extend(gfaces)
            glassface.extend(gfaces)
        #glassface_bywindowid[win_id]=fuse_listOfShape(glassface_bywindowid[win_id])
    return glassface_bywindowid
 


def link_wall_window(ifcwalls):
    #link window and walls in plain python
    wallwindow=defaultdict(list)
    for wall in ifcwalls:
        
        for op in wall.HasOpenings:
            #print('\n ***',w)
            #print('  ',op)
            for re in op.RelatedOpeningElement.HasFillings:
                #print('Related ', re.RelatedBuildingElement)
                if(re.RelatedBuildingElement.is_a()=='IfcWindow'):
                    
                    wallwindow[wall.id()].append(re.RelatedBuildingElement.id())
    return wallwindow


class shadow_on_faces:
    """ simple container to hold computation results """
    def __init__(self,lfaces,lsun_dir):
        self._lfaces=lfaces
        self._lsun_dir=lsun_dir
        self._shadow_faces=[[] for i in range(len(self._lfaces))]
        

    def compute_shadow(self,exposed_building,min_area):
        for i,gf in enumerate(self._lfaces):
            # re computation of the face normal
            # shoudl be pointing outward
            srf = BRep_Tool().Surface(gf)
            plane = Geom_Plane.DownCast(srf)
            face_norm = plane.Axis().Direction()
            if(gf.Orientation()==1):
                face_norm.Reverse()
                
            for j,sun_dir in enumerate(self._lsun_dir):
                shadow_face=shadow_caster(sun_dir,exposed_building,gf,face_norm,1.e-3)
                self._shadow_faces[i].append(shadow_face)
                
        #print(' faces ',self._shadow_faces)
    
    def compute_area_and_ratio(self):
        gpp=GProp_GProps() 
        self._glass_area=0.0
        for gf in self._lfaces :
            brepgprop_SurfaceProperties(gf,gpp)
            self._glass_area+=gpp.Mass()
        
        self._shadow_area_vector=[]
        for vector_idx in range(len(self._lsun_dir)):
            area_sum=0.0           
            for face_idx in range(len(self._lfaces)):
                brepgprop_SurfaceProperties(self._shadow_faces[face_idx][vector_idx],gpp)
                area_sum+=gpp.Mass()
                
            self._shadow_area_vector.append(area_sum)
            
        self._ratio_vector=[ a/self._glass_area for a in self._shadow_area_vector]
        #print(' shadow area vector ',self._shadow_area_vector)
        print(' ratio vector ',self._ratio_vector)
        
    def compute_area_and_ratio_byunion(self):
        """ 
        could be simpler in terms of code but rely on robustness of OCC to compute on more
        complex configurations 
        
        """
        totalface=fuse_listOfShape(self._lfaces)
        gpp=GProp_GProps() 
        brepgprop_SurfaceProperties(totalface,gpp)
        totalarea=gpp.Mass()
        
        ratio=[]
        for vector_idx in range(len(self._lsun_dir)):
            lfaces=[]
            for face_idx in range(len(self._lfaces)):
                f=self._shadow_faces[face_idx][vector_idx]
                if not f.IsNull():
                    lfaces.append(f)
            totalshadow=fuse_listOfShape(lfaces)
            brepgprop_SurfaceProperties(totalshadow,gpp)
            shadowarea=gpp.Mass()
            ratio.append(shadowarea/totalarea)
        
        #print(' shadow area vector ',self._shadow_area_vector)
        print(' ratio vector by union',ratio)
        
        
    def compute_complementary_face(self):
        cutter=BOPAlgo_BOP()
        
        self._complementary_faces=[[] for i in range(len(self._lfaces))]
        
        gpp=GProp_GProps() 
        
        #larea=[]
        
        for vector_idx in range(len(self._lsun_dir)):
            #area=0.0           
            for face_idx in range(len(self._lfaces)): 
                shadow_face=self._shadow_faces[face_idx][vector_idx]
                glass_face=self._lfaces[face_idx]
                
                if not shadow_face.IsNull():
                    cutter.Clear()
                    cutter.SetOperation(BOPAlgo_Operation.BOPAlgo_CUT)
                    cutter.AddArgument(glass_face)
                    cutter.AddTool(shadow_face)
                    cutter.SetFuzzyValue(1e-6)
                    cutter.Perform()
                    complementary=cutter.Shape()
                    #print(' cutter ',complementary)
                            
                else :
                    
                    complementary=glass_face
                    
                
                self._complementary_faces[face_idx].append(complementary)
                
                #brepgprop_SurfaceProperties(complementary,gpp)
                #area+=gpp.Mass()
            #larea.append(area/self._glass_area)
        
                
        
        


# due to some bugs in ipython parsing
__import__("logging").getLogger("parso.python.diff").setLevel("INFO")
__import__("logging").getLogger("parso.cache").setLevel("INFO")
__import__("logging").getLogger("asyncio").setLevel("INFO")


# Initialize a graphical display window (from ifcos)

setting=ifcopenshell.geom.settings()
setting.set(setting.USE_PYTHON_OPENCASCADE, True)



#display=ifcopenshell.geom.utils.initialize_display()
#ifc_file= ifcopenshell.open('data/office_ifcwiki.ifc')
ifc_file= ifcopenshell.open('data/villa.ifc')
#ifc_file= ifcopenshell.open('data/Brise_soleils_divers.ifc')
#ifc_file= ifcopenshell.open('data/DCE_CDV_BAT.ifc')
#ifc_file= ifcopenshell.open('data/Test Project - Scenario 1.ifc')
#ifc_file= ifcopenshell.open('data/Test Project - Scenario 1_wallmod.ifc')
#ifc_file= ifcopenshell.open('data/Model_article_window.ifc')


ifcwalls=ifc_file.by_type('IfcWall')
roof=ifc_file.by_type('IfcRoof')
slab=ifc_file.by_type('IfcSlab')
spaces=ifc_file.by_type('IfcSpace')
windows=ifc_file.by_type('IfcWindow')
doors=ifc_file.by_type('IfcDoor')
opening=ifc_file.by_type('IfcOpeningElement')
storeys=ifc_file.by_type('IfcBuildingStorey')
proxys=ifc_file.by_type('IfcBuildingElementProxy')


# partial building to compute external shell and exterior wall
ifccorebuilding=ifcwalls+spaces#+slab
building_shapes_core=[create_shape(setting, x).geometry for x in ifccorebuilding if x.Representation is not None]
# OCC solids
lsolid_core=shapes_as_solids(building_shapes_core)



# complete building to compute shadow on
ifcextension= []+slab#+proxys
extensionshape = [create_shape(setting, x).geometry for x in ifcextension if x.Representation is not None]
extensionsolid=  shapes_as_solids(extensionshape)

ifcbuilding= ifccorebuilding + ifcextension
building_shapes= building_shapes_core + extensionshape
lsolid= lsolid_core + extensionsolid

ext_sh=get_external_shell2(lsolid_core)

# temporary global lists for display
glassface=[]
lface_wall=[]

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

wallwindow = link_wall_window(ifcwalls)

wallnorm = exterior_wall_normal(wallwindow,ext_sh)

glassface_bywindowid=biggestfaces_along_normal(wallwindow,wallnorm)

exposed_building=fuse_listOfShape(lsolid)

sun_dir=gp_Dir(-1,-2,-1)

npos=10
h_angles=np.arange(0,360.,360./npos)
#h_angles=[270.]
v_angles=70.
x=-np.cos(np.deg2rad(h_angles))
y=-np.sin(np.deg2rad(h_angles))
z=-np.sin(np.deg2rad(v_angles))
#z=np.sin(# from horizontal
l_sun_dir=[gp_Dir(xi,yi,z) for (xi,yi) in zip(x,y)]

#print(' Angles ', h_angles)

#l_sun_dir=[sun_dir]
      
        
                
        
lsof=[]
lparams=[]
for (k,win_id) in enumerate(glassface_bywindowid.keys()):
    lglassfaces=glassface_bywindowid[win_id]
    
    sof=shadow_on_faces(lglassfaces,l_sun_dir)
    sof.compute_shadow(exposed_building,1e-3)
    sof.compute_area_and_ratio()
    sof.compute_complementary_face()
    #sof.compute_area_and_ratio_byunion()
    lsof.append(sof)
       

display, start_display, add_menu, add_function_to_menu = init_display()
[display.DisplayShape(s,transparency=0.2) for s in building_shapes]
for sof in lsof:
    [display.DisplayShape(s,transparency=0.1,color='BLACK') for s in sof._shadow_faces]
    [display.DisplayShape(s,transparency=0.1,color='YELLOW') for s in sof._complementary_faces]

display.FitAll()
#ifcopenshell.geom.utils.main_loop()
start_display()


        
for sof in lsof:
        plt.plot(h_angles,sof._ratio_vector,'o-')
plt.show()


#shad=[shadow_caster(*p) for p in lparams]
lhits=[]
lspheres=[]


solid_sfa=[]
ray_sfa=[]
#valid for face scale only, not window scale
Nrays=[5]#,10,15,20,50,100]
"""
for N in Nrays:
    locsfa=[]
    for p in lparams:
        hits,spheres = shadow_caster_ray(*p[:-1],N)
        lhits.extend(hits)
        locsfa.append(hits.sum()/hits.size)
    ray_sfa.append(locsfa) 
        #lspheres.extend(spheres)
"""   


"""
# numpy !
solid=np.array(solid_sfa)
for lsfa,Nray in zip(ray_sfa,Nrays):
    temp=np.array(lsfa)
    plt.plot(solid,lsfa/solid,'o',label=Nray)
plt.legend()    
#plt.plot(solid)
plt.show()
"""
#res=[r/s for s,r in zip(solid_sfa,ray_sfa)]

#shad=Parallel(n_jobs=2, prefer="threads")(shadow_caster(*p) for p in lparams)



    
#a=np.array(list(results.values()))
#np.savetxt('results.txt',a)

#display.DisplayShape(wall_shapes[7], transparency=0.5)


#windowshapes=[ifcopenshell.geom.create_shape(setting, win).geometry for win in windows]

