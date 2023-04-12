"""
Helper class to plot interactive images with matplotlib
"""
from os.path import join
import logging
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.widgets import RectangleSelector


__all__ = ['Plotter']

logging.getLogger('matplotlib').setLevel(logging.WARNING)
log = logging.getLogger('spread')


class Plotter(object):
    """
    Represents an instance of plotter for the Recording class
    """

    @staticmethod
    def _get_image_from_data(data, mode=None):
        try:
            im = Image.fromarray(data, mode=mode)
            return im
        except AttributeError:
            return None

    @staticmethod
    def onkeypress(event):
        """Experimental function to test key press"""
        if event.key == 'q':
            pass
            # print('event is q')

    @staticmethod
    def toggle_selector(event):
        """Activate the mouse click"""
        Plotter.toggle_selector.RS.set_active(True)

    def __init__(self):
        """Instance of plotter helper class"""

        self.selected_areas = None

    def area_borders(self):
        """Return the borders of the selected area"""
        left = int(min(self.selected_areas[0], self.selected_areas[2]))
        right = int(max(self.selected_areas[0], self.selected_areas[2]))
        bottom = int(max(self.selected_areas[1], self.selected_areas[3]))
        up = int(min(self.selected_areas[1], self.selected_areas[3]))
        return left, right, bottom, up

    def pretty_area_print(self):
        """Return a string descrptions of the selected area for prettier output"""
        return "Left: %s\n" \
               "Right: %s \n" \
               "Bottom: %s \n" \
               "Up: %s" % self.area_borders()

    def plot(self, im=None, data=None, subplot=None, outfile=None, figdir=None, resize=None, options=None):
        """
        Plot function either plots in a given subplot and returns the subplot or saves the image to a file.
        """

        im = im if im else Plotter._get_image_from_data(data)

        if resize:
            im = im.resize(resize)

        if not im:
            log.error("Nothing to plot.")
            return None

        if subplot is not None:
            self._plot(im, subplot, options)
        else:
            Plotter._save_image(im, outfile, figdir)

    def _line_select_callback(self, clk, rls):
        """
        Handles mouse events to trigger noise area selection or image selection
        """
        self.selected_areas = [clk.xdata, clk.ydata, rls.xdata, rls.ydata]

    def _plot(self, im, subplot, options):
        """Plot image either with pillow or matlab for more options"""
        if subplot == "pillow":
            im.show()
        else:
            subplot.imshow(im)
            if options:
                if options.get('noise_input', None):
                    Plotter.toggle_selector.RS = RectangleSelector(
                        subplot, self._line_select_callback, useblit=True, button=[1], minspanx=5,
                        minspany=5, spancoords='pixels', interactive=True
                    )
                    noise_box = plt.connect('key_press_event', Plotter.toggle_selector)

                if options.get('button', None):
                    # Expect a list of dict for buttons
                    for btn in options.get('button'):
                        btn_label = btn.get('label', '')

                        # Button position as in [left, bottom, width, height]
                        btn_position = btn.get('position', None)

                        btn_action = btn.get('action')()

            plt.show()
        pass

    @staticmethod
    def _save_image(im, outfile, figdir):
        """Save image to file"""
        img_name = join(figdir, outfile)
        im.save(img_name)
