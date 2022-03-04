# PDF Digitizer (_It has a back button!!_)
A Jupyter-based tool to help parse out structured text from a PDF document and explore the contents.

## Requirements
* [Tesseract](https://github.com/tesseract-ocr/tesseract#installing-tesseract)
* `jupyterlab` (notebook also works)

## Installation
It is highly recommended that you install this into a clean environment.

> Note: `layoutparser` puts an upper bound on `numpy` (1.19.3), so if you want
to use the `Parse Layout` button, it's best to install this in an empty environment.

### Conda (recommended)
> This is the order of operations which worked for me on most recently. Though it could probably be simplified
```bash
conda create -n ipypdf python pip
conda activate ipypdf
pip install numpy==1.19.2
conda install jupyterlab tesseract -c conda-forge
python -m pip install ipypdf
```
### No Conda (not tested)

Install [Tesseract](https://github.com/tesseract-ocr/tesseract#installing-tesseract)

```bash
python -m venv envs/ipypdf
cd envs/ipypdf/Scripts
activate.bat
python -m pip install jupyterlab 
python -m pip install ipypdf
```

### Development
see `DEVELOPMENT.md`

### Common Issues
* AutoTools widget keeps saying layoutparser is not installed
    * This is usually a problem with pywin32.
    * Try `conda install pywin32`
    * Also make sure that numpy is <1.19.3

## Usage
ipypdf is build for jupyter lab but should also work in jupyter notebooks.

1. Launch jupyter lab with `jupyter lab`
```python
from ipypdf import App
app = App("path/to/your/pdfs", bulk_render=False)
app
```

## Features

### Auto-Parser
`layoutparser` is used to determine the location of textblocks, images, and section headers. There is not currently a way to automatically determine the hierarchical position of these items.

![ezgif-3-51d38d81b3](https://user-images.githubusercontent.com/48299585/146793946-6af29c6d-d83c-4437-ac62-b56d2f787da8.gif)

> Note: this is 4x speed

> Also: This video is out-dated now. The AutoParse button will now attempt to sort all of the nodes. As well as attempting to deduce the 1st level of hierarchical structure.

### Table Parsing
![image](https://user-images.githubusercontent.com/48299585/150610905-566d6e33-b2ac-4eed-b4c5-463f1d9e35f2.png)


### Cytoscape
`Folders`, `PDF Documents`, and `Sections` have a tab labeled `Cytoscape`. This runs a tfidf similarity calculation over all nodes beneath the selected item. I.e. if you select the root node, then all defined nodes will be included in the calculation. However, only those with a link to another node will be drawn (this is for speed, may change this in the future).

The color of each node denotes the pdf document it originated from.

![image](https://user-images.githubusercontent.com/48299585/140627461-2685fe18-d918-461c-b678-86ca5f1f6a8e.png)

Selecting a node in the graph will highlight the node in the `DocTree`. Clicking the node in the `DocTree` will render the first page of the node.
![image](https://user-images.githubusercontent.com/48299585/140627583-0afea862-0b85-438c-b8b0-b6361f18d8e3.png)

### Digitizing Utilities
> I recommend turning off `Show Boxes` as this changes pages every time you add a node (working on a better solution)

Each node has a specific set of tools available to use. Here are the tools provided when a `Section` node is selected.
Starting from the left:
 * `Add Section Node` adds a sub-node of type `Section` and selects it
 * `Add Text Node` adds a sub-node of type `Text` and selects it
 * `Add Image Node` ...
 * `Delete Node` Delete the selected node and all of its children

![image](https://user-images.githubusercontent.com/48299585/140627713-2b761376-cf6b-4745-acbf-332ac28c782b.png)

### Content Selector
Content is extracted from the rendered image. Text is extracted using Optical Character Recognition (OCR). Images don't do any image analysis, they just denote coordinates and page number so that they can be retreived later if need be.

When a `Section` node is selected, the selection tool will attempt to parse text from the portion of the page selected by the user. This text will __overwrite__ the label assigned to the node.

When a `Text` node is selected, the selection tool will attempt to parse text from the selected area and __append__ it to the node's content. This is because text blocks are not always perfectly rectangular, and often span multiple pages.

When an `Image` node is selected, the coordinates of the box are appended to the node's content.

### Save Button
This will generate `json` files for each document in the directory with instructions for regenerating any nodes you have created when you open the tool again. Alternatively, you can just load the json into another script to extract the document structure if all you want is the text and the hierarchy.
