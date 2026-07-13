# Getting Started: Setup and Installation

This guide walks you through getting started with ek80adcp. It includes instructions for both terminal users and those using GitHub Desktop.

---

## Step 1: Get the Repository

You have two choices, depending on whether you want a local copy or are contributing changes.

### Option A: Clone the repository

#### a. Clone the repository to your computer
From a **terminal**:
```bash
git clone https://github.com/eleanorfrajka/ek80adcp
```

Or in your **browser**:
1. Navigate to [https://github.com/eleanorfrajka/ek80adcp](https://github.com/eleanorfrajka/ek80adcp)
2. Click the green `<> Code` button.
3. Choose **Open with GitHub Desktop**.

> 💡 You can rename the folder after cloning.

### Option B: Fork and contribute
See the GitHub documentation for full instructions on forking and branching when contributing to this repository.

---

## Step 2: Set Up a Python Environment

We recommend using a clean Python environment. Choose your preferred environment manager:

### Option A: Use `conda`, `mamba`, or `micromamba` (recommended for reproducibility)

If you're using conda-based environment management, create an environment from the included YAML file:

```bash
# Using conda
conda env create -f environment.yml
conda activate ek80adcp

# Using mamba (faster)
mamba env create -f environment.yml
mamba activate ek80adcp

# Using micromamba (lightweight)
micromamba create -f environment.yml
micromamba activate ek80adcp
```

### Option B: Use `venv` and `pip`
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools and testing
```

> 🔁 Both methods install all runtime and development dependencies.

---

## Step 3: Install the Package (Editable Mode)

To use the code as an importable package:
```bash
pip install -e .
```
This sets up the local repository in *editable* mode, so changes you make to `.py` files will immediately be reflected when imported.

---

## Step 4: Test That It Works

Try running the tests:
```bash
pytest
```
If all goes well, this runs the unit tests in the `tests/` folder.

---

## Optional: Use GitHub Desktop Instead of Terminal

If you prefer not to use the terminal:
- Clone the repo using GitHub Desktop.
- Set up your Python environment using a tool like Anaconda or venv.
- Open the project folder in VSCode.
- Install the Python extension and interpreter.
- Run test scripts in the terminal panel or from notebooks.

---

## You're All Set!

From here, you can start editing code, writing documentation, or adding tests.
