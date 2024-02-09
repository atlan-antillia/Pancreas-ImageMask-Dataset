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
# 2024/02/08 Modified to create the mirrored images and masks.
 
import os
import glob
import pydicom
import nibabel as nib

import shutil
from PIL import Image, ImageOps
import traceback

class ImageMaskDatasetGenerator:

  def __init__(self, dcms_dir="./Pancreas-CT/", labels_dir="./TCIA_pancreas_labels-02-05-2017/", mirrored=False):
    self.dcms_dir   = dcms_dir
    self.labels_dir = labels_dir
    self.mirrored   = mirrored
    self.subdirs    = sorted(os.listdir(self.dcms_dir))
    self.NUM_SUBDIRS = len(self.subdirs)

  def generate(self, output_dir="./Pancreas-master"):
    images_dir = os.path.join(output_dir, "images")
    if not os.path.exists(images_dir):
       os.makedirs(images_dir)

    masks_dir = os.path.join(output_dir, "masks")
    if not os.path.exists(masks_dir):
       os.makedirs(masks_dir)

    print(" len dicms_dir {}".format( self.NUM_SUBDIRS))
  
    for subdir in self.subdirs:
      if subdir == "LICENSE":
        continue
      if subdir == "PANCREAS_0063":
        continue

      print(" --- subdir {}".format(subdir))
      mask_nii      = "label" + subdir.split("_")[1] + ".nii"

      mask_nii_file = os.path.join(self.labels_dir, mask_nii)
      print("=== mask_nii_file ")
      num_mask_files = self.generate_mask_files(mask_nii_file, subdir, masks_dir)

      # ./Pancreas-CT/subdir       /*                                     /*             S/*dcm   
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

    if self.mirrored:
      mirrored_image = ImageOps.mirror(image)
      mirrored_filename =  subdir + "-mirrored-" + name + ".jpg"
      image_file = os.path.join(images_dir, filename)
      mirrored_output_file = os.path.join(images_dir, mirrored_filename)
      mirrored_image.save(mirrored_output_file)
      print("=== Saved image {}".format(mirrored_output_file))

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

        if self.mirrored:
          mirrored_image = ImageOps.mirror(image)
          mirrored_filename = subdir + "-mirrored-" +str(index+ i) + ".jpg"
          mirrored_output_file = os.path.join(masks_dir, mirrored_filename)
          mirrored_image.save(mirrored_output_file)
          print("=== Saved mask {}".format(mirrored_output_file))

      else:
        print("=== Skipped {}".format(output_file))
    return num
  
if __name__ == "__main__":
  try:
    input_file = ""
    dcms_dir    = "./Pancreas-CT/"
    labels_dir  = "./TCIA_pancreas_labels-02-05-2017/"

    output_dir  = "./Pancreas-master"

    if os.path.exists(output_dir):
      shutil.rmtree(output_dir)
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    generator = ImageMaskDatasetGenerator(dcms_dir=dcms_dir, labels_dir=labels_dir, mirrored=True)
    generator.generate(output_dir)
    
  except:
    traceback.print_exc()
