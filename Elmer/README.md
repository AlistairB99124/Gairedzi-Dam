# Elmer curved dam starter model

This folder contains a first-pass workflow for a curved concrete dam based on the client data in the Data folder.

## What is included

- build_curved_dam_geometry.py: reads Data/Dam_Base_Contours.json and generates a simple curved centerline geometry plus a Gmsh .geo file.
- load_cases.json: stores the material properties, thickness, gravity, water level, overflow head, and boundary-condition assumptions.
- dam_model.sif: starter Elmer input template for a 3D structural model with gravity, hydrostatic pressure, and a rigid-bedrock base.

## Notes

- The geometry is a first-order surrogate because no drawing was provided.
- The flat segment in the middle of the profile is preserved as a horizontal plateau in the generated geometry.
- For a realistic cracking assessment, the starter model should later be upgraded to a nonlinear concrete damage material model rather than a simple elastic one.
