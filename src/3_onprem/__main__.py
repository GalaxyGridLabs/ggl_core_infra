"""A Python Pulumi program"""

import pulumi
import pulumi_harvester as harvester
from shared.coder.coder import Coder
from shared.harvester.images import create_all_images


def main():
    print("Starting")

    # Create harvester images
    create_all_images()

    # Create a coder app
    coder = Coder("coder", "devops")

    # Create coder tunnel


if __name__ == "__main__":
    main()
