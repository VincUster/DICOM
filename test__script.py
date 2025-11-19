import pydicom
import numpy as np

from tkinter import Tk, Canvas
from PIL import Image, ImageTk

# --- Load DICOM ---
dcm_path = '//supad12.spitaluster.ch/private$/HomeDrives/vescovi1/Documents/DICOM/-US-1-93.dcm'
dcm_file = pydicom.dcmread(dcm_path)
pixel_array = dcm_file.pixel_array.copy()  # work on a copy

# Assume shape (rows, cols, channels) or (rows, cols)
rows, cols = pixel_array.shape[:2]

# --- Prepare image for display (grayscale) ---
if pixel_array.ndim == 3:
    display_array = pixel_array[:, :, 0]
else:
    display_array = pixel_array

# normalize to 0–255 for display
disp = display_array.astype(np.float32)
disp -= disp.min()
if disp.max() > 0:
    disp /= disp.max()
disp = (disp * 255).astype(np.uint8)

pil_img = Image.fromarray(disp)

# --- Tkinter UI for rectangle selection ---
root = Tk()
root.title("Select an area (drag with left mouse button)")

canvas = Canvas(root, width=cols, height=rows)
canvas.pack()

tk_img = ImageTk.PhotoImage(pil_img)
canvas.create_image(0, 0, anchor="nw", image=tk_img)

start_x = start_y = 0
rect = None
final_coords = None  # (x1, y1, x2, y2)


def on_press(event):
    global start_x, start_y, rect
    start_x, start_y = event.x, event.y

    if rect:
        canvas.delete(rect)
    rect = canvas.create_rectangle(start_x, start_y, start_x, start_y,
                                   outline="red", width=2)


def on_drag(event):
    global rect
    # live update of rectangle
    canvas.coords(rect, start_x, start_y, event.x, event.y)


def on_release(event):
    global final_coords
    x1, y1 = start_x, start_y
    x2, y2 = event.x, event.y

    # normalize (x1 < x2, y1 < y2)
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))

    # clip to image bounds
    x1 = max(0, min(cols, x1))
    x2 = max(0, min(cols, x2))
    y1 = max(0, min(rows, y1))
    y2 = max(0, min(rows, y2))

    final_coords = (int(x1), int(y1), int(x2), int(y2))
    print("Selected area (x1, y1, x2, y2):", final_coords)


canvas.bind("<Button-1>", on_press)
canvas.bind("<B1-Motion>", on_drag)
canvas.bind("<ButtonRelease-1>", on_release)

root.mainloop()

print("Final stored coordinates:", final_coords)

# --- Apply selection to original pixel_array & save DICOM ---
if final_coords is not None:
    x1, y1, x2, y2 = final_coords

    # zero out selected region
    if pixel_array.ndim == 3:
        pixel_array[y1:y2, x1:x2, :] = 0
    else:
        pixel_array[y1:y2, x1:x2] = 0

    # make sure dtype matches what the DICOM expects
    pixel_array = np.asarray(pixel_array, dtype=dcm_file.pixel_array.dtype)

    # write back into the dataset
    dcm_file.PixelData = pixel_array.tobytes()

    dcm_file.save_as("output.dcm")
    print("Saved modified DICOM as output.dcm")
else:
    print("No area selected – DICOM not modified.")
