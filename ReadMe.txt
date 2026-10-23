Aerospace Radiation Shielding Analysis Platform

Overview:
This repository houses an advanced numerical simulation orchestrator and graphical visualization dashboard built specifically for space radiation transport physics and satellite shielding design. By bridging a high performance C++ backend powered by the Geant4 toolkit with a responsive PyQt user interface, this platform enables comprehensive multi threaded analysis of energetic particle interactions across standard orbital environments.

Author and Contact Information:
Author: Piyush Pallav
Contact Email: ppallav2014@gmail.com

System Architecture:
The platform relies on a dual layer architecture where simulation execution and data visualization are decoupled for maximum stability and performance.

    C++ Backend Simulation Engine: Implemented in the source file cubesat_shield.cc, this core utilizes the Geant4 Monte Carlo toolkit and the FTFP_BERT physics list to simulate particle transport through nested shielding and payload geometries. It outputs numerical telemetry into structured data files including results.csv, tracks.csv, and secondaries.csv.

    Python Graphical Interface: Implemented in dashboard.py using PyQt5 and Matplotlib, this frontend orchestrates the compilation of the C++ engine via CMake, launches multi threaded simulation subprocesses, and renders interactive three dimensional particle tracks alongside analytical plots and Key Performance Indicator metrics.

Core Features and Capabilities:

    Mission Configuration Panel: Users can adjust orbital altitudes, select shielding materials such as aluminum, lead, water, polyethylene, tungsten, and gold, configure primary particle types, and define kinetic energies and simulation event counts.

    Real Time Three Dimensional Particle Tracking: Visualizes incoming particle beams, outer shielding boundaries, inner payload boxes, and secondary particle trajectories in a spatial coordinate system complete with custom coordinate vector layouts and descriptive legends.

    Dosimetry and Total Ionizing Dose Calculations: Computes payload penetration percentages, simulated dose values in Grays, estimated mission Total Ionizing Dose values in kRad scaled over mission lifespans, and overall shielding efficiency metrics.

    Advanced Analytical Spectra: Features a high resolution payload energy deposition spectrum histogram, a secondary particle yield distribution chart, and a cumulative dose versus depth profile curve.

    Secondary Particle Analytics Table: Aggregates secondary particles generated during radiation cascades, displaying particle names, total counts, average kinetic energies, payload impact counts, and individual dose contribution percentages.

    Reporting and Data Export: Allows engineers to export high resolution graphical plots in PNG and PDF formats alongside comprehensive summary reports in CSV format for further engineering evaluation.

Installation and Execution Instructions:

    Prerequisites: Ensure you have a working C++ compiler, CMake, Python 3, PyQt5, NumPy, Pandas, Matplotlib, and a fully configured installation of the Geant4 toolkit with environmental paths properly sourced on your operating system.

    Workspace Setup: Place cubesat_shield.cc and dashboard.py into your local project workspace directory.

    Launching the Dashboard: Execute the Python script in your terminal using the command python dashboard.py.

    Running Simulations: Configure your mission parameters within the left sidebar and click the Run Simulation button to compile the C++ backend automatically and render your analytical outputs.
