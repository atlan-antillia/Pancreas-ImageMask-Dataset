# Copyright 2024 antillia.com Toshiyuki Arai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ImageMaskDatasetGenerator.py
#
# 2024/02/08 Modified to create the horiz_flip images and masks.
# 2024/02/12 Modified not to create the horiz_flip images and masks.
# 2024/02/12 Modified use generator.config file.

# 2024/02/12 Modified to create cropped images and masks.
#  1 Cropp a center square region specified by crop box
#  2 Resize it to the original size of the image 

import os
import glob
import pydicom
import nibabel as nib
from ConfigParser import ConfigParser
from ImageMaskAugmentor import ImageMaskAugmentor

import shutil
from PIL import Image, ImageOps
import traceback
GENERATOR = "generator"
AUGMENTOR = "augmentor"

class ImageMaskDatasetGenerator:

  def __init__(self, config_file):
    parser = ConfigParser(config_file)           
    self.dcms_dir   = parser.get(GENERATOR, "dcms_dir")
    if not os.path.exists(self.dcms_dir):
      raise Exception("Not found dcms_dir" + self.dcms_dir)
    
    self.labels_dir = parser.get(GENERATOR, "labels_dir")
    if not os.path.exists(self.labels_dir):
      raise Exception("Not found labels_dir" + self.labels_dir)

    self.output_dir = parser.get(GENERATOR, "output_dir")
    if os.path.exists(self.output_dir):
      shutil.rmtree(self.output_dir)
    if not os.path.exists(self.output_dir):
      os.makedirs(self.output_dir)

    self.subdirs      = sorted(os.listdir(self.dcms_dir))
    self.NUM_SUBDIRS  = len(self.subdirs)
    # For future work.
    self.augmentation = parser.get(GENERATOR, "augmentation")

    self.WIDTH        = parser.get(GENERATOR, "image_width")
    self.HEIGHT       = parser.get(GENERATOR, "image_height")

    self.crop       = parser.get(AUGMENTOR, "crop")

    # crop_margins  = [40, 60, 80,]
    # The crop_margins list must be chosen properly depending on the real images or masks 
    # to include the acutual tumor or cancer regions.
    #self.CROP_MARGINS  = [40, 80,]
    self.crop_margins = parser.get(AUGMENTOR, "crop_margin")
    self.crop_boxes = []
    # Create the center-CROP_BOXES from self.CROP_MARGINS list 
    for margin in self.crop_margins:
      LEFT            = margin
      UPPER           = margin
      RIGHT           = self.WIDTH  - LEFT
      LOWER           = self.HEIGHT - UPPER
      self.crop_boxes.append((LEFT, UPPER, RIGHT, LOWER))

  def generate(self):
    images_dir = os.path.join(self.output_dir, "images")
    if not os.path.exists(images_dir):
       os.makedirs(images_dir)

    masks_dir = os.path.join(self.output_dir, "masks")
    if not os.path.exists(masks_dir):
       os.makedirs(masks_dir)

    print(" len dicms_dir {}".format( self.NUM_SUBDIRS))
  
    for subdir in self.subdirs:
      if subdir == "LICENSE":
        continue
      if subdir == "PANCREAS_0063":
        #Skipping image-mask-unmatched dataset 
        continue

      print(" --- subdir {}".format(subdir))
      mask_nii      = "label" + subdir.split("_")[1] + ".nii"

      mask_nii_file = os.path.join(self.labels_dir, mask_nii)
      print("=== mask_nii_file ")
      num_mask_files = self.generate_mask_files(mask_nii_file, subdir, masks_dir)

      # ./Pancreas-CT/subdir       /*                                     /*             /*dcm   
      # ./Pancreas-CT/PANCREAS_0001/11-24-2015-PANCREAS0001-Pancreas-18957/Pancreas-99667/*.dcm"      
      dcm_files = glob.glob(self.dcms_dir + subdir + "/*/*/*.dcm") 
      num_dcm_file = len(dcm_files)

      if (num_mask_files != num_dcm_file):
        print("UNMATCHED ----------- {} {}".format(num_mask_files, num_dcm_file))
        continue

      for dcm_file in dcm_files:
        basename = os.path.basename(dcm_file)
        name     = basename.split(".")[0]
        name     = name.replace("-", "")
        print("=== dcm file {}". format(dcm_file))
        filename =  subdir + "-" + name + ".jpg"
        corresponding_mask_filepath = os.path.join(masks_dir, filename)
        if os.path.exists(corresponding_mask_filepath):
          self.generate_image_file(dcm_file, subdir, images_dir)
        else:
          print("=== Skipped {}".format(filename))
    
    if self.augmentation:
      self.image_mask_augmentor = ImageMaskAugmentor(config_file)
      
  def generate_image_file(self, dcm_file, subdir, images_dir):
    dcm      = pydicom.dcmread(dcm_file)
    img      = dcm.pixel_array
    image    = Image.fromarray(img)
    image    = image.convert("RGB")

    basename = os.path.basename(dcm_file)
    name     = basename.split(".")[0]
    name     = name.replace("-", "")
    print("=== dcm file {}". format(dcm_file))
    filename =  subdir + "-" + name + ".jpg"
    image_file = os.path.join(images_dir, filename)
    image.save(image_file, "JPEG")
    print("Saved image {}".format(image_file))

    if self.crop:
      # Crop a center region specifiied by crop box, and resize it to the original
      # size of the image
      for n, box in enumerate(self.crop_boxes):
        cropped_image = image.crop(box)

        cropped_image = cropped_image.resize((self.WIDTH, self.HEIGHT))

        cropped_filename =  subdir + "-cropped-" + str(n) + "-" + name + ".jpg"
        cropped_output_file = os.path.join(images_dir, cropped_filename)
        cropped_image.save(cropped_output_file)
        print("=== Saved image {}".format(cropped_output_file))

  def generate_mask_files(self, mask_nii_file, subdir, masks_dir):
    nii = nib.load(mask_nii_file)
    fdata = nii.get_fdata()
    shape = fdata.shape
  
    num = shape[2]
    index = 1001
    for i in range(num):
      data = fdata[:,:,i]
      data = data * 255.0
      data = data.astype('uint8')
      filename = subdir + "-" + str(index+ i) + ".jpg"
      output_file = os.path.join(masks_dir, filename)
      if data.any() >0:
        image = Image.fromarray(data)
        image = image.convert("RGB")
        image = image.rotate(90)
        image = ImageOps.flip(image)
        image.save(output_file)
        print("=== Saved mask {}".format(output_file))

        # Crop a center region specifiied by crop box, and resize it to the original
        # size of the image
        if self.crop:
          for n, box in enumerate(self.crop_boxes):
            cropped_image = image.crop(box)
            cropped_image = cropped_image.resize((self.WIDTH, self.HEIGHT))

            cropped_filename =  subdir + "-cropped-" + str(n) + "-" + str(index+ i)  + ".jpg"
            cropped_output_file = os.path.join(masks_dir, cropped_filename)
            cropped_image.save(cropped_output_file)
            print("=== Saved image {}".format(cropped_output_file))

      else:
        print("=== Skipped {}".format(output_file))
    return num
  
if __name__ == "__main__":
  try:
    config_file = "./generator.config"
    if not os.path.exists(config_file):
      raise Exception("Not found config_file" + config_file)
    
    generator = ImageMaskDatasetGenerator(config_file)

    generator.generate()
    
  except:
    traceback.print_exc()
