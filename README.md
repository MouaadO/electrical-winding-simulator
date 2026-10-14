# Electrical Machine Winding Simulator

I developed a Windows application to design and visualise multiphase AC-machine stator windings. It calculates winding factors, phase EMF, magnetomotive force and harmonics.

## Main features

- Generates single-layer and double-layer winding patterns from slot, pole and phase parameters.
- Draws stator layouts and winding connections.
- Calculates winding factors and visualizes phase EMF relationships.
- Evaluates MMF distributions and harmonics for selected current and winding settings.
- Exports calculation data to spreadsheets.

## Results

Figures from the [Winding of AC Machines report](docs/winding-of-ac-machines-report.pdf).

### Stator winding layout

A three-phase, 36-slot, five-pole-pair double-layer example.

![Three-phase 36-slot double-layer winding layout](docs/results/stator-winding.png)

### EMF phasors

The normalised phasors show the phase relationships for this winding.

![Normalized three-phase winding EMF phasors](docs/results/emf-phasors.png)

### Magnetomotive force

MMF profile for the three-phase, 12-slot, one-pole-pair double-layer example at an electrical angle of 90 degrees.

![Resultant MMF and phase contributions](docs/results/resultant-mmf.png)

## Download and open the app

**[Download Winding Simulator for Windows](https://github.com/MouaadO/electrical-winding-simulator/releases/latest/download/Winding_Simulator.exe)**

1. Download `Winding_Simulator.exe`.
2. Double-click the file to open the application.
3. Explore the Winding Simulator, Voltage Checker, and MMF and Harmonics tabs.

The application includes its runtime, so Python installation is not required.

## Tools used to build the app

Python, PyQt5, NumPy, pandas, Matplotlib, openpyxl and PyInstaller.

## Technical report

[Read Winding of AC Machines](docs/winding-of-ac-machines-report.pdf) for winding theory, worked examples, fractional-slot windings, MMF calculations and harmonic analysis.

Academic group project at the National Polytechnic School of Algiers.
