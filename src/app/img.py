""" Functions to produce tk-compatible images, using Pillow as a backend.

The image is saved in the dictionary, so it stays in memory. Otherwise
it could get deleted, which will make the rendered image vanish.
"""

from PIL import ImageTk, Image, ImageDraw
import os

from srctools import Vec
from srctools.filesys import FileSystem, RawFileSystem, FileSystemChain
import srctools.logger
import logging
import utils
import wx

from typing import Iterable, Union, Dict, Tuple

LOGGER = srctools.logger.get_logger('img')

cached_img_tk = {}  # type: Dict[Tuple[str, int, int], ImageTk.PhotoImage]
cached_img_wx = {}  # type: Dict[Tuple[str, int, int], ImageTk.PhotoImage]
# r, g, b, size -> image
cached_squares = {}  # type: Dict[Union[Tuple[float, float, float, int], Tuple[str, int]], ImageTk.PhotoImage]

filesystem = FileSystemChain(
    # Highest priority is the in-built UI images.
    RawFileSystem(str(utils.install_path('images'))),
)

# Silence DEBUG messages from Pillow, they don't help.
logging.getLogger('PIL').setLevel(logging.INFO)


def load_filesystems(systems: Iterable[FileSystem]):
    """Load in the filesystems used in packages."""
    for sys in systems:
        filesystem.add_sys(sys, 'resources/BEE2/')


def tuple_size(size: Union[Tuple[int, int], int]) -> Tuple[int, int]:
    """Return an xy tuple given a size or tuple."""
    if isinstance(size, tuple):
        return size
    return size, size


def color_hex(color: Vec) -> str:
    """Convert a RGB colour to #xxxxxx."""
    r, g, b = color
    return '#{:2X}{:2X}{:2X}'.format(int(r), int(g), int(b))


def _png(path: str, resize_to, error, algo, cache, conv):
    """Shared image loading code."""
    path = path.casefold().replace('\\', '/')
    if path[-4:-3] != '.':
        path += ".png"

    resize_width, resize_height = resize_to = tuple_size(resize_to)

    try:
        return cache[path, resize_width, resize_height]
    except KeyError:
        pass

    image: Image.Image
    with filesystem:
        try:
            img_file = filesystem[path]
        except (KeyError, FileNotFoundError):
            LOGGER.warning('ERROR: "images/{}" does not exist!', path)
            return error or img_error
        with img_file.open_bin() as file:
            image = Image.open(file)
            image.load()

    if resize_to != (0, 0) and resize_to != image.size:
        image = image.resize(resize_to, algo)

    conv_img = conv(image)

    cache[path, resize_width, resize_height] = conv_img
    return conv_img


def _conv_tk(image):
    return ImageTk.PhotoImage(image=image)


def _conv_wx(image):
    image = image.convert('RGB')
    wx_img = wx.Bitmap(image.width, image.height)
    wx_img.CopyFromBuffer(image, wx.BitmapBufferFormat_RGB)
    return wx_img


def png(path: str, resize_to=0, error=None, algo=Image.NEAREST):
    """Loads in an image for use in TKinter.

    - The .png suffix will automatically be added.
    - Images will be loaded from both the inbuilt files and the extracted
    zip cache.
    - If resize_to is set, the image will be resized to that size using the algo
    algorithm.
    - This caches images, so it won't be deleted (Tk doesn't keep a reference
      to the Python object), and subsequent calls don't touch the hard disk.
    """
    return _png(path, resize_to, error, algo, cached_img_tk, _conv_tk)


def png_wx(path: str, resize_to=0, error=None, algo=Image.NEAREST) -> wx.Bitmap:
    """Loads in an image for use in WX.

    - The .png suffix will automatically be added.
    - Images will be loaded from both the inbuilt files and the extracted
    zip cache.
    - If resize_to is set, the image will be resized to that size using the algo
    algorithm.
    - This caches images.
    """
    return _png(path, resize_to, error, algo, cached_img_wx, _conv_wx)


def spr(name, error=None):
    """Load in the property icons with the correct size."""
    # We're doubling the icon size, so use nearest-neighbour to keep
    # image sharpness
    return png('icons/'+name, error=error, resize_to=32, algo=Image.NEAREST)


def icon(name, error=None):
    """Load in a palette icon, using the correct directory and size."""
    return png('items/' + name, error=error, resize_to=64)


def get_app_icon(path: str):
    """On non-Windows, retrieve the application icon."""
    with open(path, 'rb') as f:
        return ImageTk.PhotoImage(Image.open(f))


def color_square(color: Vec, size=16):
    """Create a square image of the given size, with the given color."""
    key = color.x, color.y, color.z, size

    try:
        return cached_squares[key]
    except KeyError:
        img = Image.new(
            mode='RGB',
            size=tuple_size(size),
            color=(int(color.x), int(color.y), int(color.z)),
        )
        tk_img = ImageTk.PhotoImage(image=img)
        cached_squares[key] = tk_img
        return tk_img


def invis_square(size):
    """Create a square image of the given size, filled with 0-alpha pixels."""

    try:
        return cached_squares['alpha', size]
    except KeyError:
        img = Image.new(
            mode='RGBA',
            size=tuple_size(size),
            color=(0, 0, 0, 0),
        )
        tk_img = ImageTk.PhotoImage(image=img)
        cached_squares['alpha', size] = tk_img

        return tk_img

# Colour of the palette item background
PETI_ITEM_BG = Vec(229, 232, 233)
PETI_ITEM_BG_HEX = color_hex(PETI_ITEM_BG)


BLACK_64 = color_square(Vec(0, 0, 0), size=64)
BLACK_96 = color_square(Vec(0, 0, 0), size=96)
PAL_BG_64 = color_square(PETI_ITEM_BG, size=64)
PAL_BG_96 = color_square(PETI_ITEM_BG, size=96)

# If image is not readable, use this instead
# If this actually fails, use the black image.
img_error = png('BEE2/error', error=BLACK_64)
