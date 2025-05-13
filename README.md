flow:
capture: create_folders.py -> capture_*.py -> convert.py
prepare: prepare.py -> create_kde_png.py -> label.py
train: train_cnn.py -> predict.py


sudo apt install pulseaudio-utils