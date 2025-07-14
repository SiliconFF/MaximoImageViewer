import requests
import json
import os
import cv2
import numpy as np
import time

DEBUG_ENABLED = False

credentials_file = json.loads('./creds.json')
API_BASE_URL = credentials_file['mvi-endpoint']
AUTH_TOKEN = credentials_file['mvi-key']


def get_random_bgr_colors():

    # Generate random integers for B, G, and R channels (0-255)
    b = np.random.randint(50, 256)
    g = np.random.randint(50, 256)
    r = np.random.randint(50, 256)
    return (b, g, r)


def create_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        if DEBUG_ENABLED:
            print(f"Folder '{folder_name}' created successfully.")
    else:
        if DEBUG_ENABLED:
            print(f"Folder '{folder_name}' already exists.")

def add_bounding_box(image_data, bounding_boxes, result = None):

    if bounding_boxes == {}:
        return image_data
     
    labels_list = bounding_boxes['labels']

    img_array = np.frombuffer(image_data, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    detected_labels = {}


    for label in labels_list:
        current_object_name = label['name']
        if current_object_name not in detected_labels:
            detected_labels[current_object_name] = get_random_bgr_colors()
        
       
        #Get polygons from the file
        try:
            polygon_points = np.array(label['segment_polygons'][0], np.int32)
        except KeyError:
            box = label['bndbox']
            xmax = box['xmax']
            xmin = box['xmin']
            ymin = box['ymin']
            ymax = box['ymax']
            arr = [(xmax,ymax),(xmax,ymin),(xmin,ymin),(xmin,ymax)]
            polygon_points = np.array(arr,np.int32)

        
        
        polygon_points = polygon_points.reshape((-1, 1, 2))  # Reshape for cv2.polylines

        color = detected_labels[current_object_name]  # Green color in BGR
        thickness = 2  # Line thickness
        cv2.polylines(img, [polygon_points], isClosed=True, color=color, thickness=thickness)



 
    height, width = img.shape[:2]


    # Define color key properties
    rect_size = (50, 50)  # Size of the color swatch (width, height)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2
    text_color = (255, 255, 255)  # White text for contrast
    thickness = 2
    vertical_spacing = 60  # Space between swatches vertically
    start_position = (10, height - 10)  # Starting position (bottom-left with padding)

    # Iterate through the dictionary to draw color key
    for i, (object_name, key_color) in enumerate(detected_labels.items()):
        # Calculate position for this swatch (stack vertically upwards)
        key_position = (start_position[0], start_position[1] - i * vertical_spacing)
        
        # Draw a filled rectangle (color swatch)
        top_left = (key_position[0], key_position[1] - rect_size[1])
        bottom_right = (key_position[0] + rect_size[0], key_position[1])
        cv2.rectangle(img, top_left, bottom_right, key_color, -1)  # -1 for filled

        # Add text next to the rectangle
        text_org = (key_position[0] + rect_size[0] + 5, key_position[1])  # Slightly offset to the right
        cv2.putText(img, object_name, text_org, font, font_scale, text_color, thickness, cv2.LINE_AA)

    # Define the text to display
    text = f"Result: {result}"

    # Define text properties
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (255, 255, 255)  # White text (BGR format)
    thickness = 2
    bg_color = (0, 0, 0)     # Black background for text

    # Get text size to calculate background rectangle
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)

    # Define top-right position (10 pixels from top and right edges)
    margin = 10
    position = (img.shape[1] - text_width - margin, text_height + margin)

    # Draw a filled rectangle as text background
    cv2.rectangle(
        img,
        (position[0] - margin, position[1] - text_height - margin),
        (position[0] + text_width + margin, position[1] + margin),
        bg_color,
        -1  # Filled rectangle
    )

    # Draw the text
    cv2.putText(img, text, position, font, font_scale, color, thickness)

    success, encoded_img = cv2.imencode(".jpg", img)
    if not success:
        raise ValueError("Failed to encode the image")
    modified_byte_array = encoded_img.tobytes()
    return modified_byte_array

def save_image_with_labels(image_data, bounding_boxes, file_path, meta_data):
    if not os.path.exists(file_path):
        try:
            results = metadata['ruleType']
        except:
            results = ""

        image_with_bounds = add_bounding_box(image_data, bounding_boxes, results)
        with open(file_path, "wb") as file:
            file.write(image_with_bounds)
        if DEBUG_ENABLED:
            print(f"File '{file_path}' created successfully.")
    else:
        if DEBUG_ENABLED:
            print(f"File '{file_path}' already exists.")


headers = {
    "X-Auth-Token": AUTH_TOKEN
    }

while (True):
    dataset_list_raw = requests.get(f"{API_BASE_URL}/datasets", headers=headers)
    dataset_list = json.loads(dataset_list_raw.text)
    dataset_list_inspecting = [dataset for dataset in dataset_list if dataset.get("purpose") == "inspection"]

    # List of tuples with (id, name)
    id_name_pairs = [(item["_id"], item["name"]) for item in dataset_list_inspecting] # List comprehension to get all _id values with names

    headers = {"X-Auth-Token": AUTH_TOKEN}

    params = {
            "limit": "5",
            "sortby": "created_at DESC"
            }

    for id in id_name_pairs:
        directory = "Inspections/"+id[1]
        create_folder(directory)
        dataset_list_raw = requests.get(f"{API_BASE_URL}/datasets/{id[0]}/files", headers=headers, params=params)
        dataset_list = json.loads(dataset_list_raw.text)

        for image in dataset_list:
            url = f"{API_BASE_URL}/datasets/{image['dataset_id']}/files/{image['_id']}/download"
            rawdata = requests.get(url,headers=headers)
            file_path = f"{directory}/{image['_id']}.jpg"
            url = f"{API_BASE_URL}/datasets/{image['dataset_id']}/files/{image['_id']}/labels"
            bounding_boxes = json.loads(requests.get(url, headers=headers).text)
            metadata = image['user_metadata']
            save_image_with_labels(rawdata.content,bounding_boxes,file_path,metadata)
    time.sleep(30)



