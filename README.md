# Electrical Machine Winding Simulator

A Python desktop application for visualizing multiphase stator windings and studying winding feasibility, voltage and magnetomotive-force harmonics. The interface combines winding diagrams, numerical calculations and plots.

## Tools used

Python 3, PyQt5, NumPy, pandas and Matplotlib. openpyxl supports spreadsheet exports; Pillow supports the icon utility. PyInstaller is optional for Windows packaging.

## How to run

1. Create and activate a Python virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. From this folder, run `python main.py`.
4. Explore the Winding Simulator, Voltage Checker, and MMF and Harmonics tabs.

Optional Windows packaging: install PyInstaller and run `pyinstaller winding_simulator.spec`. Packaging has not been revalidated; the existing executable is not included.

## Files

| File | Purpose |
| --- | --- |
| `main.py` | Desktop application entry point |
| `Winding_tab.py`, `StatorDrawing.py` | Winding controls and stator drawing |
| `winding_pattern_matrix.py`, `explanation.py` | Winding pattern and feasibility logic |
| `Voltage_tab.py` | Voltage analysis |
| `MMF_Harmonics_tab.py` | Active MMF/harmonics interface |
| `MMF_tab.py`, `mmf_calculation_engine.py` | Additional supplied MMF implementation |
| `requirements.txt` | Runtime dependencies |
| `winding_simulator.spec`, `version_info.txt` | Optional Windows build configuration |

## Limitations

The original virtual environment, build directories and executable were excluded. Dependencies are not pinned to a tested environment. Engineering results require independent verification for a specific machine design. The earlier build notes contained unverified distribution claims and were replaced by these instructions.

## Project context

Prepared from academic project files. Collaborative work remains team work; personal names are omitted from this public copy. Original technical comments and interfaces may be in French. No new license has been assigned.

## Verification status

All supplied Python files passed syntax parsing. Winding calculations passed shape and conductor-balance checks for 12-slot/2-pole and 36-slot/4-pole double-layer examples. The full GUI was not launched because PyQt5 is not installed in the review runtime. This does not establish full numerical correctness.
