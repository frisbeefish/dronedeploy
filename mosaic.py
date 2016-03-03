

import math
import collections
import json
from geopy.distance import vincenty
from PIL import Image


#############################################################
#
# CONSTANTS
#
#############################################################

#
# Images are this size.
#
IMAGE_WIDTH = 4000
IMAGE_HEIGHT = 3000

#
# According to DroneDeploy challenge, we've got a 35mm camera with a focal length of 20.
#
WIDTH_MM = 36
HEIGHT_MM = 26
FOCAL_LENGTH = 20


#############################################################
#
# LONG/LAT DISTANCE CALCULATIONS (in feet)
#
#############################################################

def distance_between_latlong_points_in_feet(point1,point2):
    return vincenty(point1,point2).ft

def horiz_distance_between_latlong_points_in_feet(point1,point2):
    return distance_between_latlong_points_in_feet((38,point1[1]),(38,point2[1]))

def vert_distance_between_latlong_points_in_feet(point1,point2):
    return distance_between_latlong_points_in_feet((point1[0],-123),(point2[0],-123))


#############################################################
#
# ANGLE-OF-VIEW CALCULATIONS - USED TO DETERMINE SIZE OF LAND IN EACH IMAGE
#
#############################################################

#
# "Angle of View" calcs and values from here: https://en.wikipedia.org/wiki/Angle_of_view
#
def angle_of_view(side_mm,focal_len_mm):
    """Calculate the angle-of-view for a camera.

    Args:
        side_mm - the width or height (in mm) of an image on the camera's "film" 
        focal_len_mm - the camera's focal length.
    """
    atan =  math.atan(float(side_mm)/float(focal_len_mm))
    angle_radians = 2 * math.atan(float(side_mm)/float(2*focal_len_mm))
    angle_degrees = math.degrees(angle_radians)
    return angle_degrees

def vertical_angle_of_view():
    return angle_of_view(HEIGHT_MM,FOCAL_LENGTH)

def horizontal_angle_of_view():
    return angle_of_view(WIDTH_MM,FOCAL_LENGTH)



#############################################################
#
# SOME HELPER FUNCTIONS
#
#############################################################

#
# Turn meters into feet.
#
meters_to_feet = lambda meters:3.28084*meters

# 
# Turn feet into meters.
#
feet_to_meters = lambda feet:0.3048*feet

def load_images_data_from_json():
    """Load images data from a JSON file.

    Returns:
        a list of image data objects. Each image data object has these fields: filename, lat, long, altitude,
        yaw, pitch, and roll
    """

    #
    # This will contain the drone image records.
    #
    images = []

    #
    # Load up the drone image records from the JSON file.
    #
    with open('data.json') as data_file:
        images_data = json.load(data_file)
    for one_image_data in images_data:
        image = DroneImage(one_image_data["filename"],one_image_data["lat"],one_image_data["long"],
            one_image_data["altitude"], one_image_data["yaw"], one_image_data["pitch"], one_image_data["roll"])
        images.append(image)

    return images



#############################################################
#
# CLASS DEFS (and NAMED TUPLE)
#
#############################################################


#
# A little quick object thingy that will hold each drone image record that comes from the JSON file.
#
DroneImage = collections.namedtuple('DroneImage', 'filename lat long altitude yaw pitch roll')


#
# The class representing the mosaic image.
#
class Mosaic(object):


    #############################################################
    #
    # PUBLIC INTERFACE
    #
    #############################################################

    def __init__(self,images):
        """Constructor.

        Iterate through the list of images. Capture the min and max latitudes and longitudes - by looking at the 
        latitudes and longitudes of each image.

        Args:
            images - a list data for 24 drone images. Each image has these fields: filename, lat, long, altitude,
            yaw, pitch, and roll
        """
        self.images = images 

        #
        # Calculate and remember the latitude and longitude values for images placed in the top-leftmost corner and the 
        # bottom-rightmost corner.
        #
        self.top_left_lat_long, self.bottom_right_lat_long = self._get_mosaic_lat_long_corners()

        #
        # Calculate the "pixels per foot" value. We'll use this alot.
        #
        self.pixels_per_foot = self._calculate_pixels_per_foot()

        #
        # Create the desination image into which we'll paste each of the 24 images.
        #
        self.mosaic_image = self._create_mosaic_image()


    def add_image_to_mosaic(self, image):
        """Add a single image into the mosaic.

        This method will use the pitch, roll, and yaw of the drone when it took this picture to determine how to determine 
        the "real" latitude and longitude for the center of the image. Then rather than placing the image at the 
        latitude and longitude in the image object (this latitude longitude is the lat/long where the drone was when it 
        took the photo), this code will adjust the center of the image so that it is placed at the latitude and longitude 
        represented by the very center of the image.

        NOTE: In the ideal world, the drone would have been heading due North and would have had a pitch of zero (meaning
        the nose wasn't pointing up or down but straight ahead) and would have a roll of zero (meaning that the left 
        wing was at the same position as the right wing - neither was above the other vertically). In this ideal configuration,
        the center of the image would be the latitude and longitude of the drone when it took the image. But, if the 
        drone had any yaw (non due-North heading) and/or non-zero pitch and/or non-zero roll, then the center of the 
        image isn't the same as the center of the drone. And in that case, we need to slide the image into a position 
        on the mosaic so that the center of the image sits at the latitude/longitude represented by the center of the 
        image and not the latitude/longitude of the drone that took the photo.

        Args:
            image - the image to paste onto the mosaic.
        """
        
        #
        # Capture the image's/drones latitude and longitude.
        #
        imagepos = (image.lat,image.long)

        #
        # How far in feet and pixels is this image from the left edge of the earth/land shown in the mosaic?
        #
        feet_from_left = horiz_distance_between_latlong_points_in_feet(imagepos,self.top_left_lat_long)
        pixels_from_left = feet_from_left * self.pixels_per_foot

        #
        # How far in feet and pixels is this image from the top edge of the earth/land shown in the mosaic?
        #
        feet_from_top = vert_distance_between_latlong_points_in_feet(imagepos,self.top_left_lat_long)
        pixels_from_top = feet_from_top * self.pixels_per_foot

        #
        # Before doing any adjustments to where we will position the image, calculate the center of the image (in pixels)
        # for when we paste the image onto the mosaic image.
        # 
        x, y = 2000 + int(pixels_from_left), 1500+int(pixels_from_top)

        #
        # Assuming the drone was in a perfect due-North orientation, calculate the offset in vertical pixels we'll need
        # to apply to the image based on the "pitch" of the drone. This value will be used to nudge the image up or down
        # a bit from the current value in "y" - since that value in "y" would only be the correct place to put the image
        # if the image was taken when the drone was looking straight down (ie, with pitch=0) as opposed to when it was 
        # nose-up a bit or nose-down a bit.
        #
        vertical_offset_pixels = self._calculate_vertical_offset(image)

        #
        # Assuming the drone was in a perfect due-North orientation, calculate the offset in horizontal pixels we'll need
        # to apply to the image based on the "roll" of the drone. This value will be used to nudge the image left or right
        # in order to compensate for the fact that the photo is actually not a photo of the land at exactly the same
        # longitude as the drone is at but is instead a photo of a longitude a bit to the left or a bit to the right
        # of where the drone is.
        #
        horizontal_offset_pixels = self._calculate_horizontal_offset(image)

        #
        # Now, we will use some Trig to alter the calculated vertical and horizontal offsets that we'll use to adjust
        # the "x" and "y" values. This Trig adjusts for the angle of "yah" (non due-North orientation) of the drone when
        # it took the photo.
        #
        xshift = vertical_offset_pixels * math.sin(math.radians(image.yaw))
        vertical_offset_pixels = vertical_offset_pixels * math.cos(math.radians(image.yaw))
        horizontal_offset_pixels = horizontal_offset_pixels - xshift

        #
        # Now, what we're doing is adjusting the "x" and "y" values (the center of the image) so that they reflect
        # the actual latitude and longitude of the land/earth showing in the center of the image instead of the
        # latitude and longitude of the center of the drone when it took the photo.
        #
        x += horizontal_offset_pixels
        y += vertical_offset_pixels

        print 'centering image: %s at (%d,%d) and rotating degrees: %f' % (image.filename,int(x),int(y),image.yaw)

        #
        # Open the original image file. Give it an alpha background so that when we rotate it, the background behind the
        # rotated image shows through (so it doesn't obstruct other images).
        #
        img = Image.open(image.filename)
        img = img.convert('RGBA')

        #
        # Rotate the image by the amount that the drone was rotated (yaw) so that even if the plane was twisted at some
        # strange angle, by the time the image is pasted onto the mosaic, its North will be the same as the North of all
        # the other images pasted onto the mosaic.
        #
        rot = img.rotate(-1 * image.yaw,expand=True)
        self._paste_image(rot,int(x),int(y))

    def add_all_images(self):
        """Add all of the images from self.images into the mosaic.
        """
        for image in self.images:
            self.add_image_to_mosaic(image)

    def add_images(self,start,end):
        """Add all of the images from a slice of self.images into the mosaic.

           Args:
               start - The index of the first element in the slice of self.images 
               end - The index of the after-the-last element in the slice of self.images
        """
        for image in self.images[start:end]:
            self.add_image_to_mosaic(image)

    def show(self):
        """Pop up the mosaic image so you can see it!
        """
        self.mosaic_image.show()

    def save(self,filename):
        """Save the mosaic image to disk.

           Args:
               filename - the name of the image that will be saved.
        """
        self.mosaic_image.save(filename,"PNG")


    #############################################################
    #
    # PRIVATE METHODS
    #
    #############################################################

    def _get_min_max_long_and_lat(self):
        """Iterate through the list of images. Capture the min and max latitudes and longitudes - by looking at the 
        latitudes and longitudes of each image.

        Returns:
            min_long - the minimum (leftmost in our part of the world) longitude of all the images' longitudes
            max_long - the maximum (rightmost in our part of the world) longitude of all the images' longitudes
            min_lat - the minimum latitude of all the latitudes of all the images
            max_lat - the maximum latitude of all the latitudes of all the images
        """

        min_long = None
        max_long = None
        min_lat = None
        max_lat = None

        for image in self.images:
            if min_long is None:
                min_long = image.long
            elif image.long < min_long:
                min_long = image.long
            if max_long is None:
                max_long = image.long
            elif image.long > max_long:
                max_long = image.long
            if min_lat is None:
                min_lat = image.lat
            elif image.lat < min_lat:
                min_lat = image.lat
            if max_lat is None:
                max_lat = image.lat
            elif image.lat > max_lat:
                max_lat = image.lat

        return min_long, max_long, min_lat, max_lat


    def _get_mosaic_lat_long_corners(self):
        """Calculate the top-left-most latitude and longitude and the bottom-right-most lattitude and longitude
        based on all of the images and their latitudes and longitudes.

        Returns:
            The two tuples - the first is the lattitude and longitude of an image if it was positioned in the 
            top-left of the mosaic we are creating. The second is the lattitude and longitude of an image if 
            it was positioned in the bottom-right of the mosaic we are creating.
        """
        min_long, max_long, min_lat, max_lat = self._get_min_max_long_and_lat()
        return (max_lat,min_long),(min_lat,max_long)    


    def _calculate_pixels_per_foot(self):
        """Use the horizontal angle-of-view for the camera + the average altitude of the drone when
        pics are taken to calculate the width (in feet) of the earth photographed by each image. Then
        return the pixels-per-each-foot-of-earth that is in each photo.

        Returns:
            The number of pixels in an image that represent a foot of land/earth.
        """

        average_altitude_meters = sum([image.altitude for image in self.images])/len(images)

        horiz_angle_of_view = horizontal_angle_of_view()
        
        half_horiz_angle_of_view = float(horiz_angle_of_view)/2

        image_width_in_meters = 2 * math.tan( math.radians(half_horiz_angle_of_view) ) * average_altitude_meters

        image_width_in_feet = meters_to_feet(image_width_in_meters)

        pixels_per_foot = IMAGE_WIDTH/image_width_in_feet

        return pixels_per_foot


    def _paste_image(self,image,x,y):
        """Add an image (with transparency so if it is rotated the background doesn't block stuff below) into the 
        mosaic image.

        Args:
            image - the image to paste onto the mosaic 
            x - the x position for the center of the image on the mosaic.
            y - the y position for the center of the image on the mosaic.
        """

        xpos = lambda image,x:x-image.size[0]/2
        ypos = lambda image,y:y-image.size[1]/2

        #
        # Get the top-left corner positions.
        #
        top_left_xpos = xpos(image,x)
        top_left_ypos = ypos(image,y)

        self.mosaic_image.paste(image,(xpos(image,x),ypos(image,y)),image)

    def _calculate_vertical_offset(self,image):
        """Calculate and return the number of pixels to nudge this image up or down when it is pasted onto the mosaic. 
        
        image.pitch = how "upish" or "downish" the nose of the drone was pointing when it took the photo.

        The image will be shoved up a bit if the nose of the drone is up-ish (and thus the center of the photo taken
        by the drone is really not at the image.lat value - the drone's latitude - but is at a latitude a bit above the 
        latitude of the drone. Likewise, the image will be shoved down a bit (in the mosaic) if the nose of the drone 
        was pointing a bit down when it took the photo (which would mean that the vertical center of the photo would 
        not be at the latitude where the drone is but at a slightly lower latitude).

        Put differently, assuming the drone was pointing perfectly North, calculate how far below or above the drone's 
        latitude (which is in image.lat) the center of the image is. We are calculating the number of feet and then
        the number of pixels by which to shift the image up or down in the mosaic.

        Args:
            image - the image that will be shifted up or down based on the pitch of the drone when the drone took
            this image.
        """
        offset_in_meters = image.altitude * math.tan(math.radians(image.pitch))
        offset_in_feet = meters_to_feet(offset_in_meters)
        pixels_per_foot = self.pixels_per_foot
        offset_in_pixels = pixels_per_foot * offset_in_feet
        return offset_in_pixels


    def _calculate_horizontal_offset(self,image):
        """Calculate and return the number of pixels to nudge this image left or right when it is pasted onto the mosaic. 
        
        image.roll = how tilted left from perfectly horizontal or tilted right from perfectly horizontal is the drone.
        
        The image will be shoved left a bit if the left wing of the drone was a bit above the right wing of the drone 
        when the photo taken (and thus the horizontal center of the photo taken by the drone is really not at the
        image.long value - the drone's longitude - but is at a longitude a bit to the left the longitude of the drone. 

        The image will be shoved right a bit if the right wing of the drone was a bit above the left wing of the drone 
        when the photo taken (and thus the horizontal center of the photo taken by the drone is really not at the
        image.long value - the drone's longitude - but is at a longitude a bit to the right the longitude of the drone. 

        Args:
            image - the image that will be shifted left or right based on the roll of the drone when the drone took
            this image.
        """
        offset_in_meters = image.altitude * math.tan(math.radians(image.roll))
        offset_in_feet = meters_to_feet(offset_in_meters)
        pixels_per_foot = self.pixels_per_foot
        offset_in_pixels = pixels_per_foot * offset_in_feet
        return offset_in_pixels



    def _create_mosaic_image(self):
        """Create the destination "mosaic" image using PIL.
        
        Create an image that is large enough to contain all of the images collected by the drone.

        ASSUME: All the latitudes and longitudes of images represent the centers of those images (and the center of the 
        drone when it took the photos).
        """
        horiz_feet_between_edge_images = horiz_distance_between_latlong_points_in_feet(self.top_left_lat_long, self.bottom_right_lat_long)
        vert_feet_between_edge_images = vert_distance_between_latlong_points_in_feet(self.top_left_lat_long, self.bottom_right_lat_long)

        horiz_pixels = self.pixels_per_foot  * horiz_feet_between_edge_images
        horiz_pixels += 4000

        vert_pixels = self.pixels_per_foot  * vert_feet_between_edge_images
        vert_pixels += 3000

        mosaic_image = Image.new("RGBA", (int(horiz_pixels),int(vert_pixels)), "white")
        return mosaic_image



if __name__ == "__main__":
    
    #
    # Load the image records from the JSON file.
    #
    images = load_images_data_from_json()

    #
    # Create the mosaic
    #
    m = Mosaic(images)

    #
    # Add the images into the mosaic.
    #
    m.add_all_images()

    m.show()

    m.save('mosaic.png');




    
