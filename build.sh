python setup.py sdist bdist_wheel ; pyinstaller --onefile runp.py --hidden-import=flask ; sudo cp dist/runp /usr/local/bin/
#runp ../nolus-profit12.py ../nolus-profit57.py

