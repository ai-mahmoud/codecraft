# F1 Intelligence Report (CodeCraft hackathon)

Analysis of Formula 1 results from 1950 to 2022, built for the CodeCraft data hackathon. The problem statement and data dictionary are included as PDFs.

## What's here

- **Data model:** a star schema with one fact table (`fact_Results`) and three dimensions (`dim_Drivers`, `dim_Races`, `dim_Circuits`), as raw and cleaned CSVs.
- **`f1_analysis.ipynb`:** cleaning (`\N` placeholders, types, joins) and exploratory analysis.
- **`steaming/steam.py`:** an interactive Streamlit dashboard with three views:
  - **Overview:** top drivers by points, points per season, and race completion vs DNF rate.
  - **Driver analysis:** points per season, finish-position distribution and a race-by-race log for any driver, plus a KPI comparison of the top 20.
  - **Circuits:** a world map of circuits and the circuits with the most DNFs.

## Run the dashboard

```sh
pip install streamlit pandas numpy plotly
cd steaming
streamlit run steam.py
```

**Built with:** Python, pandas, NumPy, Plotly, Streamlit, Jupyter
