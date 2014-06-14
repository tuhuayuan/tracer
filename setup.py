from setuptools import setup

setup(
    name='tracer',
    version='1.0.0',
    description="web app build on tornado",
    keywords='tornado web',
    author='tuhuayuan',
    author_email='tuhuayuan@gmail.com',
    url='',
    license='MIT',
    packages=['tracer'],
    scripts=['tracer/scripts/tracer-admin.py'],
    install_requires=[
        "tornado",
        "sqlalchemy",
        "MySQL-python"
    ],
    entry_points="""
        # -*- Entry points: -*-
    """
)
