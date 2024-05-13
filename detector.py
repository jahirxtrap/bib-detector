import cv2 as cv
import numpy as np

class detector:
    def __init__(self, cfg, wts, classes):
        """Initialize detector object
        
        Args
            cfg (str): path to model config file
            wts (str): path to model weights file
            classes (list): list of class names
        """
        self.classes = classes
        self.net = cv.dnn.readNetFromDarknet(cfg, wts)
        self.net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)

        # determine the output layer
        layer_names = self.net.getLayerNames()
        self.ln = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]

        
    def detect(self, img, conf):
        """
        Make predictions and return classes and bounding boxes
        
        Args
            img (numpy array): image array from openCV .imread
            conf (float): prediction confidence threshold
            
        Returns
            List containing bounding box values and class names for detections
            in the form [<class name>, [x, y, width, height]]
        """

        #format image for detection
        blob = cv.dnn.blobFromImage(img, 1/255.0, (416, 416), swapRB=True, crop=False)
        
         # get detections
        self.net.setInput(blob)
        outputs = self.net.forward(self.ln)

        # initialize lists
        boxes = []
        confidences = []
        classIDs = []

        # initialize image dimensions
        h_img, w_img = img.shape[:2]

        for output in outputs:
            for detection in output:
                scores = detection[5:]
                classID = np.argmax(scores)
                confidence = scores[classID]

                # drop low confidence detections and 
                if confidence > conf:
                    box = detection[:4] * np.array([w_img, h_img, w_img, h_img])
                    (centerX, centerY, width, height) = box.astype("int")
                    x = int(centerX - (width / 2))
                    y = int(centerY - (height / 2))
                    box = [x, y, int(width), int(height)]
                    boxes.append(box)
                    confidences.append(float(confidence))
                    classIDs.append(classID)

        # apply non maximal suppression for
        # initialize lists
        self.boxes = []
        self.confidences = []
        self.detected_classes = []
        cls_and_box = []
        # get indices of final bounding boxes  
        indices = cv.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

        if len(indices) > 0:
            for i in indices.flatten():
                self.boxes.append(boxes[i])
                self.confidences.append(confidences[i])
                self.detected_classes.append(self.classes[classIDs[i]])
                
                cls_and_box.append([self.classes[classIDs[i]], boxes[i]])
        
        return cls_and_box


def get_rbns(img, single=False, model=1):
    """
    Given an image return bib numbers and bib bounding boxes for detected bibs
    
    Args
        img (numpy array): image array given by openCV .imread
        single (bool): whether one or many bib detections will be
            returned.  If true, return detection with largest bounding
            box area.
            
    Returns
        List of detected bib numbers and corresponding bounding boxes in
        the format [<bib number>, [x, y, width, height]]
    """

    yolo_path = './data/YOLO2/'
    if model == 2:
        yolo_path = './data/YOLO/'

    # Configuración del modelo de detección de números dorsales
    bd_configPath = yolo_path + 'bib_detector/RBNR2_custom-yolov4-tiny-detector.cfg'
    bd_weightsPath = yolo_path + 'bib_detector/RBNR2_custom-yolov4-tiny-detector_best.weights'
    bd_classes = ['bib']

    # Number reader config
    nr_configPath = yolo_path + 'num_reader/SVHN3_custom-yolov4-tiny-detector.cfg'
    nr_weightsPath = yolo_path + 'num_reader/SVHN3_custom-yolov4-tiny-detector_best.weights'
    nr_classes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    # Instantiate detectors
    bd = detector(bd_configPath, bd_weightsPath, bd_classes)
    nr = detector(nr_configPath, nr_weightsPath, nr_classes)

    # Make bib location predictions
    bib_detections = bd.detect(img, 0.25)


    if len(bib_detections) > 0:
        for obj in bib_detections:
            # crop out detected bib
            (x, y, w, h) = obj[1]
            obj.append(w * h)
            crop_img = img[y:y+h, x:x+w]
            
            # detect numbers on bib
            num_detections = nr.detect(crop_img, 0.5)
            bib_digit_loc = []
            if len(num_detections) > 0:
                # get digits and locations
                for digit in num_detections:
                    (d_x, d_y, d_w, d_h) = digit[1]
                    bib_digit_loc.append((d_x, str(digit[0])))

                # sort detected numbers L->R and put together
                bib_digit_loc.sort()
                rbn = int(''.join([i[1] for i in bib_digit_loc]))
                obj.append(rbn)
            else:
                obj.append(0) # bib detection but no digit detection

        if single: 
            if len(bib_detections) > 1:
                bib_detections.sort(key=lambda x: x[2], reverse=True)
            return [[bib_detections[0][3], bib_detections[0][1]]]
        else:
            final_bibs = []
            for bib in bib_detections:
                final_bibs.append([bib[3], bib[1]])
            return final_bibs
    else: return None


def annotate(img, annot, color):
    """
    Add bib numbers and bib bounding boxes to an image
    
    Args
        img (numpy array): image array of original from openCV .imread
        annot (list): list of bib numbers and bounding boxes in the 
            form [[<bib number>, [x, y, width, height]]]
        color (array): RGB color array for annotation color
        
    Returns
        Annotated image as numpy array
    """
    
    # draw bouding box on original image
    (x, y, w, h) = annot[1]
    annot_img = cv.rectangle(img,(x,y),(x+w,y+h),color,5)
    # add bib number to original image
    rbn = annot[0]
    cv.putText(annot_img, str(rbn), (x, y - 25), cv.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    return annot_img