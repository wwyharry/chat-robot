import os

if not os.path.exists('uploads'):
    os.makedirs('uploads')
    print("Created uploads directory")
