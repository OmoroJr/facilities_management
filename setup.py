from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

with open("facilities_management/__init__.py") as f:
	version = [l.split("=")[1].strip().strip('"').strip("'") for l in f if l.startswith("__version__")][0]

setup(
	name="facilities_management",
	version=version,
	description="Facilities Work Order, Asset, Maintenance, Booking, Vendor & Safety Management for Frappe/ERPNext",
	author="PingTap Solutions",
	author_email="info@pingtapsolutions.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
