import os

# Path to your folder
folder_path = "packages/aegis/interfaces"

# Iterate through all files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".py"):
        file_path = os.path.join(folder_path, filename)
        # Read the file
        with open(file_path, "r") as f:
            lines = f.readlines()
        # Keep only lines that do not start with "checkpoint("
        new_lines = [line for line in lines if not line.lstrip().startswith("checkpoint(")]
        # Write back the filtered content
        with open(file_path, "w") as f:
            f.writelines(new_lines)

print("Removed all lines starting with 'checkpoint(' from Python files.")