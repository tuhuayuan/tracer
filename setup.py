from setuptools import setup

setup(
    name="tracer",
    version="1.0.0",
    description="website powered by tornado",
    keywords="tornado",
    author="tuhuayuan",
    author_email="tuhuayuan@gmail.com",
    url="http://webrfs.im",
    license="MIT",
    packages=["tracer"],
    include_package_data=True,
    scripts=["tracer/scripts/tracer-admin.py"],
    install_requires=[
        "tornado",
        "sqlalchemy",
        "MySQL-python",
        "qrcode",
        "pillow",
    ],
)
