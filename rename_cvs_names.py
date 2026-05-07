import os
import glob
import random

first_names = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Alex", "Sophia", "Maria", "Carlos", "Luis", "Olivia", "Daniel", "Matthew", "Anthony", "Mark",
    "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Edward"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

files = glob.glob('example_data/CVs/**/*', recursive=True)
count = 0

for file in files:
    if os.path.isfile(file) and not file.endswith('.DS_Store'):
        dir_name = os.path.dirname(file)
        ext = os.path.splitext(file)[1]
        
        # Keep trying until we find a unique name in this directory
        while True:
            first = random.choice(first_names)
            last = random.choice(last_names)
            new_name = f"{first}_{last}{ext}"
            new_path = os.path.join(dir_name, new_name)
            if not os.path.exists(new_path):
                break
                
        os.rename(file, new_path)
        print(f"Renamed: {file} -> {new_path}")
        count += 1

print(f"Done renaming {count} files.")
