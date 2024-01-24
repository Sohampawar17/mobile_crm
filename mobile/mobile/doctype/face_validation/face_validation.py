# Copyright (c) 2024, Qunatbit and contributors
# For license information, please see license.txt
import face_recognition
import cv2
from datetime import datetime
from sklearn.cluster import DBSCAN
import frappe
from frappe.model.document import Document
import numpy as np
import os

def get_image_files(folder_path):
    image_files = []
    for file in os.listdir(folder_path):
        if file.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
            image_files.append(os.path.join(folder_path, file))
    return image_files

class FaceValidation(Document):
	def before_save(self):
            self.capture_and_compare_attendance()

    def mark_attendance(self, name, timestamp):
        frappe.msgprint(f"{name} - {timestamp}")
        

    def capture_and_compare_attendance(self):
        all_encodings = frappe.get_all("Face-Registration", fields=['name1'])

        known_face_encodings = []
        known_face_names = []

        folder_path = "/home/bubbles/frappe-bench/sites/face_recog.com/private/files"
        image_files = get_image_files(folder_path)

        for image in image_files:
            face_image = face_recognition.load_image_file(image)
            face_encodings = face_recognition.face_encodings(face_image)
            if face_encodings:
                known_face_encodings.append(face_encodings[0])

        for person in all_encodings:
            nam = person["name1"]
            known_face_names.append(nam)

        frame = cv2.imread(frappe.get_site_path('public', 'files', (str(self.image_input).split('/')[-1])))

        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for face_encoding in face_encodings:
            face_encoding = np.array(face_encoding)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.4)
            for i, match in enumerate(matches):
                if match:
                    name = known_face_names[i]
                    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.mark_attendance(name, current_date)
                    break
                else:
                    frappe.msgprint("No User")
                    break
