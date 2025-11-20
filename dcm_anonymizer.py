import pydicom
import numpy as np

from tkinter import Tk, Canvas
from PIL import Image, ImageTk
import os


class DicomAnonymizer:
    def __init__(self, dcm_path):
        self.dcm_file = pydicom.dcmread(dcm_path)
        self.pixel_array = self.dcm_file.pixel_array.copy()
        self.rows, self.cols = self.pixel_array.shape[:2]

        self.start_x, self.start_y = None, None
        self.rect = None
        self.final_coords = None
        self.root = None
        self.canvas = None

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y

        # remove previous rectangle if there is one
        if self.rect:
            self.canvas.delete(self.rect)

        # create a new tiny rectangle (will be resized on drag)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red", width=2
        )

    def on_drag(self, event):
        # live update of rectangle
        if self.rect:
            self.canvas.coords(
                self.rect,
                self.start_x, self.start_y,
                event.x, event.y
            )

    def on_release(self, event):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        # normalize (x1 < x2, y1 < y2)
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))

        # clip to image bounds
        x1 = max(0, min(self.cols, x1))
        x2 = max(0, min(self.cols, x2))
        y1 = max(0, min(self.rows, y1))
        y2 = max(0, min(self.rows, y2))

        self.final_coords = (int(x1), int(y1), int(x2), int(y2))
        print("Selected area (x1, y1, x2, y2):", self.final_coords)

        # if you want to close the window after selection:
        self.root.destroy()

    def get_coordinates_to_anonymize(self):

        # --- Prepare image for display (grayscale) ---
        if self.pixel_array.ndim == 3:
            display_array = self.pixel_array[:, :, 0]
        else:
            display_array = self.pixel_array

        # normalize to 0–255 for display
        disp = display_array.astype(np.float32)
        disp -= disp.min()
        if disp.max() > 0:
            disp /= disp.max()
        disp = (disp * 255).astype(np.uint8)

        pil_img = Image.fromarray(disp)

        # --- Tkinter UI for rectangle selection ---
        self.root = Tk()
        self.root.title("Select an area (drag with left mouse button)")

        self.canvas = Canvas(self.root, width=self.cols, height=self.rows)
        self.canvas.pack()

        tk_img = ImageTk.PhotoImage(pil_img)
        self.canvas.create_image(0, 0, anchor="nw", image=tk_img)
        # keep reference so image is not garbage collected
        self.canvas.image = tk_img

        self.rect = None
        self.final_coords = None

        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.root.mainloop()

        print("Final stored coordinates:", self.final_coords)
        return self.final_coords


# --- usage ---

dcm_dir = '//supad12.spitaluster.ch/private$/HomeDrives/vescovi1/Documents/DICOM/DICOM-TEMP/Patient Anonymized-rDuKSMI/Schwangerschaft-Ultraschall-20251103-826'

out_dir = os.path.join(os.path.dirname(dcm_dir), 'anonymized')
os.makedirs(out_dir, exist_ok=True)

first_path = os.path.join(dcm_dir, os.listdir(dcm_dir)[0])

anonymizer = DicomAnonymizer(first_path)
coords = anonymizer.get_coordinates_to_anonymize()

print("Returned coords:", coords)

# Example of applying to all files once coords are chosen:

if coords is not None:
    x1, y1, x2, y2 = coords

    for filename in os.listdir(dcm_dir):
        filepath = os.path.join(dcm_dir, filename)

        dcm_file = pydicom.dcmread(filepath)

        if dcm_file.SOPClassUID == '1.2.840.10008.5.1.4.1.1.6.1':

            pixel_array = dcm_file.pixel_array.copy()  # work on a copy

            # zero out selected region
            if pixel_array.ndim == 3:
                pixel_array[y1:y2, x1:x2, :] = 0
            else:
                pixel_array[y1:y2, x1:x2] = 0

            pixel_array = np.asarray(pixel_array, dtype=dcm_file.pixel_array.dtype)
            dcm_file.PixelData = pixel_array.tobytes()

            out_path = os.path.join(out_dir, filename)
            dcm_file.save_as(out_path)
            print(f'{filename} ✅')

