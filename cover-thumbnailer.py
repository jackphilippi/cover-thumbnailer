#!/usr/bin/env python3
# -*- coding: utf-8 -*-

   #########################################################################
 ##                                                                       ##
##           ┏━╸┏━┓╻ ╻┏━╸┏━┓   ╺┳╸╻ ╻╻ ╻┏┳┓┏┓ ┏┓╻┏━┓╻╻  ┏━╸┏━┓            ##
##           ┃  ┃ ┃┃┏┛┣╸ ┣┳┛    ┃ ┣━┫┃ ┃┃┃┃┣┻┓┃┗┫┣━┫┃┃  ┣╸ ┣┳┛            ##
##           ┗━╸┗━┛┗┛ ┗━╸╹┗╸    ╹ ╹ ╹┗━┛╹ ╹┗━┛╹ ╹╹ ╹╹┗━╸┗━╸╹┗╸            ##
##                         — www.flogisoft.com —                          ##
##                                                                        ##
############################################################################
##                                                                        ##
## Cover thumbnailer                                                      ##
##                                                                        ##
## Copyright (C) 2009 - 2023  Fabien Loison <http://www.flozz.fr/>        ##
##                                                                        ##
## This program is free software: you can redistribute it and/or modify   ##
## it under the terms of the GNU General Public License as published by   ##
## the Free Software Foundation, either version 3 of the License, or      ##
## (at your option) any later version.                                    ##
##                                                                        ##
## This program is distributed in the hope that it will be useful,        ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of         ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          ##
## GNU General Public License for more details.                           ##
##                                                                        ##
## You should have received a copy of the GNU General Public License      ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>.  ##
##                                                                        ##
############################################################################
##                                                                        ##
## WEB SITE : https://github.com/flozz/cover-thumbnailer                  ##
##                                                                       ##
#########################################################################


"""Generates thumbnails for nautilus' folders.

Cover thumbnailer generates thumbnail that will be displayed instead of the
default folder icons. It has a specific presentation for music and pictures
folders, and a generic one for other folders.

Usage:
    cover-thumbnailer <directory's path> <output thumbnail's path>
"""

__version__ = "0.10.1"
__author__ = "Fabien Loison <http://www.flozz.fr/>"
__copyright__ = "Copyright © 2009 - 2023 Fabien LOISON"


import re
import sys
import os.path
import math
import itertools
from gi.repository import Gio
from pathlib import Path

try:
    from PIL import Image
except:
    import Image


#==================================================================== CONF ====
#Base path for cover thumbnailer's pictures
if "DEVEL" in os.environ:
    BASE_PATH = "./share/" #For devel
else:
    BASE_PATH = "/usr/share/cover-thumbnailer/"

#Cover files list
COVER_FILES = ["cover.png", "cover.jpg", ".cover.png", ".cover.jpg",
        "Cover.png", "Cover.jpg", ".Cover.png", ".Cover.jpg",
        "folder.png", "folder.jpg", ".folder.png", ".folder.jpg",
        "Folder.png", "Folder.jpg", ".Folder.png", ".Folder.jpg"]

#Supported picture ext (ALWAY LAST 4 CHARS !!)
PICTURES_EXT = [".jpg", ".JPG", "jpeg", "JPEG",
        ".png", ".PNG", #Not interlaced
        ".gif", ".GIF",
        ".bmp", ".BMP", #Window ans OS/2 bitmap
        ".ico", ".ICO", #Windows icon format
        ".tga", ".TGA", #Truevision Targa format
        ".tif", ".TIF", "tiff", "TIFF", #Adobe Tagged Image File Format
        ".psd", ".PSD", #Adobe Photosop format (only version 2.5 and 3.0)
        ]

#==============================================================================


class Conf(dict):

    """ Import configuration.

    Import configuration from the GNOME and cover thumbnailer files
    """

    def __init__(self):
        """ The constructor

        Set the default values
        """
        #Initialize the dictionary
        dict.__init__(self)
        #Music
        self['music_enabled'] = True
        self['music_keepdefaulticon'] = False
        self['music_usegnomefolder'] = True
        self['music_cropimg'] = True
        self['music_makemosaic'] = False
        self['music_paths'] = []
        self['music_defaultimg'] = os.path.join(BASE_PATH, "music_default.png")
        self['music_fg'] = os.path.join(BASE_PATH, "music_fg.png")
        self['music_bg'] = os.path.join(BASE_PATH, "music_bg.png")
        #Pictures
        self['pictures_enabled'] = True
        self['pictures_keepdefaulticon'] = False
        self['pictures_usegnomefolder'] = True
        self['pictures_maxthumbs'] = 3
        self['pictures_paths'] = []
        self['pictures_fg'] = os.path.join(BASE_PATH, "pictures_fg.png")
        self['pictures_bg'] = os.path.join(BASE_PATH, "pictures_bg.png")
        #Other
        self['other_enabled'] = True
        self['other_fg'] = os.path.join(BASE_PATH, 'other_fg.png')
        #Ignored
        self['ignored_dotted'] = False
        self['ignored_paths'] = []
        #Never ignored
        self['neverignored_paths'] = []
        #Global
        self.user_homedir = os.environ.get("HOME")
        self.user_gnomeconf = os.path.join(
                self.user_homedir,
                ".config/user-dirs.dirs"
                )
        self.user_conf = os.path.join(
                self.user_homedir,
                ".cover-thumbnailer/cover-thumbnailer.conf"
                )
        #Read configuration
        self.import_user_conf()
        self.import_gnome_conf()

    def import_gnome_conf(self):
        """ Import user folders from GNOME configuration file. """
        if os.path.isfile(self.user_gnomeconf):
            gnome_conf_file = open(self.user_gnomeconf, 'r')
            for line in gnome_conf_file:
                if re.match(r'.*?XDG_MUSIC_DIR.*?=.*?"(.*)".*?', line) and self['music_usegnomefolder']:
                    match = re.match(r'.*?XDG_MUSIC_DIR.*?=.*?"(.*)".*?', line)
                    path = match.group(1).replace('$HOME', self.user_homedir)
                    #If path == user home dir, don't use it, it's probably a misconfiguration !
                    if os.path.isdir(path) and not os.path.samefile(path, self.user_homedir):
                        self['music_paths'].append(path)
                elif re.match(r'.*?XDG_PICTURES_DIR.*?=.*?"(.*)".*?', line) and self['pictures_usegnomefolder']:
                    match = re.match(r'.*?XDG_PICTURES_DIR.*?=.*?"(.*)".*?', line)
                    path = match.group(1).replace('$HOME', self.user_homedir)
                    #If path == user home dir, don't use it, it's probably a misconfiguration !
                    if os.path.isdir(path) and not os.path.samefile(path, self.user_homedir):
                        self['pictures_paths'].append(path)
            gnome_conf_file.close()
        else:
            print("W: [%s:Conf.import_gnome_conf] Can't find `user-dirs.dirs' file." % __file__)

    def import_user_conf(self):
        """ Import user configuration file. """
        if os.path.isfile(self.user_conf):
            current_section = "unknown"
            user_conf_file = open(self.user_conf, "r")
            for line in user_conf_file:
                #Comments
                if re.match(r"\s*#.*", line):
                    continue
                #Section
                elif re.match(r"\s*\[([a-z]+)\]\s*", line.lower()):
                    match = re.match(r'\s*\[([a-z]+)\]\s*', line.lower())
                    current_section = match.group(1)
                #Boolean key
                elif re.match(r"\s*([a-z]+)\s*=\s*(yes|no|true|false)\s*", line.lower()):
                    match = re.match(r"\s*([a-z]+)\s*=\s*(yes|no|true|false)\s*", line.lower())
                    key = match.group(1)
                    value = match.group(2)
                    if value in ("yes", "true"):
                        value = True
                    else:
                        value = False
                    self[current_section + "_" + key] = value
                #String key : path
                elif re.match(r"\s*(path|PATH|Path)\s*=\s*\"(.+)\"\s*", line):
                    match = re.match(r"\s*(path|PATH|Path)\s*=\s*\"(.+)\"\s*", line)
                    key = "paths"
                    value = match.group(2)
                    self[current_section + "_" + key].append(value)
                #Integer key
                elif re.match(r"\s*([a-z]+)\s*=\s*([0-9]+)\s*", line.lower()):
                    match = re.match(r"\s*([a-z]+)\s*=\s*([0-9]+)\s*", line.lower())
                    key = match.group(1)
                    value = match.group(2)
                    self[current_section + "_" + key] = int(value)

            user_conf_file.close()

            #Replace "~/" by the user home dir
            for path_list in (self['music_paths'], self['pictures_paths'], self['ignored_paths']):
                for i in range(0, len(path_list)):
                    if path_list[i][0] == "~":
                        path_list[i] = os.path.join(self.user_homedir, path_list[i][2:])

            #Import "useGnomeConf" key (for compatibility)
            if "miscellaneous_usegnomeconf" in self:
                self["music_usegnomefolder"] = self["miscellaneous_usegnomeconf"]
                self["pictures_usegnomefolder"] = self["miscellaneous_usegnomeconf"]


class Thumb(object):
    """ Makes thumbnails.

    Generate thumbnails for all kind of folders
    """
    def __init__(self, img_paths):
        """The constructor.

        Argument:
          * img_paths -- a list of picture path
        """
        self.img = []
        for path in img_paths:
            try:
                img = Image.open(path).convert("RGBA")
            except IOError:
                print("E: [%s:Thumb.__init__] Can't open '%s'." % (__file__, path))
            else:
                self.img.append(img)
        self.thumb = None

    def thumbnailize(self, image, twidth=128, theight=128, rotate=0):
        """ Make thumbnail.

        Crop the picture if necessaries and return a thumbnail of it.

        Keyword argument:
          * twidth -- the width of the thumbnail (in pixels).
          * theight -- the width of the thumbnail (in pixels).

        NOTE: the size shouldn't be greater than 128 px for a standard
              freedesktop thumbnail.
        """
        width = image.size[0]
        height = image.size[1]
        
        # TODO: Implement rotate
        if (rotate):
            image.rotate(rotate, 0, 1)

        image.thumbnail((twidth, theight), Image.LANCZOS)
        return image

    def pictures_thumbnail(self, bg_picture, fg_picture, max_pictures=3):
        """ Makes thumbnails for picture folders.

        Arguments:
          * bg_picture -- the background picture
          * fg_picture -- the foreground picture

        Keyword argument:
          * max_pictures -- the maximum number of pictures on the thumbnail
        """
        #Background
        bg = Image.open(CONF["other_fg"]).convert("RGBA")
        bg_width = bg.size[0]
        bg_height = bg.size[1]
        picts = []
        number_of_pictures = 0

        #One picture
        if len(self.img) == 1 or max_pictures == 1 and len(self.img) > 0:
            number_of_pictures = 1
            thumb = self.thumbnailize(
                    self.img[0],
                    bg_width,
                    bg_height
                    )
            x = int((bg_width - thumb.size[0]) / 2)
            y = int((bg_height - thumb.size[1]) / 2)
            picts.append({
                    'thumb': thumb,
                    'x': x,
                    'y': y
                    })
        #Two pictures
        elif len(self.img) == 2 or max_pictures == 2 and len(self.img) > 0:
            number_of_pictures = 2
            #Thumb 0
            thumb = self.thumbnailize(
                    self.img[0], # image
                    bg_width, # w pos
                    int(0.7*bg_height)
                    )
            picts.append({
                    'thumb': thumb,
                    'x': 10,
                    'y': 5
                    })
            #Thumb 1
            thumb = self.thumbnailize(
                    self.img[1],
                    bg_width,
                    int(0.7*bg_height)
                    )
            x = bg_width - thumb.size[0] - 10
            y = bg_height - thumb.size[1] - 5
            picts.append({
                    'thumb': thumb,
                    'x': x,
                    'y': y
                    })
        #Three pictures
        elif len(self.img) == 3 or max_pictures == 3 and len(self.img) > 0:
            number_of_pictures = 3
            #Thumb 0
            thumb = self.thumbnailize(self.img[0], bg_width, int(0.7*bg_height))
            picts.append({
                    'thumb': thumb,
                    'x': 10,
                    'y': 5
                    })
            #Thumb 1
            thumb = self.thumbnailize(self.img[1], bg_width, int(0.7*bg_height))
            x = int(bg_width/2 - thumb.size[0]/2)
            y = int(bg_height/2 - thumb.size[1]/2)
            picts.append({
                    'thumb': thumb,
                    'x': x,
                    'y': y
                    })
            #Thumb 2
            thumb = self.thumbnailize(self.img[2], bg_width, int(0.7*bg_height))
            x = bg_width - thumb.size[0] - 10
            y = bg_height - thumb.size[1] - 5
            picts.append({
                    'thumb': thumb,
                    'x': x,
                    'y': y
                    })

        #Paste pictures on background
        for i in range(0, number_of_pictures):
            bg.paste(
                    picts[i]['thumb'],
                    (picts[i]['x'], picts[i]['y']),
                    picts[i]['thumb']
                    )
        #Paste forground on background+pictures
        fg = Image.open(CONF["other_fg"]).convert("RGBA")
        bg.paste(fg, (0, 0), fg)
        self.thumb = bg

    def save_thumb(self, output_path, output_format='PNG'):
        """ Save the thumbnail in a file.

        Argument:
          * output_path -- the output path for the thumbnail
        Keyword argument:
          * format -- the format of the picture (PNG, JPEG,...)

        NOTE : The output format must be a PNG for a standard
               freedesktop thumbnail
        """
        if self.thumb is not None:
            self.thumb.save(output_path, output_format)
        else:
            print("E: [%s:Thumb.save_thumb] No thumbnail created" % __file__)


def search_cover(path):
    """ Search for a cover file.

    Search for files like cover.png, .folder.jpg,... in the folder and return
    its name as a list of on item (or an empty list if no pictures were found)

    Argument:
      * path -- the path of the folder
    """

    images_list = list(
        itertools.chain.from_iterable(
            Path(path).glob(pattern) for pattern in ["*.jpg", "*.jpeg"]
        )
    )

    cover_path = []
    image_path_list = []

    for img in images_list:
        # for cover in COVER_FILES:
        img_path = os.path.join(path, img)
        if (os.stat(img_path).st_size > 2000000): # 2mb
            # skip images too large
            continue
        if (len(cover_path) > 3):
            # max 3 covers
            break
        if os.path.isfile(img_path):
            cover_path.append(img_path)

    return cover_path

def match_path(path, path_list):
    """ Test if a folder is a sub-folder of another one in the list.

    Arguments
      * path -- path to check
      * path_list -- list of path
    """
    match = False
    #We add a slash at the end.
    if path[-1:] != "/":
        path += "/"
    for entry in path_list:
        #We add a slash at the end.
        if entry[-1:] != "/":
            entry += "/"
        if re.match(r"^" + entry + ".*", path):
            if path != entry:
                match = True
                break
    return match


def gvfs_uri_to_path(uri):
    """Returns local file path from gvfs URI

    Arguments:
    uri -- the gvfs URI
    """
    if not re.match(r"^[a-zA-Z0-9_-]+://", uri):
        return uri
    gvfs = Gio.Vfs.get_default()
    return gvfs.get_file_for_uri(uri).get_path()


if __name__ == "__main__":
    #If we have 2 args
    if len(sys.argv) == 3:
        INPUT_FOLDER = gvfs_uri_to_path(sys.argv[1])
        OUTPUT_FILE = gvfs_uri_to_path(sys.argv[2])
    else:
        #Display informations and usage
        print("Cover thumbnailer - %s" % __doc__)
        print("Version: %s" % __version__)
        print(__copyright__)
        sys.exit(1)

    #If input path does not exists
    if not os.path.isdir(INPUT_FOLDER):
        print("E: [%s:__main__] '%s' is not a directory" % (__file__, INPUT_FOLDER))
        sys.exit(2)

    #Load configuration
    CONF = Conf()

    #Ignored folders
    if match_path(INPUT_FOLDER, CONF['ignored_paths']) \
    and not match_path(INPUT_FOLDER, CONF['neverignored_paths']):
        sys.exit(0)

    #Folders whose name starts with a dot
    elif CONF['ignored_dotted'] and re.match(".*/\..*", INPUT_FOLDER):
        sys.exit(0)

    #Picture folders
    elif CONF['pictures_enabled']: # and match_path(INPUT_FOLDER, CONF['pictures_paths']):
        picture_list = search_cover(INPUT_FOLDER)
        if (len(picture_list) > 0):
            thumbnail = Thumb(picture_list)
            thumbnail.pictures_thumbnail(
                CONF['pictures_bg'],
                CONF['pictures_fg'],
                CONF['pictures_maxthumbs']
                )
            thumbnail.save_thumb(OUTPUT_FILE, "PNG")