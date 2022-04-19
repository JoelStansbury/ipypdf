import numpy as np
import pandas as pd
import pytesseract as tess

from .tess_utils import im_to_data


def grid_detect(
    im,
    v_thresh=0.05,
    h_thresh=0.1,
    min_v_gap=0.05,  # percentage of average word height
    min_h_gap=2,  # percentage of average word height
):
    """
    im <PIL.Image or imarray>: Image of a table

    v_thresh <float> (0.1): Threshold for considering a row of pixels to be considered
        a vertical boundary in the grid. Higher values mean fewer rows.

    h_thresh <float> (0.1): Threshold for considering a column of pixels to be considered
        a horizontal boundary in the grid. Higher values mean fewer columns.
    """
    # use Tesseract to find all words
    df = im_to_data(im, scaling_factor=1)
    boxes = df[["left", "top", "width", "height"]].values
    avg_word_height = boxes[:, 3].min()
    min_v_gap *= avg_word_height
    min_h_gap *= avg_word_height
    # min_v_gap = 1
    # min_h_gap = 1
    # print(min_h_gap)

    # create a word mask from tesseract bboxes
    mask = np.zeros(im.size)
    for bbox in boxes:
        x, y, w, h = bbox
        mask[x : x + w, y : y + h] = 1

    v_density = mask.sum(axis=0) / max(mask.sum(axis=0))
    h_density = mask.sum(axis=1) / max(mask.sum(axis=1))

    # scale the density vectors so that the mean is equal to 0.2
    # this makes the thresholds directly related to the average density
    v_density = v_density / (np.mean(v_density) * 4)
    h_density = h_density / (np.mean(h_density) * 4)

    # move down the image and record spans which exceed the threshold for being considered a row
    grid_y = []
    to_del = set()
    y = 0
    out = True
    for y, val in enumerate(v_density):
        if val > v_thresh and out:
            out = False
            if len(grid_y) == 0 or y - grid_y[-1][-1] > min_v_gap:
                grid_y.append([y])
            else:
                grid_y[-1] = [grid_y[-1][0]]
        if val < v_thresh and not out:
            grid_y[-1].append(y)
            out = True
        if not out:  # inside of a peak
            if val > 1.5:
                to_del.add(len(grid_y) - 1)

    # expand to fill
    grid_y[0][0] = 0
    grid_y[-1][1] = im.size[1] - 1
    for i in range(len(grid_y) - 1):
        x1 = grid_y[i][1]  # end of this
        x2 = grid_y[i + 1][0]  # begining of next
        m = int((x1 + x2) / 2)
        grid_y[i][1] = m
        grid_y[i + 1][0] = m

    grid_x = []
    to_del = set()
    x = 0
    out = True
    for x, val in enumerate(h_density):
        if val > h_thresh and out:
            out = False
            if len(grid_x) == 0 or x - grid_x[-1][-1] > min_h_gap:
                grid_x.append([x])
            else:
                grid_x[-1] = [grid_x[-1][0]]
        if not val > h_thresh and not out:
            grid_x[-1].append(x)
            out = True
        if not out:  # inside of a peak
            if val > 1.5:
                to_del.add(len(grid_x) - 1)

    # expand to fill
    grid_x[0][0] = 0
    grid_x[-1][1] = im.size[0] - 1
    for i in range(len(grid_x) - 1):
        x1 = grid_x[i][1]  # end of this
        x2 = grid_x[i + 1][0]  # begining of next
        m = int((x1 + x2) / 2)
        grid_x[i][1] = m
        grid_x[i + 1][0] = m

    grid = []
    for y in grid_y:
        y1, y2 = y
        for x in grid_x:
            x1, x2 = x
            grid.append([x1, y1, x2 - x1, y2 - y1])
    return grid, df


def contains(coords1, coords2):
    xa, ya, wa, ha = coords1
    xb, yb, wb, hb = coords2
    px = xb + wb / 2
    py = yb + hb / 2
    return xa < px and (xa + wa) > px and ya < py and (ya + ha) > py


def grid_2_table(grid, df=None):
    cells = [[""] for cell in grid]
    for i, bbox in enumerate(df[["left", "top", "width", "height"]].values):
        text = df["text"][i]
        for j, cell in enumerate(grid):
            if contains(cell, bbox):
                cells[j].append(text)
    n = len(set([x[0] for x in grid]))
    cells = [" ".join(x) for x in cells]
    return [cells[i : i + n] for i in range(0, len(cells), n)]


def img_2_table(im):
    grid, df = grid_detect(im)
    return grid_2_table(grid, df)
