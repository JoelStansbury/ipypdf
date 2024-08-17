# This script (Work in Progress) contains a pipeline for generating
# trainable data from user input. So far (12/13/2021) the pipeline only
# adds an identifier to words extracted from Tesseract indicating wether or
# not the word is part of a section heading. There is not yet any mechanism
# for indicating the position of the section relative to the document tree.
# The current plan is to pass this data into an LSTM to predict the hierarchy.

import numpy as np
import pandas as pd
import pytesseract as tess

from .image_utils import ImageContainer, pil_2_rel


def tessdata_to_df(tessdata, keep_garbage=False):
    """Ingests a string repr of tesseract output and spits out a dataframe"""
    rows = [r.split("\t") for r in tessdata.split("\n")[:-1]]
    h = rows[0]
    rows = rows[1:]

    df = pd.DataFrame(rows)
    df.columns = h

    # set types
    dtypes = [int] * 10 + [float, str]
    for c, t in zip(df.columns, dtypes):
        df[c] = df[c].values.astype(t)

    if not keep_garbage:
        df = df[[x.strip() != "" for x in df["text"]]]
        df = df[df["conf"] > 0].reset_index()

    return df


def fit_bboxes_to_text(im, tessdata):
    """
    Tesseract bboxes sometimes have very wide margins on them. This is bad for the purpose
    of determining the grid that defines the layout.
    Shrinks each side of the bbox until ~8% of the darkness is lost.

    im <PIL.Image or np.array()>: image used for cropping out the boxes defined in tessdata

    tessdata <Pandas.DataFrame>: Should be a dataframe with columns ["left","top","width","height"]
        as is returned by tessdata_to_df
    """
    df_left = tessdata["left"].values
    df_top = tessdata["top"].values
    df_width = tessdata["width"].values
    df_height = tessdata["height"].values

    im = np.array(im).sum(axis=2)
    im = im / im.max()
    im = abs(im - 1)
    for i, bbox in enumerate(
        tessdata[["left", "top", "width", "height"]].values
    ):
        x, y, w, h = bbox
        cropped = im[y : y + h, x : x + w]

        v_sum = cropped.sum(axis=1)
        h_sum = cropped.sum(axis=0)

        top = 0
        while sum(v_sum[top:]) > sum(v_sum) * 0.98 and top < len(v_sum) - 3:
            top += 1

        bottom = len(v_sum)
        while sum(v_sum[top:bottom]) > sum(v_sum) * 0.96 and bottom > top + 2:
            bottom -= 1

        left = 0
        while sum(h_sum[left:]) > sum(h_sum) * 0.98 and left < len(h_sum) - 3:
            left += 1

        right = len(h_sum)
        while sum(h_sum[left:right]) > sum(h_sum) * 0.96 and right > left + 2:
            right -= 1

        df_left[i] = x + left
        df_top[i] = y + top
        df_width[i] = right - left
        df_height[i] = bottom - top

    df = tessdata.copy()
    df["left"] = df_left
    df["top"] = df_top
    df["width"] = df_width
    df["height"] = df_height
    return df


def scale(im, scale):
    return im.resize(tuple(int(x * scale) for x in im.size))


def im_to_data(im, scaling_factor=1):
    """
    im: Image
    scaling_factor: Amount to scale the image (evenly along both axes)
        This is solely for the purpose of improving OCR results. The
        image is scaled before passing to Tesseract, then the output
        of Tesseract is scaled down to fit the dimensions of the original
        image.
        Default = 1 (no scaling)
    """
    tessdata = tess.image_to_data(scale(im, scaling_factor), config="--psm 1")

    df = tessdata_to_df(tessdata)
    df["left"] = (df["left"] // scaling_factor).astype(int)
    df["top"] = (df["top"] // scaling_factor).astype(int)
    df["width"] = (df["width"] // scaling_factor).astype(int)
    df["height"] = (df["height"] // scaling_factor).astype(int)
    return df


def get_ocr_data(path):
    """
    This is almost identical to tessdata_to_df
    TODO: merge the two functions into one
    """
    imgs = ImageContainer(path, bulk_render=False)
    for i in range(imgs.info["Pages"]):
        img = imgs[i]
        # Pass full page into Tesseract
        data = tess.image_to_data(img, config="--psm 1")
        # Parse output into dataframe
        p_rows = [line.split("\t") for line in data.split("\n")]
        df = pd.DataFrame(data=p_rows[1:-1], columns=p_rows[0])
        # Remove whitespaces TODO: keep this whitespace in the dataset
        df = df[df["conf"] != "-1"]
        df["left"] = df["left"].astype(int)
        df["top"] = df["top"].astype(int)
        df["width"] = df["width"].astype(int)
        df["height"] = df["height"].astype(int)

        df["block_num"] = df["block_num"].astype(int)
        # Remember page num
        df["page"] = i
        df["page_width"] = img.width
        df["page_height"] = img.height
        yield df.reset_index()


def get_text_blocks(path):
    """
    Used to extract text from images
    """
    for df in get_ocr_data(path):
        groups = df.groupby(by="block_num").groups
        # print(groups.groups)
        keys = sorted(list(groups.keys()))
        text_blocks = []
        for k in keys:
            word_idxs = groups[k]
            tmp = df.iloc[word_idxs]
            w = tmp.to_dict("records")[0]
            x1 = min(tmp["left"])
            y1 = min(tmp["top"])
            x2 = max(tmp["left"] + tmp["width"])
            y2 = max(tmp["top"] + tmp["height"])
            coords = pil_2_rel(
                [x1, y1, x2, y2], w["page_width"], w["page_height"]
            )
            text = " ".join(tmp["text"])
            text_blocks.append(
                {
                    "value": text,
                    "page": w["page"],
                    "rel_coords": coords,
                    "pil_coords": [x1, y1, x2, y2],
                }
            )
        yield text_blocks
