import scihorizon_elab.simulation.entities as components
import os

xml_root = os.path.join(os.getenv("SCIHORIZON_ELAB_ROOT"), "simulation", "assets")

def get_object_list(xml_dir, all=True, seen=True):
    """
    Get all the xml files under the xml_dir
    Parameters:
      - xml_dir: the root dir to search for xml files
      - all: whether to return all the xml files
      - seen: if not return all the files, if True, return seen objects in traning set, else return unseen objects for unseen evaluation
    Return:
        a list of split paths of xml files
    """
    xml_paths = []
    subdirs = os.listdir(xml_dir)
    for subdir in subdirs:
        if subdir.endswith(".xml"):
            xml_paths.append(os.path.join(xml_dir, subdir))
        elif os.path.isdir(os.path.join(xml_dir, subdir)):
            xml_paths.extend(get_object_list(os.path.join(xml_dir, subdir)))
    if all: xml_paths = xml_paths
    else:
        if seen: xml_paths = xml_paths[:len(xml_paths)//2]
        else: xml_paths = xml_paths[len(xml_paths)//2:]
    split_xml_paths = [xml_path.split("assets/")[-1] for xml_path in xml_paths]
    return sorted(split_xml_paths)

name2class_xml = {
    # containers/receptacles
    "drawer": [components.ContainerWithDrawer, "obj/drawer/drawer.xml"],

    # chemistry objects
    "tube": [components.ChemistryTube, "obj/tube/tube.xml"],
    "chemistry_tube_stand": [components.TubeStand, "obj/tube_stand/tube_stand.xml"],
    "flask": [components.ChemistryContainer, "obj/flask/flask/flask.xml"],
    "centrifuge": [components.Container, "obj/centrifuge/centrifuge.xml"],

    # lab equipment
    "petri_dish": [components.ChemistryContainer, "obj/petri_dish/petri_dish/petri_dish/petri_dish.xml"],
    "petri_dish_lid": [components.CommonGraspedEntity, "obj/petri_dish_lid/petri_dish_lid/petri_dish_lid/petri_dish_lid.xml"],
    "bunsen_burner": [components.CommonGraspedEntity, "obj/bunsen_burner/7532be8f501d435194e3feec33a3addf/7532be8f501d435194e3feec33a3addf.xml"],

    # local GLB processed assets
    "pipettes_stand": [components.PipetteStand, "obj/pipettes_stand/pipettes_stand-ver-/pipettes_stand-ver-.xml"],
    "mechanical_pipette": [components.MechanicalPipette, "obj/mechanical_pipette/mechanical_pipette/mechanical_pipette.xml"],
    "table": [components.Container, "obj/table/table.xml"],
    "large_beaker": [components.ChemistryContainer, "obj/beaker_large/large_beaker/large_beaker.xml"],
    "small_beaker": [components.ChemistryContainer, "obj/beaker_small/small_beaker/small_beaker.xml"],
    "cylinder_small": [components.ChemistryContainer, "obj/cylinder_small/cylinder_small/cylinder_small/cylinder_small.xml"],
    "cylinder_mid": [components.ChemistryContainer, "obj/cylinder_mid/cylinder_mid/cylinder_mid/cylinder_mid.xml"],
    "cylinder_big": [components.ChemistryContainer, "obj/cylinder_large/cylinder_large/cylinder_large/cylinder_large.xml"],
    "cylinder_large": [components.ChemistryContainer, "obj/cylinder_large/cylinder_large/cylinder_large/cylinder_large.xml"],
    "glass_stirring_rod": [components.CommonGraspedEntity, "obj/glass_stirring_rod/glass_stirring_rod/glass_stirring_rod.xml"],

    "funnel": [components.CommonGraspedEntity, "obj/funnel/funnel.xml"],
    "hot_plate": [components.FlatContainer, "obj/hot_plate/hot_plate/hot_plate.xml"],
    "electronic_scale": [components.FlatContainer, "obj/electronic_scale/electronic_scale/electronic_scale.xml"],
    "aspirin_pill_bottle": [components.ContainerWithCap, "obj/aspirin_pill_bottle/aspirin_pill_bottle/aspirin_pill_bottle/aspirin_pill_bottle.xml"],
    "pill_bottle": [components.ContainerWithCap, "obj/pill_bottle/pill_bottle/pill_bottle/pill_bottle.xml"],
    "magnetic_stir_plate": [components.FlatContainer, "obj/magnetic_stir_plate/magnetic_stir_plate.xml"],
    "rag": [components.CommonGraspedEntity, "obj/rag/rag/rag.xml"],
    "water_bath": [components.WaterBathContainer, "obj/water_bath/water_bath/water_bath/water_bath.xml"],
    "chemistry_lab_table": [components.FlatContainer, "obj/chemistry_lab_table/chemistry_lab_table/chemistry_lab_table/chemistry_lab_table.xml"],
    "universal_support": [components.FlatContainer, "obj/universal_support/universal_support/universal_support/universal_support.xml"],
    "alcohol_lamp": [components.AlcoholLamp, "obj/alcohol_lamp/alcohol_lamp.xml"],
    "chemistry_tube": [components.ChemistryTube, "obj/chemistry_tube/chemistry_tube/chemistry_tube.xml"],
    "square_mat": [components.FlatContainer, "obj/square_mat/square_mat/square_mat/square_mat.xml"],
    "thermometer": [components.CommonGraspedEntity, "obj/thermometer/thermometer/thermometer.xml"],
    "heat_device": [components.HeatDevice, "obj/heat_device/heat_device/heat_device/heat_device.xml"],
    "drying_box": [components.DryingBox, "obj/drying_box/drying_box/drying_box/drying_box.xml"],
    "lab_table": [components.FlatContainer, "obj/lab_table/lab_table/lab_table/lab_table.xml"],
    "pipette": [components.Pipette, "obj/pipette/pipette/pipette_-_laboratory_essential_tool/pipette_-_laboratory_essential_tool.xml"],
    "conical_flask_small": [components.ChemistryContainer, "obj/conical_flask_small/conical_flask_small/conical_flask_small/conical_flask_small.xml"],
    "conical_flask_mid": [components.ChemistryContainer, "obj/conical_flask_mid/conical_flask_mid/conical_flask_mid/conical_flask_mid.xml"],
    "conical_flask_large": [components.ChemistryContainer, "obj/conical_flask_large/conical_flask_large/conical_flask_large/conical_flask_large.xml"],
    "tripod": [components.Container, "obj/tripod/tripod/tripod/tripod.xml"],
    "florence_flask": [components.ChemistryContainer, "obj/florence_flask/florence_flask/florence_flask/florence_flask.xml"],

}

additional_dict = {}
for key, value in name2class_xml.items():
    if value[-1] is None:
        continue
    if isinstance(value[1], list):
        additional_dict[key+"_seen"] = [value[0], value[1][:len(value[1])//2]]
        additional_dict[key+"_unseen"] = [value[0], value[1][len(value[1])//2:]]
    name2class_xml.update(additional_dict)