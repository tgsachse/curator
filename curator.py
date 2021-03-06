"""Curate images and videos with this simple script!

Written by Tiger Sachse.
"""
import os
import shutil
import pathlib
import argparse
import datetime


# Constants and defaults for this script.
KNOWN_IMAGE_TYPES = {
    ".gif",
    ".bmp",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
}
KNOWN_VIDEO_TYPES = {
    ".m4v",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
}
DEFAULT_TITLE = "Album"
DEFAULT_VIDEO_DIRECTORY = "Clips"
TITLE_FORMAT = "{year}-{month} {title}"
ITEM_FORMAT = "{initials}_{index}{extension}"
IGNORING_ITEM_FORMAT = "Ignoring {0} due to unknown filetype."


class Parser(argparse.ArgumentParser):
    """This class parses and sanitizes command line arguments."""

    def __init__(self, *args, **kwargs):
        """Initialize super and add some arguments."""
        super().__init__(*args, add_help=False, **kwargs)
        self.__add_arguments()

    def parse_arguments(self):
        """Parse the command line arguments."""
        self.__parse_arguments()
        self.__sanitize_arguments()
        if self.arguments["initials"] is None:
            self.__determine_initials()
        
    def error(self, message):
        """If any parsing error occurs, tell the user."""
        print("An error occurred:", message)

    def __add_arguments(self):
        """Add a handful of arguments to this script."""
        self.add_argument("destination")
        self.add_argument("sources", nargs="+")
        self.add_argument("--initials", default=None)
        self.add_argument("--title", default=DEFAULT_TITLE)
        self.add_argument("--year", default=datetime.datetime.now().year)
        self.add_argument("--month", default=datetime.datetime.now().month)

    def __parse_arguments(self):
        """Parse known arguments and save them."""
        self.arguments, self.unknown = self.parse_known_args()
        self.arguments = vars(self.arguments)

    def __sanitize_arguments(self):
        """Transform some arguments into more useful forms."""
        def collect_subsources(source, subsources):
            """Recursively collect subsources inside of a source."""
            for item in source.iterdir():
                if item.is_dir():
                    subsources.add(item)
                    collect_subsources(item, subsources)

        self.arguments["month"] = str(self.arguments["month"]).rjust(2, "0")
        self.arguments["year"] = str(self.arguments["year"]).rjust(4, "0")
        self.arguments["destination"] = pathlib.Path(self.arguments["destination"])
        self.arguments["sources"] = set(
            map(
                lambda source: pathlib.Path(source),
                self.arguments["sources"],
            ),
        )
        subsources = set()
        for source in self.arguments["sources"]:
            collect_subsources(source, subsources)
        self.arguments["sources"] |= subsources
        self.arguments["sources"] = list(
            sorted(self.arguments["sources"], key=lambda source_path: source_path),
        )

    def __determine_initials(self):
        """Get initials from the title."""
        self.arguments["initials"] = "".join(
            filter(
                lambda character: character.isupper(),
                self.arguments["title"],
            ),
        )


def count_files(sources, desired_filetypes):
    """Count the number of files in a collection of sources."""
    file_count = 0
    for source in sources:
        for item in source.iterdir():
            filetype = item.suffix.lower()
            if filetype in desired_filetypes:
                file_count += 1

    return file_count


# Main entry point of the script.
parser = Parser()
parser.parse_arguments()

# Determine the number of places required for the image and video indexes.
image_count = count_files(parser.arguments["sources"], KNOWN_IMAGE_TYPES)
video_count = count_files(parser.arguments["sources"], KNOWN_VIDEO_TYPES)
image_index_places = len(str(image_count))
video_index_places = len(str(video_count))

# Create the Path objects for the main destination and the video destination.
destination = parser.arguments["destination"] / TITLE_FORMAT.format(
    year=parser.arguments["year"],
    month=parser.arguments["month"],
    title=parser.arguments["title"],
)

# Place videos in the main destination if no images exist, else place them in a
# separate directory.
if video_count > 0 and image_count == 0:
    video_destination = destination
else:
    video_destination = destination / DEFAULT_VIDEO_DIRECTORY

# If either destination doesn't exist, create it.
if image_count > 0 and not destination.exists():
    destination.mkdir(parents=True)
if video_count > 0 and not video_destination.exists():
    video_destination.mkdir(parents=True)

# Collect all items into a list. This list is sorted by modification time on a
# per-subsource basis.
items = []
for source in parser.arguments["sources"]:
    subsource_items = []
    for item in source.iterdir():
        if item.is_dir():
            continue
        subsource_items.append((item, os.path.getmtime(str(item))))
    subsource_items = sorted(subsource_items, key=lambda pair: pair[1])
    items.extend(subsource_items)

# Copy each image and video into the correct destination.
image_index = 1
video_index = 1
for item, timestamp in items:
    filetype = item.suffix.lower()
    if filetype in KNOWN_IMAGE_TYPES:
        shutil.copy2(
            item,
            destination / ITEM_FORMAT.format(
                initials=parser.arguments["initials"],
                index=str(image_index).rjust(image_index_places, "0"),
                extension=filetype,
            ),
        )
        image_index += 1
    elif filetype in KNOWN_VIDEO_TYPES:
        shutil.copy2(
            item,
            video_destination / ITEM_FORMAT.format(
                initials=parser.arguments["initials"],
                index=str(video_index).rjust(video_index_places, "0"),
                extension=filetype,
            ),
        )
        video_index += 1
    else:
        print(IGNORING_ITEM_FORMAT.format(item))
