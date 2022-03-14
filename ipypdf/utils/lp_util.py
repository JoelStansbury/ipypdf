import warnings

import pytesseract as tess

from .image_utils import ImageContainer, pil_2_rel


def sort_layout(layout: list):
    x_min = float("inf")
    x_max = 0
    for block in layout:
        mn = block.coordinates[0]
        mx = block.coordinates[2]
        x_min = mn if mn < x_min else x_min
        x_max = mx if mx > x_max else x_max
    page_width = x_max - x_min

    def column(pil_coords):
        # NOTE: This places an upper-bound on columns
        # TODO: Check for changes in the predicted number of columns
        # and fix multi-column blocks vertically so that they don't get pushed
        # to the end if it changes further down
        x1, _, x2, _ = pil_coords

        if abs(x1 - x_min) < (page_width / 3):  # Max of 3 columns
            return 0

        # if it is centered then column = 0
        w = x2 - x1
        mid = x1 + (w / 2)
        page_mid = x_min + (page_width / 2)
        if abs(page_mid - mid) < (page_width / 50):
            return 0

        # max possible number of columns
        # c_num = int(page_width//w)

        return (x1 - x_min) // (page_width / 10)

    layout.sort(key=lambda x: (column(x.coordinates), x.coordinates[1]))


def parse_layout(fname, model=None, start=0, stop=-1, ignore_warning=False):
    if model is None:
        if not ignore_warning:
            warnings.warn("No model provided: loading 'ppyolov2_r50vd_dcn_365e'")
        import layoutparser as lp

        model = lp.models.PaddleDetectionLayoutModel(
            "lp://PubLayNet/ppyolov2_r50vd_dcn_365e/config"
        )

    imgs = ImageContainer(fname, bulk_render=False)
    if stop == -1:
        stop = imgs.info["Pages"]
    for i in range(start, stop):
        img = imgs[i]
        layout = list(model.detect(img))
        sort_layout(layout)
        for block in layout:
            block.relative_coordinates = pil_2_rel(
                block.coordinates, img.width, img.height
            )
            if block.type in ["Title", "List", "Text"]:
                block.text = tess.image_to_string(img.crop(block.coordinates)).strip()
        yield layout
