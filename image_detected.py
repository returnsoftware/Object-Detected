import socket
import json
import numpy as np
import os
import sys
import tensorflow as tf
from matplotlib import pyplot as plt
import base64
import io
sys.path.append("..")
from object_detection.utils import ops as utils_ops
from utils import label_map_util
from utils import visualization_utils as vis_util
import threading
import tkinter
from PIL import ImageTk, Image 
import time


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
MODEL_NAME = 'ssd_mobilenet_v1_coco_2017_11_17'
PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'
PATH_TO_LABELS = os.path.join('data', 'mscoco_label_map.pbtxt')
NUM_CLASSES = 90

detection_graph = tf.Graph()
with detection_graph.as_default():
  od_graph_def = tf.GraphDef()
  with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
    serialized_graph = fid.read()
    od_graph_def.ParseFromString(serialized_graph)
    tf.import_graph_def(od_graph_def, name='')

label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)

def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)

IMAGE_SIZE = (12, 8)


def run_inference_for_single_image(image, graph,sess):
  with graph.as_default():
      
      ops = tf.get_default_graph().get_operations()
      all_tensor_names = {output.name for op in ops for output in op.outputs}
      tensor_dict = {}
      for key in [
          'num_detections', 'detection_boxes', 'detection_scores',
          'detection_classes', 'detection_masks'
      ]:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
          tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
              tensor_name)
      if 'detection_masks' in tensor_dict:
        
        detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
        detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
        
        real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
        detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
        detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
        detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
            detection_masks, detection_boxes, image.shape[0], image.shape[1])
        detection_masks_reframed = tf.cast(
            tf.greater(detection_masks_reframed, 0.5), tf.uint8)
        
        tensor_dict['detection_masks'] = tf.expand_dims(
            detection_masks_reframed, 0)
      image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

      
      output_dict = sess.run(tensor_dict,
                             feed_dict={image_tensor: np.expand_dims(image, 0)})

      
      output_dict['num_detections'] = int(output_dict['num_detections'][0])
      output_dict['detection_classes'] = output_dict[
          'detection_classes'][0].astype(np.uint8)
      output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
      output_dict['detection_scores'] = output_dict['detection_scores'][0]
      if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
  return output_dict


# In[11]:
class StreamData(object):
    def __init__(self,UserId,Detectionlist):
         self.UserId=UserId
         self.Detectionlist=Detectionlist
 
class Result(object):
    def __init__(self, data):
	    self.__dict__ = json.loads(data)

UDP_IP_ADDRESS = "127.0.0.1"
UDP_PORT_NO = 1254

serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSock.bind((UDP_IP_ADDRESS, UDP_PORT_NO))


def get_started_image_detected():
  with tf.Session(graph=detection_graph) as sess:
   while True:
    try :
      data, addr = serverSock.recvfrom(999999)
      result = Result(data.decode())
      print ("Receive: " + str(result.UserId))
      print(addr[1])
      image = base64.b64decode(result.Image)
      image = io.BytesIO(image)
      image_detected = Image.open(image)
      print(image_detected)
      image_np = load_image_into_numpy_array(image_detected)
      image_np_expanded = np.expand_dims(image_np, axis=0)
      output_dict = run_inference_for_single_image(image_np, detection_graph,sess)
      vis_util.visualize_boxes_and_labels_on_image_array(
         image_np,
         output_dict['detection_boxes'],
         output_dict['detection_classes'],
         output_dict['detection_scores'],
         category_index,
         instance_masks=output_dict.get('detection_masks'),
         use_normalized_coordinates=True,
         line_thickness=8)
      detection_scores = []
      detection_classes = []
      for key in  output_dict['detection_scores']:
          if key <= 0.5: break
          if key > 0.5:
              detection_scores.append(key)
      for key in range(len(detection_scores)):
          detection_classes.append(str(output_dict['detection_classes'][key]))
      print(detection_classes)
      stream = StreamData(result.UserId,detection_classes)
      json_str = json.dumps(stream.__dict__)
      serverSock.sendto(json_str.encode(), (addr[0], addr[1]))
    except ConnectionResetError:
        print('connection lost!')
        pass
   



get_started_image_detected()


  

  
  
  