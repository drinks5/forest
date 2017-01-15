from distutils.core import setup
from Cython.Build import cythonize

# ext_modules = cythonize([Extension(
#     "forest.app",
#     ["forest/app.pyx"], )])

ext_modules = cythonize("forest/*.pyx")
setup(packages=['forest'], name="forest", ext_modules=ext_modules)
