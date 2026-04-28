import pydicom
import numpy as np

filepath = 'I:/ICT/03_Applikationsmanagement/96_DICOM_Korrektur/20260428-154875/Patient Anonymized-drA\Fehlen/-US-1-12.dcm'

dcm = pydicom.dcmread(filepath)

frames = dcm.pixel_array