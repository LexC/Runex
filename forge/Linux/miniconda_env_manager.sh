#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIVISION="--------------------------------------------"

# Welcome
echo "$DIVISION"
echo "Miniconda Environment Manager"
echo "$DIVISION"
echo "Choose an option:"
echo "1. Install Miniconda"
echo "2. Create a Conda virtual environment"
echo "3. Delete a Conda virtual environment"
echo "4. Install requirements.txt into a Conda environment"
read -p "Enter your choice (1-4): " CHOICE

case $CHOICE in
  1)
    # Install Miniconda
    if command -v conda >/dev/null 2>&1; then
        echo "Miniconda is already installed."
    else
        echo "Miniconda is not installed."
        read -p "Do you want to install Miniconda? (y/n): " user_input
        if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
            echo "Downloading Miniconda installer..."
            wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda_installer.sh

            echo "Running Miniconda installer..."
            bash ~/miniconda_installer.sh
            rm ~/miniconda_installer.sh
        else
            echo "Miniconda installation skipped."
            exit 0
        fi
    fi

    echo "Checking if Miniconda path is exported in ~/.bashrc..."
    if grep -q 'conda initialize' ~/.bashrc; then
        echo "Miniconda path already exists in ~/.bashrc."
    else
        echo "Miniconda path not found in ~/.bashrc. Running 'conda init bash'..."
        ~/miniconda3/bin/conda init bash
        # Prevent base auto-activation
        sed -i 's/^# auto_activate_base.*/auto_activate_base: false/' ~/.condarc || echo 'auto_activate_base: false' >> ~/.condarc
        source ~/.bashrc
    fi
    ;;
  
  2)
    # Create a Conda environment
    echo "$DIVISION"
    echo "Miniconda Environment Creation"
    if [[ "$1" == "--venv" && -n "$2" ]]; then
      ENV_NAME="$2"
    else
      echo "$DIVISION"
      echo "Enter the name of the Conda environment to create: "
      read -p "" ENV_NAME
    fi

    if [[ -z "$ENV_NAME" ]]; then
      echo "$DIVISION"
      echo "Error: Environment name cannot be empty. Exiting."
      exit 1
    fi

    if conda info --envs | grep -q "^$ENV_NAME\\s"; then
      echo "$DIVISION"
      echo "The environment '$ENV_NAME' already exists."
      read -p "Do you want to overwrite it? (yes/[no]): " CONFIRMATION
      CONFIRMATION=${CONFIRMATION,,}
      CONFIRMATION=${CONFIRMATION:-no}

      if [[ "$CONFIRMATION" != "yes" && "$CONFIRMATION" != "y" ]]; then
        echo "Operation canceled. The environment '$ENV_NAME' was not created."
        exit 0
      else
        echo "Deleting the existing environment '$ENV_NAME'..."
        conda remove --name "$ENV_NAME" --all -y
      fi
    fi

    echo "$DIVISION"
    echo "Creating the Conda environment: $ENV_NAME..."
    conda create -n "$ENV_NAME" -y

    if conda info --envs | grep -q "^$ENV_NAME\\s"; then
      echo "$DIVISION"
      echo "The Conda environment '$ENV_NAME' has been successfully created."
    else
      echo "$DIVISION"
      echo "Failed to create the Conda environment. Please check for errors."
      exit 1
    fi

    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate "$ENV_NAME"

    echo "$DIVISION"
    echo "Installing Python 3.12..."
    conda install -n "$ENV_NAME" python=3.12 -y
    conda run -n "$ENV_NAME" python --version
    conda deactivate
    ;;

  3)
    # Delete a Conda environment
    echo "$DIVISION"
    echo "Miniconda Environment Deletion"
    if [[ "$1" == "--venv" && -n "$2" ]]; then
      ENV_NAME="$2"
    else
        echo "$DIVISION"
        echo "Available Conda environments:"
        conda info --envs
        echo "$DIVISION"
        echo "Enter the name of the environment you want to delete: "
        read -p "" ENV_NAME
    fi

    if conda info --envs | grep -q "^$ENV_NAME\\s"; then
      echo "$DIVISION"
      echo "The environment '$ENV_NAME' will be deleted."
      read -p "Are you sure you want to proceed? (yes/[no]): " CONFIRMATION
      CONFIRMATION=${CONFIRMATION,,}
      CONFIRMATION=${CONFIRMATION:-yes}

      if [[ "$CONFIRMATION" == "yes" || "$CONFIRMATION" == "y" ]]; then
        echo "Deleting the environment '$ENV_NAME'..."
        conda remove --name "$ENV_NAME" --all -y
        echo "The environment '$ENV_NAME' has been successfully deleted."
      else
        echo "Deletion canceled. The environment '$ENV_NAME' was not deleted."
      fi
    else
      echo "$DIVISION"
      echo "The environment '$ENV_NAME' does not exist. Exiting script."
    fi
    ;;

  4)
    # Install requirements.txt in an environment
    echo "$DIVISION"
    echo "Install requirements.txt into an environment"
    echo "Available Conda environments:"
    conda info --envs
    read -p "Enter the name of the environment to use: " ENV_NAME

    if conda info --envs | grep -q "^$ENV_NAME\\s"; then
      REQ_PATH="$SCRIPT_DIR/requirements.txt"
      if [[ -f "$REQ_PATH" ]]; then
        echo "Installing requirements from $REQ_PATH into $ENV_NAME..."
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda activate "$ENV_NAME"
        pip install -r "$REQ_PATH"
        conda deactivate
      else
        echo "requirements.txt not found in script directory: $SCRIPT_DIR"
      fi
    else
      echo "Environment $ENV_NAME does not exist."
    fi
    ;;

  *)
    echo "Invalid choice. Exiting."
    ;;
esac
