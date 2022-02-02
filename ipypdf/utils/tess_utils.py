# This script (Work in Progress) contains a pipeline for generating
# trainable data from user input. So far (12/13/2021) the pipeline only
# adds an identifier to words extracted from Tesseract indicating wether or
# not the word is part of a section heading. There is not yet any mechanism
# for indicating the position of the section relative to the document tree.
# The current plan is to pass this data into an LSTM to predict the hierarchy.

import pandas as pd
import pytesseract as tess

from .image_utils import ImageContainer, pil_2_rel


def get_ocr_data(path):
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
            coords = pil_2_rel([x1, y1, x2, y2], w["page_width"], w["page_height"])
            text = " ".join(tmp["text"])
            text_blocks.append(
                {"value": text, "page": w["page"], "coords": coords}
            )
        yield text_blocks
        
