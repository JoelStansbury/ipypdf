import io

from ipywidgets import Image
from pdf2image import convert_from_path, pdfinfo_from_path


def fit(img, w, h):
    w_old = img.width
    h_old = img.height
    return min(w / w_old, h / h_old)


def scale(img, factor):
    w_old = img.width
    h_old = img.height
    return img.resize(
        size=(int(w_old * factor), int(h_old * factor)), resample=1
    )


def scale_coords(coords, w, h):
    return [w * coords[0], h * coords[1], w * coords[2], h * coords[3]]


def canvas_2_rel(coords, w, h):
    x1, y1, x2, y2 = coords
    x1, x2 = sorted([x1, x2])
    y1, y2 = sorted([y1, y2])
    return [x1 / w, x2 / w, y1 / h, y2 / h]


def rel_2_canvas(rel_coords, w, h):
    x1, x2, y1, y2 = rel_coords
    coords = [x1 * w, y1 * h, x2 * w, y2 * h]
    return [int(x) for x in coords]


def pil_2_widget(img, format="png"):
    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format=format)
    return Image(value=imgByteArr.getvalue())


def rel_2_pil(rel_coords, w, h):
    """Scales up the relative coordinates to x1, y1, x2, y2"""
    x1, x2, y1, y2 = rel_coords
    return [int(x) for x in [x1 * w, y1 * h, x2 * w, y2 * h]]


def pil_2_rel(coords, w, h):
    x1, y1, x2, y2 = coords
    return [x for x in [x1 / w, x2 / w, y1 / h, y2 / h]]


def rel_crop(img, rel_coords):
    coords = rel_2_pil(rel_coords, img.width, img.height)
    return img.crop(coords)


def cv2_2_rel(coords, w, h, offset=None):
    offset = (0, 0, 0, 0) if offset is None else offset
    dx, dy, _1, _2 = offset
    x, y, cw, ch = coords
    x1 = x + dx
    x2 = x1 + cw
    y1 = y + dy
    y2 = y1 + ch
    return [x1 / w, x2 / w, y1 / h, y2 / h]


def rel_2_cv2(rel_coords, w, h):
    x1, y1, x2, y2 = rel_2_pil(rel_coords, w, h)
    x = x1
    y = y1
    w = x2 - x
    h = y2 - y
    return [x, y, w, h]


class ImageContainer:
    def __init__(self, fname, bulk_render=True):
        self.info = pdfinfo_from_path(str(fname))
        self.bulk_render = bulk_render
        if bulk_render:
            self.imgs = convert_from_path(str(fname), dpi=300)
        else:
            self.fname = str(fname)

    def __getitem__(self, i):
        if self.bulk_render:
            return self.imgs[i]
        # manual page indexing starts at 1
        return convert_from_path(
            str(self.fname), first_page=i + 1, last_page=i + 1, dpi=300
        )[0]
