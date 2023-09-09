from fastapi import FastAPI, UploadFile, HTTPException
from pydicom import dcmread
import numpy as np
from scipy.ndimage import label
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for your frontend application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Adjust the origin as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_dicom(file: UploadFile, threshold: float = 0.5):
    try:
        # Read DICOM image
        dcm_data = dcmread(file.file)
        pixel_data = dcm_data.pixel_array.astype(float)

        # Normalize pixel data to [0, 1]
        normalized_data = (pixel_data - np.min(pixel_data)) / (np.max(pixel_data) - np.min(pixel_data))

        # Thresholding
        thresholded_data = normalized_data > threshold

        # Calculate volume in mm^3
        voxel_volume = float(dcm_data.SliceThickness) * float(dcm_data.PixelSpacing[0]) * float(dcm_data.PixelSpacing[1])
        labeled_data, num_features = label(thresholded_data)
        volume_mm3 = np.sum(labeled_data) * voxel_volume

        return {
            "success": True,
            "message": "Image processed successfully.",
            "data": {
                "volume_mm3": volume_mm3,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing DICOM: {str(e)}",
            "data": None,
        }

@app.post("/process")
async def process_dcm(file: UploadFile, threshold: float = 0.5):
    result = process_dicom(file, threshold)
    if result["success"]:
        return result["data"]
    else:
        raise HTTPException(status_code=500, detail=result["message"])

# curl "http://127.0.0.1:8000/process?filename=1-101.dcm&threshold=0.6"
# uvicorn untitled2:app --host 0.0.0.0 --port 5000 --reload