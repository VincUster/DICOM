import pydicom
import numpy as np

from tkinter import Tk, Canvas
from tkinter.filedialog import  askdirectory
from PIL import Image, ImageTk
import os
import promptlib
from pydicom.uid import ExplicitVRLittleEndian
from pydicom.uid import JPEG2000Lossless


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


root = Tk()
root.withdraw()
dcm_dir = askdirectory(title="Select a directory")
root.destroy()

out_dir = os.path.join(os.path.dirname(dcm_dir), 'anonymized')
os.makedirs(out_dir, exist_ok=True)

first_path = os.path.join(dcm_dir, os.listdir(dcm_dir)[0])

anonymizer = DicomAnonymizer(first_path)
coords = anonymizer.get_coordinates_to_anonymize()

print("Returned coords:", coords)

# Example of applying to all files once coords are chosen:
i = 0
if coords is not None:
    x1, y1, x2, y2 = coords

    for filename in os.listdir(dcm_dir):
        filepath = os.path.join(dcm_dir, filename)
        print(i)
        i+=1

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





        elif dcm_file.SOPClassUID == '1.2.840.10008.5.1.4.1.1.3.1':
            """
            orig_ts = dcm_file.file_meta.TransferSyntaxUID
            was_compressed = orig_ts.is_compressed

            if was_compressed:
                dcm_file.decompress()

               """ 
            frames = dcm_file.pixel_array.copy()
            

            # Mask only the pixel region
            if frames.ndim == 4:          # frames, rows, cols, samples
                frames[:, y1:y2, x1:x2, :] = 0
            elif frames.ndim == 3:        # frames, rows, cols
                frames[:, y1:y2, x1:x2] = 0
            elif frames.ndim == 2:        # single frame fallback
                frames[y1:y2, x1:x2] = 0
            else:
                raise ValueError(f"Unexpected pixel array shape: {frames.shape}")

            dcm_file.PixelData = frames.tobytes()

            # Keep metadata consistent
            dcm_file.Rows = frames.shape[-3] if frames.ndim == 4 else frames.shape[-2]
            dcm_file.Columns = frames.shape[-2] if frames.ndim == 4 else frames.shape[-1]

            # Recompress near original size
            """
            from pydicom.uid import JPEG2000
            if was_compressed:
                dcm_file.compress(JPEG2000, j2k_cr=[30])
            """

            out_path = os.path.join(out_dir, filename)
            dcm_file.save_as(out_path, write_like_original=False)

            print(f'{filename} ✅')

        else:
            print(f'{dcm_file.dcm_file.SOPClassUID}')


            

