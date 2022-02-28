# Development
## 1. Clone this repo

```bash
git clone https://github.com/JoelStansbury/ipypdf.git
cd PDFDigitizer
```

## 2. Get `mamba`

> or stick to `conda` if you like...  just change `mamba` to `conda` in the instructions below.

If you have anaconda or miniconda, install `mamba` (it's faster and better than conda):

```bash
conda install mamba
```

You may need to specify the channel:
```conda install -c conda-forge mamba```

If you don't have `anaconda` or `miniconda`, just get [Mambaforge](https://github.com/conda-forge/miniforge/releases/tag/4.9.2-5).

## 3. Setup the `base` environment

This will be an environment that has [`anaconda-project`](https://anaconda-project.readthedocs.io) and some other dependencies to run the development commands.

For added consistency, use the provided `.condarc` file:

```bash
CONDARC=.github/.condarc        # linux
set CONDARC=.github\.condarc    # windows
```

```bash
conda env create -f .github/environment.yml -p envs/ipypdf
```

> You don't have to repeat these steps unless you delete your base environment.

## 4. Activate the environment

You will have to activate the base environment to make sure you are using the appropriate version.  You will have to do this every time you open a new shell (e.g., windows command prompt, a linux bash) unless you automate the activation of the environment.

```bash
conda activate envs/ipypdf
```

### Additional configuration

> If you are going to be changing the `anaconda-project` environments, it is a good idea to make `anaconda-project` use `mamba` instead of `conda` (it is much faster)

> Remember you will have to do this when you start your shell unless you set these environment variables permanently.

```bash
CONDA_EXE=mamba        # linux
set CONDA_EXE=mamba    # windows
```

> Remember to set your `.condarc` path as explained in `Step 3`.

## 5. Setup the Development Environment

> This will install the non-packaged dependencies and `PDF Digitizer` in editable mode.

```bash
anaconda-project run setup
```


# Dev Utilities
These helper commands are stored in `anaconda-project.yml`. Normally, the environment
is defined in this file, but environment variables are not always handled correctly.
This causes problems with Tesseract, so I've opted to define the environment in
a more static manner.

* Build the conda package<br>
    `conda build ipypdf -c conda-forge --output-folder="build/"`

* PyPi packaging
    ```bash
    python -m pip install --upgrade build
    python -m pip install --upgrade twine
    python -m build
    python -m twine upload --repository pypi dist/*
    ```

* Test
    `pytest --cov=ipypdf tests/`

* Formatting
    * `isort ipypdf/ tests/`
    * `black ipypdf/ tests/ -l 79`
    * `flake8 ipypdf/ tests/ --ignore W503`
    * `pylint ipypdf/ tests/ --rcfile=.pylintrc`
    


