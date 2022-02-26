import numpy as np
import pandas as pd
import pytesseract as tess

def grid_detect(
    im,
    v_thresh=0.05,
    h_thresh=0.05,
    min_v_gap = 10, # pixels
    min_h_gap = 15, # pixels
):
    """
    This method assumes that darker pixels correspond to text within a cell. The mask
    used to generate the cell grid is just the normalized black/white image. This method is
    faster but more noisy than the ocr method.

    :params:
    im <PIL.Image or imarray>: Image of a table
        
    v_thresh <float> (0.1): Threshold for considering a row of pixels to be considered
        a vertical boundary in the grid. Higher values mean fewer rows.
        
    h_thresh <float> (0.1): Threshold for considering a column of pixels to be considered
        a horizontal boundary in the grid. Higher values mean fewer columns.
    
    :returns:
    grid <list>: list of bboxes corresponding to predicted cells
    """
    
    mask=np.array(im).sum(axis=2).T
    mask=mask/mask.max()
    mask-=1
    mask = abs(mask)
    mask = (mask>0.1).astype(int)

    v_density = mask.sum(axis=0)/max(mask.sum(axis=0))
    h_density = mask.sum(axis=1)/max(mask.sum(axis=1))
    
    # scale up the density vectors so that the mean is equal to 0.2
    # this makes the thresholds directly related to the average density
    v_density = v_density / (np.mean(v_density)*4)
    h_density = h_density / (np.mean(h_density)*4)
    
    
    # move down the image and record spans which exceed the threshold for being considered a row
    grid_y = []
    to_del = set()
    y=0
    out=True
    for y,val in enumerate(v_density):
        if val>v_thresh and out:
            out=False
            grid_y.append([y])
        if not val > v_thresh and not out:
            grid_y[-1].append(y)
            out = True
        if not out:  # inside of a peak
            if val > 1.5:
                to_del.add(len(grid_y)-1)

    # remove spans which exceed the limit of being considered a row.
    # (this is used to filter out horizontal and vertical lines)
    for x in sorted(list(to_del),reverse=True):
        grid_y.pop(x)
    
    # join spans which are too close together
    # (ocr does this in its own way, taking advantage of known character height)
    tmp = [grid_y[0]]
    for gy in grid_y[1:]:
        l = tmp[-1][1]
        r = gy[0]
        if r-l < min_v_gap:
            tmp[-1][1] = gy[1]
        else:
            tmp.append(gy)
    grid_y = tmp

    # expand to fill
    grid_y[0][0]=0
    grid_y[-1][1]=im.size[1]-1
    for i in range(len(grid_y)-1):
        x1 = grid_y[i][1] # end of this
        x2 = grid_y[i+1][0] # begining of next
        m = int((x1+x2)/2)
        grid_y[i][1]=m
        grid_y[i+1][0]=m
    
    grid_x = []
    to_del = set()
    x=0
    out=True
    for x,val in enumerate(h_density):
        if val>h_thresh and out:
            out = False
            grid_x.append([x])
        if not val>h_thresh and not out:
            grid_x[-1].append(x)
            out = True
        if not out:  # inside of a peak
            if val > 1.5:
                to_del.add(len(grid_x)-1)
    
    # remove spans which exceed the limit of being considered a row.
    # (this is used to filter out horizontal and vertical lines)
    for x in sorted(list(to_del),reverse=True):
        grid_x.pop(x)

    # join spans which are too close together
    # (ocr does this in its own way, taking advantage of known character height)
    tmp = [grid_x[0]]
    for gx in grid_x[1:]:
        b = tmp[-1][1]
        t = gx[0]
        if t-b < min_h_gap:
            tmp[-1][1] = gx[1]
        else:
            tmp.append(gx)
    grid_x = tmp
    
    # expand to fill
    grid_x[0][0]=0
    grid_x[-1][1]=im.size[0]-1
    for i in range(len(grid_x)-1):
        x1 = grid_x[i][1] # end of this
        x2 = grid_x[i+1][0] # begining of next
        m = int((x1+x2)/2)
        grid_x[i][1]=m
        grid_x[i+1][0]=m
        # diff = x2-x1
        # grid_x[i][1]+=int(3*diff/4)
        # grid_x[i+1][0]-=int(diff/4)
    
    grid = []
    for y in grid_y:
        y1,y2 = y
        for x in grid_x:
            x1,x2 = x
            grid.append([x1,y1,x2-x1,y2-y1])

    return grid

def contains(coords1, coords2):
    xa, ya, wa, ha = coords1
    xb, yb, wb, hb = coords2
    px = xb + wb/2
    py = yb + hb/2
    return xa < px and (xa + wa) > px and ya < py and (ya + ha) > py

def grid_2_table(grid, df=None):
    cells = [[""] for cell in grid]
    for i,bbox in enumerate(df[['left', 'top', 'width', 'height']].values):
        text = df["text"][i]
        for j, cell in enumerate(grid):
            if contains(cell, bbox):
                cells[j].append(text)
    n = len(set([x[0] for x in grid]))
    cells = [" ".join(x) for x in cells]
    return [cells[i:i+n] for i in range(0,len(cells),n)]

def tessdata_to_df(tessdata, keep_garbage=False):
    """Ingests a string repr of tesseract output and spits out a dataframe"""
    rows = [r.split("\t") for r in tessdata.split("\n")[:-1]]
    h = rows[0]
    rows = rows[1:]
        
    df = pd.DataFrame(rows)
    df.columns = h
    
    # set types
    dtypes = [int]*10 + [float, str]
    for c,t in zip(df.columns, dtypes):
        df[c] = df[c].values.astype(t)
    
    if not keep_garbage:
        df = df[[x.strip() != "" for x in df["text"]]]
        df = df[df["conf"] > 0].reset_index()
    
    return df

def im_to_data(im):
    tessdata = tess.image_to_data(im, config="--psm 1")
    return tessdata_to_df(tessdata)

def img_2_table(im):
    grid = grid_detect(
        im, 
        v_thresh=.1,
        h_thresh=.2,
        min_v_gap = 5, # pixels
        min_h_gap = 10, # pixels
    )
    df = im_to_data(im)
    return grid_2_table(grid, df)
