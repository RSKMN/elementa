import tkinter as tk
from tkinter import ttk, messagebox
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
from datetime import datetime, timedelta
import os
from PIL import Image, ImageTk
import numpy as np
from io import BytesIO
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api_keys import aqi as aqi_api


class AirQualityDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Air Quality Index Dashboard")
        self.root.geometry("1000x800")
        self.root.configure(bg="#f0f0f0")

        # Constants
        self.API_BASE_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
        self.API_KEY = aqi_api  # Replace with your data.gov.in key

        # Use CPCB categories for AQI
        self.aqi_categories = {
            'Good': (0, 50, '#8CD790', 'Minimal health impact'),
            'Satisfactory': (51, 100, '#A8E05F', 'Minor breathing discomfort to sensitive people'),
            'Moderate': (101, 200, '#FDD74B', 'Breathing discomfort to people with lung disease'),
            'Poor': (201, 300, '#FE9B57', 'Breathing discomfort to most people on prolonged exposure'),
            'Very Poor': (301, 400, '#FE6A69', 'Respiratory illness on prolonged exposure'),
            'Severe': (401, 500, '#A87383', 'Affects healthy people and seriously impacts those with existing diseases')
        }

        # Variables
        self.selected_city = tk.StringVar()
        self.city_list = self.get_city_list()

        # UI Setup
        self.setup_ui()

        # Initialize with default city
        if self.city_list:
            self.selected_city.set(self.city_list[0])
            self.get_air_quality_data()

    def setup_ui(self):
        # Main panels
        top_frame = ttk.Frame(self.root, padding="10 10 10 10")
        top_frame.pack(fill=tk.X)

        results_frame = ttk.Frame(self.root, padding="10 5 10 10")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # City selection
        ttk.Label(top_frame, text="Select City:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        city_dropdown = ttk.Combobox(
            top_frame,
            textvariable=self.selected_city,
            values=self.city_list,
            width=30,
            state="readonly"
        )
        city_dropdown.pack(side=tk.LEFT, padx=5)
        city_dropdown.bind("<<ComboboxSelected>>", lambda e: self.get_air_quality_data())

        refresh_button = ttk.Button(top_frame, text="Refresh Data", command=self.get_air_quality_data)
        refresh_button.pack(side=tk.LEFT, padx=10)

        # Create tab control
        self.tab_control = ttk.Notebook(results_frame)

        # Current AQI tab
        self.current_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.current_tab, text="Current AQI")

        # Historical Data tab
        self.historical_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.historical_tab, text="Historical Data")

        # Pollutant Breakdown tab
        self.pollutant_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.pollutant_tab, text="Pollutant Breakdown")

        # Health Impact tab
        self.health_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.health_tab, text="Health Impact")

        self.tab_control.pack(expand=1, fill=tk.BOTH)

        # Setup each tab content
        self.setup_current_tab()
        self.setup_historical_tab()
        self.setup_pollutant_tab()
        self.setup_health_tab()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_current_tab(self):
        # Left side - AQI display
        left_frame = ttk.Frame(self.current_tab, padding="10 20 10 10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Title label
        self.city_label = ttk.Label(left_frame, text="Loading...", font=("Arial", 24, "bold"))
        self.city_label.pack(pady=10)

        # Current datetime
        self.datetime_label = ttk.Label(left_frame, text="", font=("Arial", 12))
        self.datetime_label.pack(pady=5)

        # AQI Value and category in a frame
        aqi_frame = ttk.Frame(left_frame)
        aqi_frame.pack(pady=20)

        self.aqi_value_label = ttk.Label(aqi_frame, text="--", font=("Arial", 60, "bold"))
        self.aqi_value_label.pack()

        self.aqi_category_label = ttk.Label(aqi_frame, text="Loading...", font=("Arial", 16))
        self.aqi_category_label.pack(pady=5)

        # Air quality meter visual (will be a canvas)
        self.aqi_meter_canvas = tk.Canvas(left_frame, width=300, height=150, bg="#f0f0f0", highlightthickness=0)
        self.aqi_meter_canvas.pack(pady=10)

        # Right side - Station details
        right_frame = ttk.Frame(self.current_tab, padding="10 20 10 10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Title for station details
        ttk.Label(right_frame, text="Monitoring Stations", font=("Arial", 16, "bold")).pack(anchor=tk.W, pady=10)

        # Scrollable frame for stations
        stations_container = ttk.Frame(right_frame)
        stations_container.pack(fill=tk.BOTH, expand=True)

        # Canvas and scrollbar for stations
        stations_canvas = tk.Canvas(stations_container)
        scrollbar = ttk.Scrollbar(stations_container, orient="vertical", command=stations_canvas.yview)
        self.stations_frame = ttk.Frame(stations_canvas)

        self.stations_frame.bind(
            "<Configure>",
            lambda e: stations_canvas.configure(scrollregion=stations_canvas.bbox("all"))
        )

        stations_canvas.create_window((0, 0), window=self.stations_frame, anchor="nw")
        stations_canvas.configure(yscrollcommand=scrollbar.set)

        stations_container.pack(fill=tk.BOTH, expand=True)
        stations_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_historical_tab(self):
        # Title label
        ttk.Label(self.historical_tab, text="Historical AQI Data", font=("Arial", 16, "bold")).pack(pady=10)

        # Time range selection
        time_frame = ttk.Frame(self.historical_tab)
        time_frame.pack(fill=tk.X, pady=5)

        ttk.Label(time_frame, text="Time Range:").pack(side=tk.LEFT, padx=5)

        self.time_range = tk.StringVar(value="24h")

        for text, value in [("24 Hours", "24h"), ("7 Days", "7d"), ("30 Days", "30d")]:
            ttk.Radiobutton(
                time_frame,
                text=text,
                variable=self.time_range,
                value=value,
                command=self.update_historical_data
            ).pack(side=tk.LEFT, padx=10)

        # Graph frame
        self.historical_graph_frame = ttk.Frame(self.historical_tab)
        self.historical_graph_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # We'll create the actual plot when data is available
        self.historical_fig = plt.Figure(figsize=(9, 5), dpi=100)
        self.historical_ax = self.historical_fig.add_subplot(111)
        self.historical_canvas = FigureCanvasTkAgg(self.historical_fig, master=self.historical_graph_frame)
        self.historical_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def setup_pollutant_tab(self):
        # Title label
        ttk.Label(self.pollutant_tab, text="Pollutant Breakdown", font=("Arial", 16, "bold")).pack(pady=10)

        # Pollutant selection frame
        selection_frame = ttk.Frame(self.pollutant_tab)
        selection_frame.pack(fill=tk.X, pady=5)

        ttk.Label(selection_frame, text="Select Station:").pack(side=tk.LEFT, padx=5)

        self.station_var = tk.StringVar()
        self.station_dropdown = ttk.Combobox(
            selection_frame,
            textvariable=self.station_var,
            width=40,
            state="readonly"
        )
        self.station_dropdown.pack(side=tk.LEFT, padx=5)
        self.station_dropdown.bind("<<ComboboxSelected>>", self.update_pollutant_data)

        # Upper and lower frames for pollutant info
        upper_frame = ttk.Frame(self.pollutant_tab)
        upper_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Pollutant labels and values
        self.pollutant_frame = ttk.LabelFrame(upper_frame, text="Pollutants", padding="10")
        self.pollutant_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_health_tab(self):
        # Title label
        ttk.Label(self.health_tab, text="Health Impact", font=("Arial", 16, "bold")).pack(pady=10)

        # Display health guidelines based on AQI range
        self.health_impact_label = ttk.Label(self.health_tab, text="Select a city to view health impact", font=("Arial", 14))
        self.health_impact_label.pack(pady=10)

    def get_city_list(self):
        """
        Fetches the list of cities for the dropdown.
        """
        # Simulate a list of cities (replace this with actual API request if needed)
        return ['City1', 'City2', 'City3']

    def get_air_quality_data(self):
        """
        Fetches air quality data for the selected city from the API and updates the UI.
        """
        city = self.selected_city.get()
        self.city_label.config(text=city)
        self.datetime_label.config(text="Data updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Simulating API call and response (use real API call to fetch data)
        # Replace this block with actual API call code

        # Mock Data for testing
        aqi_value = 75
        category = "Satisfactory"
        stations = ["Station 1", "Station 2", "Station 3"]

        self.aqi_value_label.config(text=str(aqi_value))
        self.aqi_category_label.config(text=category)

        # Clear previous stations
        for widget in self.stations_frame.winfo_children():
            widget.destroy()

        # Display station data
        for station in stations:
            ttk.Label(self.stations_frame, text=station).pack(anchor=tk.W)

        # Update air quality meter visualization
        self.update_aqi_meter(aqi_value)

    def update_aqi_meter(self, aqi_value):
        """
        Updates the AQI meter based on the current AQI value.
        """
        # Clear the previous drawing
        self.aqi_meter_canvas.delete("all")
        
        # Define meter ranges for colors and categories
        for category, (min_val, max_val, color, description) in self.aqi_categories.items():
            if min_val <= aqi_value <= max_val:
                self.aqi_meter_canvas.create_oval(20, 20, 280, 130, fill=color, outline=color)  # Create circle
                self.aqi_meter_canvas.create_text(150, 75, text=category, font=("Arial", 14), fill="white")
                break

    def update_historical_data(self):
        """
        Updates the historical AQI data based on the selected time range.
        """
        # Simulate historical data fetch based on selected range
        range_selected = self.time_range.get()
        print(f"Fetching data for the last {range_selected}")
        
        # Here you would fetch the actual historical data and plot the graph
        # Mock graph data for demonstration
        dates = pd.date_range(datetime.now() - timedelta(days=7), periods=7)
        aqi_values = np.random.randint(50, 150, size=7)

        self.historical_ax.clear()
        self.historical_ax.plot(dates, aqi_values, label="AQI")
        self.historical_ax.set_title(f"Historical AQI - Last {range_selected}")
        self.historical_ax.set_xlabel("Date")
        self.historical_ax.set_ylabel("AQI")
        self.historical_canvas.draw()

    def update_pollutant_data(self, event=None):
        """
        Fetches and updates the pollutant data based on the selected station.
        """
        station = self.station_var.get()
        print(f"Fetching pollutant data for {station}")
        
        # Simulate pollutant data update (Replace with actual API data)
        pollutant_data = {
            'PM2.5': 35,
            'PM10': 45,
            'CO': 0.5,
            'NO2': 30
        }
        
        # Clear previous pollutant data
        for widget in self.pollutant_frame.winfo_children():
            widget.destroy()

        # Display new pollutant data
        for pollutant, value in pollutant_data.items():
            ttk.Label(self.pollutant_frame, text=f"{pollutant}: {value} µg/m³").pack(anchor=tk.W)

if __name__ == "__main__":
    root = tk.Tk()
    app = AirQualityDashboard(root)
    root.mainloop()
