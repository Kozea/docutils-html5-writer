from setuptools import setup, find_packages
setup(
    name='docutils_html5_writer',
    version='1.0.2',
    author='James H. Fisher, Kozea',
    license='public domain',
    install_requires=['docutils', 'html5lib', 'lxml', 'dateutil'],
    packages=find_packages(),
)
