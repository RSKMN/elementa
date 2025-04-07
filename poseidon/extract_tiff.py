import os
import zipfile
import shutil
import numpy as np
import rasterio
import cv2
from tqdm import tqdm

# Configurations
ZIP_DIR = 'zips'            # Folder containing your zip files
TEMP_UNZIP_DIR = './temp_unzip'
OUTPUT_DIR = './water_patches'
PATCH_SIZE = 128
NDWI_THRESHOLD = 0.2
BATCH_SIZE = 3              # Process 3 .tif files at a time

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
if os.path.exists(TEMP_UNZIP_DIR):
    shutil.rmtree(TEMP_UNZIP_DIR)
os.makedirs(TEMP_UNZIP_DIR, exist_ok=True)

def calculate_ndwi(green, nir):
    return (green.astype(np.float32) - nir.astype(np.float32)) / (green + nir + 1e-5)

def extract_water_patches(tiff_path):
    print(f"[DEBUG] Processing TIFF: {tiff_path}")
    try:
        with rasterio.open(tiff_path) as src:
            # Check if there are at least 8 bands
            if src.count < 8:
                print(f"[!] Not enough bands in {tiff_path}. Skipping.")
                return
            green = src.read(3)
            nir = src.read(8)
            # Assume RGB from bands 4, 3, 2
            rgb = np.stack([src.read(4), src.read(3), src.read(2)], axis=-1)
    except Exception as e:
        print(f"[!] Error opening {tiff_path}: {e}")
        return

    ndwi = calculate_ndwi(green, nir)
    water_mask = ndwi > NDWI_THRESHOLD

    h, w = ndwi.shape
    patch_count = 0
    for y in range(0, h - PATCH_SIZE + 1, PATCH_SIZE):
        for x in range(0, w - PATCH_SIZE + 1, PATCH_SIZE):
            window = water_mask[y:y+PATCH_SIZE, x:x+PATCH_SIZE]
            if np.mean(window) > 0.5:
                patch = rgb[y:y+PATCH_SIZE, x:x+PATCH_SIZE, :]
                if patch.shape == (PATCH_SIZE, PATCH_SIZE, 3):
                    # Normalize patch to 0-255
                    patch = cv2.normalize(patch, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                    out_name = f"{os.path.splitext(os.path.basename(tiff_path))[0]}_{x}_{y}.jpg"
                    out_path = os.path.join(OUTPUT_DIR, out_name)
                    cv2.imwrite(out_path, patch)
                    patch_count += 1
    print(f"[DEBUG] Generated {patch_count} patches from {os.path.basename(tiff_path)}")

def process_zip_in_batches(zip_path):
    print(f"\n[DEBUG] Processing ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Get list of all TIFF files in the zip (using infolist)
        tif_members = [info.filename for info in zf.infolist() if info.filename.lower().endswith('.tif')]
        print(f"[DEBUG] Found {len(tif_members)} TIFF files in {os.path.basename(zip_path)}")
        
        # Process in batches of BATCH_SIZE TIFF files
        for i in range(0, len(tif_members), BATCH_SIZE):
            batch = tif_members[i:i+BATCH_SIZE]
            print(f"[DEBUG] Processing batch: {batch}")
            
            # Ensure TEMP_UNZIP_DIR is clean
            if os.path.exists(TEMP_UNZIP_DIR):
                shutil.rmtree(TEMP_UNZIP_DIR)
            os.makedirs(TEMP_UNZIP_DIR, exist_ok=True)
            
            # Extract only the files in the current batch
            for member in batch:
                try:
                    zf.extract(member, TEMP_UNZIP_DIR)
                    print(f"[DEBUG] Extracted {member}")
                except Exception as e:
                    print(f"[!] Error extracting {member}: {e}")
            
            # Process each extracted TIFF file
            for member in batch:
                tiff_path = os.path.join(TEMP_UNZIP_DIR, member)
                if os.path.exists(tiff_path):
                    extract_water_patches(tiff_path)
                    try:
                        os.remove(tiff_path)
                        print(f"[DEBUG] Deleted {tiff_path}")
                    except Exception as e:
                        print(f"[!] Could not delete {tiff_path}: {e}")
                else:
                    print(f"[!] File not found: {tiff_path}")
            
            # Cleanup TEMP_UNZIP_DIR for this batch
            if os.path.exists(TEMP_UNZIP_DIR):
                shutil.rmtree(TEMP_UNZIP_DIR)
                os.makedirs(TEMP_UNZIP_DIR, exist_ok=True)

def process_all_zips():
    zip_files = [f for f in os.listdir(ZIP_DIR) if f.lower().endswith('.zip')]
    print(f"[DEBUG] Total ZIP files in '{ZIP_DIR}': {len(zip_files)}")
    for zipf in tqdm(zip_files, desc="Processing ZIP files"):
        zip_path = os.path.join(ZIP_DIR, zipf)
        try:
            process_zip_in_batches(zip_path)
        except zipfile.BadZipFile:
            print(f"[!] Corrupt ZIP file: {zipf}")
            continue

if __name__ == "__main__":
    process_all_zips()
