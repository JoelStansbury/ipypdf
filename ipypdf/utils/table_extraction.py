# import cv2 # Temporarily removing due to conda issues
import numpy as np
import PIL.Image as pil
import pytesseract as tess

# TODO: combine img_2_cells and cells_2_table into one function
# TODO: create a clustering approach for tables without solid borders


def img_2_cells(img, approximate_cell_height=20, approximate_cell_width=150):
    """
    img <PIL.Image>: image of a table
    approximate_cell_height (pixels) <int>: This is used as a lower bound for
        valid cells. It is also used to distinguish between different rows for
        the purpose of ordering items in the output
    approximate_cell_width (pixels) <int>: This is used as a lower bound for
        valid cells. It is also used to distinguish between different columns
        for the purpose of ordering items in the output

    return <list<tuple(cv2_coords, text)>>: A list of tuples containing the
        bbox and text of detected cells. The elements are ordered first by
        column, then by row.
    """

    img = np.array(img)
    img = cv2.rectangle(
        img=img,
        pt1=(1, 1),
        pt2=(len(img[0]) - 1, len(img) - 1),
        color=(0, 0, 0),
        thickness=2,
    )
    imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(
        src=imgray, thresh=180, maxval=255, type=cv2.THRESH_BINARY_INV
    )

    # kernel = np.ones((5, 5), np.uint8)
    # dilated_value = cv2.dilate(thresh, kernel, iterations=1)

    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    items = []
    for contour, hierarchy in zip(contours, hierarchy[0]):
        x, y, w, h = cv2.boundingRect(contour)
        if w > approximate_cell_width and h > approximate_cell_height:
            text = tess.image_to_string(
                pil.fromarray(img).crop((x, y, x + w, y + h)), config="--psm 1"
            ).strip()
            cv2_coords = x, y, w, h
            items.append((cv2_coords, text))
    items.sort(
        key=lambda x: (
            x[0][1] // approximate_cell_height,
            x[0][0] // approximate_cell_width,
        )
    )
    return items


def contains(coords, px, py):
    x, y, w, h = coords
    return x < px and x + w > px and y < py and y + h > py


def cells_2_table(cells, h_thresh=20, w_thresh=20):
    """
    Given the cells returned from img_2_cells will try to construct a table

    cells <list<tuple(cv2_coords, str)>>: list of cells returned from img_2_cells
    h_thresh <int>: Sets the threshold (in pixel distance) required
        for two cells to be considered different rows
    w_thresh <int>: Sets the threshold (in pixel distance) required
        for two cells to be considered different columns
    """

    # find all row and column boundaries
    column_positions = set()
    row_positions = set()
    for cv2_coords, _ in cells:
        # thresh*(x//thresh) is used to filter out small deviations in bboxes
        column_positions.add(w_thresh * (cv2_coords[0] // w_thresh))
        column_positions.add(
            w_thresh * ((cv2_coords[0] + cv2_coords[2]) // w_thresh)
        )
        row_positions.add(h_thresh * (cv2_coords[1] // h_thresh))
        row_positions.add(
            h_thresh * ((cv2_coords[1] + cv2_coords[3]) // h_thresh)
        )

    # find the centers of each cell according to the boundaries identified above
    cp = sorted(list(column_positions))
    cp = [cp[i] + (cp[i + 1] - cp[i]) / 2 for i in range(len(cp) - 1)]

    rp = sorted(list(row_positions))
    rp = [rp[i] + (rp[i + 1] - rp[i]) / 2 for i in range(len(rp) - 1)]

    # identify the cells found in the image which best fit each of the cell
    # midpoints found above
    rows = []
    for y in rp:
        row = []
        for x in cp:
            # find all potential cells which could be used for this position
            candidate_cells = [
                cell for cell in cells if contains(cell[0], x, y)
            ]
            # sort by area
            candidate_cells.sort(key=lambda cell: cell[0][2] * cell[0][3])
            # use the smallest cell that encompases the midpoint
            if candidate_cells:
                row.append(candidate_cells[0])
            else:
                row.append((None, ""))
        rows.append(tuple(row))

    # remove duplicate rows
    unique = []
    for r in rows:
        if r not in unique:
            unique.append(r)
    rows = [list(r) for r in unique]

    # remove duplicate columns
    columns_to_remove = []
    unique_columns = []
    for c in range(len(rows[0])):
        col = []
        for r in rows:
            col.append(r[c])
        if tuple(col) in unique_columns:
            columns_to_remove.append(c)
        else:
            unique_columns.append(tuple(col))
    for c in columns_to_remove[::-1]:
        for r in rows:
            r.pop(c)

    return rows
