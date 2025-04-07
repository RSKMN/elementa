import os
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import mapping
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class GreenCoverCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Green Cover Calculator")
        self.root.geometry("900x700")
        
        # Variables
        self.red_path = ""
        self.nir_path = ""
        self.boundary_path = ""
        self.ndvi_threshold = tk.DoubleVar(value=0.3)
        self.pixel_size = tk.DoubleVar(value=10.0)  # Default to Sentinel-2 resolution
        
        self.create_widgets()
    
    def create_widgets(self):
        # Create frames
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        input_frame = ttk.LabelFrame(top_frame, text="Input Data", padding=10)
        input_frame.pack(fill=tk.X, pady=5)
        
        param_frame = ttk.LabelFrame(top_frame, text="Parameters", padding=10)
        param_frame.pack(fill=tk.X, pady=5)
        
        button_frame = ttk.Frame(top_frame, padding=10)
        button_frame.pack(fill=tk.X, pady=5)
        
        result_frame = ttk.LabelFrame(self.root, text="Results", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Input widgets
        ttk.Label(input_frame, text="Red Band (B4):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Button(input_frame, text="Browse...", command=self.select_red_band).grid(row=0, column=1, padx=5, pady=2)
        self.red_label = ttk.Label(input_frame, text="No file selected")
        self.red_label.grid(row=0, column=2, sticky=tk.W, pady=2)
        
        ttk.Label(input_frame, text="NIR Band (B8):").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Button(input_frame, text="Browse...", command=self.select_nir_band).grid(row=1, column=1, padx=5, pady=2)
        self.nir_label = ttk.Label(input_frame, text="No file selected")
        self.nir_label.grid(row=1, column=2, sticky=tk.W, pady=2)
        
        ttk.Label(input_frame, text="Boundary File (Optional):").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Button(input_frame, text="Browse...", command=self.select_boundary).grid(row=2, column=1, padx=5, pady=2)
        self.boundary_label = ttk.Label(input_frame, text="No file selected")
        self.boundary_label.grid(row=2, column=2, sticky=tk.W, pady=2)
        
        # Parameter widgets
        ttk.Label(param_frame, text="NDVI Threshold:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Scale(param_frame, from_=0.0, to=1.0, variable=self.ndvi_threshold, orient=tk.HORIZONTAL, length=200).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(param_frame, textvariable=self.ndvi_threshold).grid(row=0, column=2, sticky=tk.W, pady=2)
        
        ttk.Label(param_frame, text="Pixel Size (meters):").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(param_frame, textvariable=self.pixel_size, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(param_frame, text="(10m for Sentinel-2, 30m for Landsat)").grid(row=1, column=2, sticky=tk.W, pady=2)
        
        # Buttons
        ttk.Button(button_frame, text="Calculate Green Cover", command=self.calculate_green_cover).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Results", command=self.save_results).pack(side=tk.LEFT, padx=5)
        
        # Results area (matplotlib)
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=result_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Results text
        self.results_text = tk.Text(result_frame, height=5, width=80)
        self.results_text.pack(fill=tk.X, pady=5)
        
        # Initialize plots
        self.ax1.set_title("Original Image (RGB)")
        self.ax1.axis('off')
        self.ax2.set_title("NDVI/Green Cover")
        self.ax2.axis('off')
        self.fig.tight_layout()
        self.canvas.draw()
    
    def select_red_band(self):
        filepath = filedialog.askopenfilename(
            title="Select Red Band (B4) GeoTIFF",
            filetypes=[("GeoTIFF files", "*.tif"), ("All files", "*.*")]
        )
        if filepath:
            self.red_path = filepath
            self.red_label.config(text=os.path.basename(filepath))

    def select_nir_band(self):
        filepath = filedialog.askopenfilename(
            title="Select NIR Band (B8) GeoTIFF",
            filetypes=[("GeoTIFF files", "*.tif"), ("All files", "*.*")]
        )
        if filepath:
            self.nir_path = filepath
            self.nir_label.config(text=os.path.basename(filepath))

    def select_boundary(self):
        filepath = filedialog.askopenfilename(
            title="Select Boundary Shapefile",
            filetypes=[("Shapefiles", "*.shp"), ("GeoJSON", "*.geojson"), ("All files", "*.*")]
        )   
        if filepath:
            self.boundary_path = filepath
            self.boundary_label.config(text=os.path.basename(filepath))

    def calculate_green_cover(self):
        if not self.red_path or not self.nir_path:
            messagebox.showerror("Error", "Please select both Red and NIR band files")
            return
    
        try:
            # Open raster files
            with rasterio.open(self.red_path) as red_src, rasterio.open(self.nir_path) as nir_src:
                red = red_src.read(1).astype('float32')
                nir = nir_src.read(1).astype('float32')
            
            # Check if files have same shape
                if red.shape != nir.shape:
                    messagebox.showerror("Error", "Red and NIR bands have different dimensions")
                    return
            
            # Create a meta profile for outputs
                meta = red_src.meta.copy()
            
            # Apply boundary mask if provided
                if self.boundary_path:
                    try:
                        # Read the boundary file
                        gdf = gpd.read_file(self.boundary_path)
                        if gdf.crs != red_src.crs:
                            gdf = gdf.to_crs(red_src.crs)
                    
                    # Create shapes list for mask
                        shapes = [mapping(geom) for geom in gdf.geometry]
                        red, red_transform = mask(red_src, shapes, crop=True, nodata=0)
                        red = red[0]
                        nir, nir_transform = mask(nir_src, shapes, crop=True, nodata=0)
                        nir = nir[0]
                    # Update metadata for cropped image (if needed)
                        meta.update({
                            "height": red.shape[0],
                            "width": red.shape[1],
                            "transform": red_transform
                        })
                    except Exception as e:
                        messagebox.showerror("Error", f"Error applying boundary mask: {str(e)}")
                        return
            
            # Calculate NDVI safely: avoid division by zero
                denominator = nir + red + 1e-6  # add a small number to avoid zero division
                ndvi = (nir - red) / denominator
            
            # Apply threshold to create green mask
                threshold = self.ndvi_threshold.get()
                green_mask = ndvi > threshold
            
            # Calculate green cover statistics
                total_pixels = np.sum(~np.isnan(ndvi))
                green_pixels = np.sum(green_mask)
                green_percentage = (green_pixels / total_pixels) * 100 if total_pixels > 0 else 0
            
            # Calculate area (using pixel size provided in meters)
                pixel_size = self.pixel_size.get()  # assume this is in meters
                total_area_sqkm = (total_pixels * pixel_size * pixel_size) / 1e6
                green_area_sqkm = (green_pixels * pixel_size * pixel_size) / 1e6
            
            # Display results in text area
                self.results_text.delete(1.0, tk.END)
                results = (
                    f"Green Cover Analysis Results:\n"
                    f"------------------------\n"
                    f"Total Area: {total_area_sqkm:.2f} sq km\n"
                    f"Green Area: {green_area_sqkm:.2f} sq km\n"
                    f"Green Coverage: {green_percentage:.2f}%\n"
                    f"NDVI Threshold Used: {threshold}\n"
                )
                self.results_text.insert(tk.END, results)
            
            # Prepare images for display (downsample if necessary)
            def downsample(image, max_dim=1024):
                # Downsample an image array to max_dim pixels in each dimension if it's larger
                import cv2
                height, width = image.shape
                scale = 1
                if max(height, width) > max_dim:
                    scale = max_dim / max(height, width)
                    new_size = (int(width * scale), int(height * scale))
                    image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
                return image
                        # Downsample for display only
                red_display = downsample(red)
                ndvi_display = downsample(ndvi)
            
            # Display RGB approximation using Red band (as grayscale)
                self.ax1.clear()
                self.ax1.imshow(red_display, cmap='gray')
                self.ax1.set_title("Red Band (Grayscale)")
                self.ax1.axis('off')
            
            # Display NDVI map
                self.ax2.clear()
                ndvi_img = self.ax2.imshow(ndvi_display, cmap='RdYlGn', vmin=-1, vmax=1)
                self.ax2.set_title(f"NDVI Map (Green > {threshold})")
                self.ax2.axis('off')
                plt.colorbar(ndvi_img, ax=self.ax2, fraction=0.046, pad=0.04)
            
                self.fig.tight_layout()
                self.canvas.draw()
            
            # Store results for saving
                self.results = {
                    'ndvi': ndvi,
                    'green_mask': green_mask,
                    'meta': meta,
                    'total_area_sqkm': total_area_sqkm,
                    'green_area_sqkm': green_area_sqkm,
                    'green_percentage': green_percentage
                }
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def save_results(self):
        if not hasattr(self, 'results'):
            messagebox.showerror("Error", "No results to save. Please calculate green cover first.")
            return
        
        # Select directory to save results
        save_dir = filedialog.askdirectory(title="Select Directory to Save Results")
        if not save_dir:
            return
        
        try:
            # Save NDVI raster
            ndvi_path = os.path.join(save_dir, "ndvi.tif")
            meta = self.results['meta'].copy()
            meta.update(dtype='float32', nodata=-9999)
            
            with rasterio.open(ndvi_path, 'w', **meta) as dst:
                dst.write(self.results['ndvi'].astype('float32'), 1)
            
            # Save green mask raster
            green_path = os.path.join(save_dir, "green_cover.tif")
            meta.update(dtype='uint8', nodata=0)
            
            with rasterio.open(green_path, 'w', **meta) as dst:
                dst.write(self.results['green_mask'].astype('uint8'), 1)
            
            # Save statistics as text
            stats_path = os.path.join(save_dir, "green_cover_stats.txt")
            with open(stats_path, 'w') as f:
                f.write(f"Green Cover Analysis Results\n")
                f.write(f"------------------------\n")
                f.write(f"Total Area: {self.results['total_area_sqkm']:.2f} sq km\n")
                f.write(f"Green Area: {self.results['green_area_sqkm']:.2f} sq km\n")
                f.write(f"Green Coverage: {self.results['green_percentage']:.2f}%\n")
                f.write(f"NDVI Threshold: {self.ndvi_threshold.get()}\n")
                f.write(f"Pixel Size: {self.pixel_size.get()} meters\n")
            
            # Save NDVI plot
            plot_path = os.path.join(save_dir, "ndvi_map.png")
            self.fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            
            messagebox.showinfo("Success", f"Results saved to {save_dir}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving results: {str(e)}")


def main():
    root = tk.Tk()
    app = GreenCoverCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main()