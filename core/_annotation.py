"""
Definition of the annotation object
"""
from . import constants


class Annotation(object):
    """
    Represents an instance of Annotation with information about the label and the region of the object

    Label: Integer denoting the class index in the given dataset

    Annotation region coordinates. They should always map to a region in the corresponding image normalized by the image
    size. That is, point (322, 456) in a (512x512) image should have coordinates (0.6289062, 0.890625). If given values
    are invalid they are adjusted to the range of [0,1].

    Note: A 6 digit precision is recommended for use with Yolo tools.

    x_c: Box center x coordinate
    y_c: Box center y coordinate
    Box width
    Box height
    """

    @staticmethod
    def nrmlz(value, size):
        """
        Normalize a given value by the size of the picture. Truncates to 6 decimals.

        For example pixel position 322 in a 512 length scale would return 0.6289062.
        """
        return round(float(value) / size, 6)

    @staticmethod
    def denormlz(value, size):
        """
        Return the absolute value based on the image size.

        For example pixel position 0.6289062 in a 512 length scale would return 322.
        """
        return int(value * size)

    @classmethod
    def get_annotation_from_borders(cls, label, left, right, bottom, up):
        """
        Return an annotation object based on given borders of the object region.

        Note: Borders should be given normalized by the image size
        """
        label = int(label)
        width = right - left
        height = bottom - up
        x_c = float(left) + width / 2.0
        y_c = float(up) + height / 2.0
        if any([x > 1.0 for x in [x_c, y_c, width, height]]):
            return None
        else:
            return cls(label, x_c, y_c, width, height)

    @classmethod
    def get_annotation_from_str(cls, annot_str):
        """
        Return an annotation object based on given annotation string. Annotation string is assumed to follow the YOLO
        convention as follows, with coordinates normalized by the the image size:

        <label center_x center_y width height>
        """
        label, x_c, y_c, width, height = annot_str.split()
        return cls(int(label), float(x_c), float(y_c), float(width), float(height))

    @classmethod
    def empty(cls):
        """Returns an empty/invalid annotation instance"""
        return cls(-1, 0.0, 0.0, 0.0, 0.0)

    @classmethod
    def combine_annotations(cls, i, j):
        """
        Combines the coordinates of two annotations into a single one and returns a string representing the combined one
        """
        # Create a new annotation with the same borders as the two old ones
        new_up = min(i.up(), j.up())
        new_down = max(i.down(), j.down())
        new_left = min(i.left(), j.left())
        new_right = max(i.right(), j.right())
        new_width = new_right - new_left
        new_height = new_down - new_up
        return cls(
            i.label,
            new_left + new_width / 2.0,
            new_up + new_height / 2.0,
            new_width,
            new_height
        )

    @staticmethod
    def merge_annotations(annot_list):
        """
        Given a list of annotation objects, returns a list of merged annotations based on their location and class
        """
        # Remove possible empty or invalid annotations
        annot_list = [ann for ann in annot_list if ann.label >= 0]

        # Sort all the annotations based on the class index and on the start of transmission
        annot_list.sort(key=lambda x: (x.label, x.y_c - x.height / 2.0))
        # Iteratively merge annotations until necessary
        while True:
            for i in annot_list[:-1]:
                for j in annot_list[annot_list.index(i) + 1:]:
                    # Check same class
                    if i.label == j.label:
                        # Check similar left and right
                        avg_width = (i.width + j.width) / 2
                        if (abs(i.x_c - i.width / 2.0 - j.x_c + j.width / 2.0) <
                            constants.SIDE_THRESHOLD[i.label] * avg_width and
                            abs(i.x_c + i.width / 2.0 - j.x_c - j.width / 2.0) <
                            constants.SIDE_THRESHOLD[i.label] * avg_width) or \
                                ((i.x_c - i.width / 2.0 - j.x_c + j.width / 2.0) *
                                 (i.x_c + i.width / 2.0 - j.x_c - j.width / 2.0)) < 0:
                            # Check beginning - end (this approach also merges overlapping transmissions in the same
                            # channel which is intended since it would be hard to separate the weaker transmission in
                            # the picture)
                            if j.y_c - j.height / 2.0 - i.y_c - i.height / 2.0 < constants.TIME_THRESHOLD[i.label]:
                                merged = Annotation.combine_annotations(i, j)
                                break
                # Inner for loop else clause
                else:
                    continue
                # If inner for-loop breaks, break the outer for-loop in order to reconstruct the list and start over.
                break
            # When no more merging is needed
            else:
                # Break the while-loop
                break

            # Otherwise replace the merged elements with the new one and continue the while-loop.
            annot_list.insert(annot_list.index(i), merged)
            # Remove both merged annotations, mind that the index of j is increased by one.
            annot_list.remove(i)
            annot_list.remove(j)
            continue

        return annot_list

    @classmethod
    def compress_annotation(cls, annot, compr_factor, pic_index):
        """
        Return a new, compressed annotation from a given annotation and a compression factor.

        We assume that the original annotation was generated on flipped pictures. Therefore, no flipping should be done,
        the boxes must be compressed by the factor in height and the center coordinate must be adjusted to reflect the
        compression.
        """

        # If the original annotation is empty or invalid, return an empty annotation
        if annot.label < 0:
            return cls.empty()

        # Compress by the factor, setting a minimum threshold to avoid completely flattening the annotation
        new_height = annot.height / compr_factor

        # If annotation is compressed to 1 pixel or less, delete it
        if new_height < 1 / 512.0:
            return cls.empty()

        # Adjust the new center. The compression is done by stacking <compr_factor> pictures vertically and compressing
        # them, first input picture being moved at the bottom of the resulting one (to depict the flipping of pictures)
        new_y_c = (annot.y_c + compr_factor - pic_index - 1) / float(compr_factor)
        return cls(
            annot.label,
            annot.x_c,
            new_y_c,
            annot.width,
            new_height
        )

    def __init__(self, label, x_c, y_c, width, height):
        try:
            self.label = int(label)
            self.x_c = max(min(float(x_c), 1.0), 0.0)
            self.y_c = max(min(float(y_c), 1.0), 0.0)
            self.width = max(min(float(width), 1.0), 0.0)
            self.height = max(min(float(height), 1.0), 0.0)
        except ValueError as e:
            raise e

    # Set of helper properties to quickly check if the annotation region falls within valid numbers ([0,1])
    @property
    def left(self):
        """Return the left border of the object region in the annotation"""
        return self.x_c - self.width / 2

    @property
    def right(self):
        """Return the right border of the object region in the annotation"""
        return self.x_c + self.width / 2

    @property
    def bottom(self):
        """Return the lower border of the object region in the annotation"""
        return self.y_c + self.height / 2

    @property
    def up(self):
        """Return the upper border of the object region in the annotation"""
        return self.y_c - self.height / 2

    def shift_center(self, new_center_point):
        """Shifts the annotation to a new center point given by a tuple of (new_x_c, new_y_c)"""
        self.x_c, self.y_c = new_center_point

    def scale_annotation(self, factor, ax=None):
        """
        Scales the annotation (up/down) by a given factor along a given axes (x/y, w/h, width/height). If no axes is
        provided, both dimensions are scaled
        """
        if not ax:
            ax = 'both'
        if ax.lower() in ['x', 'w', 'width', 'both']:
            self.width *= factor
        elif ax.lower() in ['y', 'h', 'height', 'both']:
            self.height *= factor

    def get_annot_str(self):
        """
        Returns a string for the annotation following the convention of YOLO with coordinates normalized in the range of
        [0,1]:

        <label center_x center_y width height>
        """
        return "%d %.6f %.6f %.6f %.6f" % (
            self.label,
            self.x_c,
            self.y_c,
            self.width,
            self.height
        )

# Define Box Class

# Connect Annotation and Box classes both ways?

# Draw boxes on images
