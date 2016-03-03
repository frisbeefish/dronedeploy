# dronedeploy
This is an implementation of the DroneDeploy coding challenge. [Description of the Challenge](https://github.com/frisbeefish/dronedeploy/blob/master/DroneDeployReconstructionChallenge.pdf)

## Overview

Each of the 24 images included in this project were taken by a drone. As each image was taken, the drone recorded its pitch (nose up-ness or down-ness), roll (tilted to the left or tilted to the right), and yaw (non due-North heading). If a drone took a photo when the pitch was 0, the roll was 0, and the yaw was 0, then the center of the photo would represent that part of the earth that was at the latitude and longitude of the drone.
<br />
However, in the real world, drones are almost always not positioned ideally. If a drone's nose is aimed a bit upward when it takes a photo, the latitude of the part of the earth in the vertical center of the photo will not be the same latitude as the drone but will instead be a slightly higher latitude. If you were going to take that photo and place it on a big map of the earth, you would place the photo at a latitude slightly higher than where you'd place a little icon of the drone that took the picture.
<br />
If instead the drone's nose was pointing down a bit, then the latitude of the part of earth that was captured in the vertical center of the photo would be a little bit below the latitude of the drone.
<br />
The same sort of adjustments apply to the photo when the left wing is slightly above the right wing or the right wing is slightly above the left wing. In either of these cases, the longitude of the earth showing in the horizontal center of a photo would not be the exact same longitude of the drone when it took the photo.
<br />
In addition to pitch and roll, the drone is also often not pointing exactly due-North. Instead it can be pointing just about any direction of the compass (along a 360 range of motion that you'd get if the drone was a toy hanging by a thread and tied to the very center of the drone. You could spin the drone to point in any direction of the compass).
<br />
The algorighm in the "mosaic.py" file will use the pitch, roll, and yaw to determine the exact latitude and longitude represented by the center of an image. It will also rotate all images so that even though they all might have been taken when the drone's nose was pointing in a different compass direction (imagine the drone might have flown around in a circle and taken all of these photos along that path) once the images are pasted onto the single mosaic image, all of them will be oriented in the same direction.
<br />
NOTE: You'll see that once all of the images have been stitched together, the mosaic image isn't perfectly smooth. Edges of pieces of the total are jagged at times. There are a few reasons for this and some things that might remedy the issue a bit. One reason for this is that the mosaic isn't a single panorama type photo that was taken from a single point of view. Instead, the mosaic is a compilation of photos that were taken from different perspectives during the flight of a drone. A rock might have a dark shadow on its side in the first photo that the drone took. But then when the drone was in a different position and took a different photo of the rock, the angle is different, the rock looks different, and there is no longer a shadow. So the mosaic is a stitched together set of photos taken from different perspectives. They do all represent the same general area of the earth. But because each photo was taken from a different perspective, the total stitched together mosaic is a bit funny looking.
<br />
BUT!!! If you try to load just a few consecutive photos (the photos in the data.json file are in the order in which they were taken by the drone) into the mosaic, you'll see they stitch together really nicely - since they were all taken from almost the same perspective.
<br />
The other thing that causes a bit of imperfection when stitching these photos together is that due to the fact that the drone took pictures when it was at different pitch and roll and yaw locations, each picture has a slight bit of perspective distortion. (If you took a picture directly looking down, you'd have no distortion. But if you took one at the ground way in front of you, you'd see that the actual content of the image was squeezed a bit at the top due to perspective. You might not notice it, but it is there.) It is possible that this stitching algorighm would have benefitted by some perspective transform like the code does here:

```
import numpy
import sys
from PIL import Image

def find_coeffs(pa, pb):
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])

    A = numpy.matrix(matrix, dtype=numpy.float)
    B = numpy.array(pb).reshape(8)

    res = numpy.dot(numpy.linalg.inv(A.T * A) * A.T, B)
    return numpy.array(res).reshape(8)


coeffs = find_coeffs(
        [(0, 0), (320, 0), (320, 256), (0, 256)],
        [(46, 48), (270, 0), (320, 256), (0, 209)]
        )

img = Image.open("stretched.png")

#
# Make the perspective-stretched image into a rectangular image that looks the way the
# image would look if you had taken the photo from directly above.
#
img.transform((320, 256), Image.PERSPECTIVE, coeffs,
        Image.BICUBIC).show()

```


## Install

```
$ virtualenv venv
$ source venv/bin/activate
$ pip install
```

## Run

```
$ python mosaic.py
```
